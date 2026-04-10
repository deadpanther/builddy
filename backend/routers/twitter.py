"""Twitter poll, auto-poll loop, and reply-on-deploy endpoints."""

import asyncio
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from config import settings
from database import get_new_session, get_session
from models import Build, Mention
from services.twitter import post_reply, search_mentions, twitter_configured
from services.twitter_scraper import scraper as twitter_scraper

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/twitter", tags=["Twitter"])

# ---------------------------------------------------------------------------
# Background polling state
# ---------------------------------------------------------------------------

_poll_task: asyncio.Task | None = None
POLL_INTERVAL_SECONDS = 60  # check every 60s

# One mention → one pipeline → many GLM requests. Serializing Twitter builds avoids 4× load when
# the scraper submits several mentions in one poll (still "one user", one API key).
_twitter_pipeline_sem: asyncio.Semaphore | None = None


def _twitter_pipeline_semaphore() -> asyncio.Semaphore:
    global _twitter_pipeline_sem
    if _twitter_pipeline_sem is None:
        n = max(1, int(getattr(settings, "TWITTER_MAX_CONCURRENT_PIPELINES", 1)))
        _twitter_pipeline_sem = asyncio.Semaphore(n)
        logger.info("Twitter mention builds: max %d concurrent pipeline(s)", n)
    return _twitter_pipeline_sem


async def _poll_loop():
    """Background loop that checks for @builddy mentions periodically."""
    logger.info("Twitter auto-poll loop started (every %ds)", POLL_INTERVAL_SECONDS)
    while True:
        try:
            await _process_mentions()
        except Exception as e:
            logger.error("Poll loop error: %s", str(e))
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _process_mentions():
    """Fetch new mentions, create builds, kick off pipelines."""
    session = get_new_session()
    try:
        # Get since_id from latest processed mention
        latest = session.exec(
            select(Mention).order_by(Mention.created_at.desc()).limit(1)
        ).first()
        since_id = latest.tweet_id if latest else None

        mentions = await search_mentions(since_id=since_id)
        for m in mentions:
            # Skip already-processed tweets
            existing = session.exec(
                select(Mention).where(Mention.tweet_id == m["tweet_id"])
            ).first()
            if existing:
                continue

            # Strip @builddy from the prompt
            raw_text = m["tweet_text"]
            prompt = raw_text.replace("@builddy", "").replace("@Builddy", "").strip()
            if not prompt:
                logger.info("Skipping empty mention from @%s", m["twitter_username"])
                continue

            logger.info(
                "New mention from @%s: %s", m["twitter_username"], prompt[:80]
            )

            # Create mention record
            mention = Mention(
                tweet_id=m["tweet_id"],
                tweet_text=raw_text,
                twitter_username=m["twitter_username"],
                processed=False,
            )
            session.add(mention)
            session.commit()
            session.refresh(mention)

            # Create build
            build = Build(
                tweet_id=m["tweet_id"],
                tweet_text=raw_text,
                twitter_username=m["twitter_username"],
                prompt=prompt,
                status="pending",
            )
            session.add(build)
            session.commit()
            session.refresh(build)

            # Link mention -> build
            mention.build_id = build.id
            mention.processed = True
            session.add(mention)
            session.commit()

            # Each mention starts a full pipeline concurrently (many = GLM 429s). GLM calls are
            # globally capped via GLM_MAX_CONCURRENT_REQUESTS in agent/llm.py.
            asyncio.create_task(_build_and_reply(build.id, m["tweet_id"], m["twitter_username"]))

    finally:
        session.close()


async def _build_and_reply(build_id: str, tweet_id: str, username: str):
    """Run text pipeline then reply to the tweet with the live app link."""
    from routers.builds import _run_build_pipeline

    try:
        await _run_build_pipeline(build_id)
    except Exception as e:
        logger.error("Pipeline failed for tweet-build %s: %s", build_id, e)

    await _send_reply(build_id, tweet_id, username)


async def _build_screenshot_and_reply(
    build_id: str, tweet_id: str, username: str,
    screenshot_b64: str, prompt: str,
):
    """Run screenshot-to-app pipeline then reply with the live link.

    The prompt is enriched to capture the ESSENCE of the referenced app,
    not just pixel-copy it — we add our own twist and improvements.
    """
    from agent.pipeline import run_screenshot_pipeline

    enriched_prompt = (
        f"{prompt}\n\n"
        f"IMPORTANT: The screenshot above is INSPIRATION, not a clone target. "
        f"Capture the core concept and purpose of this app, then BUILD YOUR OWN VERSION that is:\n"
        f"- Visually distinct with a fresh, modern design (don't copy their exact colors/layout)\n"
        f"- Feature-enhanced — add 2-3 features the original is missing\n"
        f"- More polished — better animations, dark mode, keyboard shortcuts\n"
        f"- Fully functional — not just a visual shell\n"
        f"Think of it as: 'What if a top designer reimagined this app from scratch?'"
    )

    try:
        await run_screenshot_pipeline(build_id, [screenshot_b64], enriched_prompt)
    except Exception as e:
        logger.error("Screenshot pipeline failed for tweet-build %s: %s", build_id, e)

    await _send_reply(build_id, tweet_id, username)


async def _send_reply(build_id: str, tweet_id: str, username: str):
    """Check build result and reply to the tweet."""
    session = get_new_session()
    try:
        build = session.get(Build, build_id)
        if not build:
            return

        if build.status == "deployed" and build.deploy_url:
            app_name = build.app_name or "your app"
            reply_text = (
                f"@{username} your app is live! \n\n"
                f"{app_name}\n"
                f"{build.deploy_url}\n\n"
                f"Built with GLM 5.1 in minutes. "
                f"Reply again to modify it!"
            )
        elif build.status == "failed":
            reply_text = (
                f"@{username} I hit a snag building that one. "
                f"Try rephrasing or adding more detail to your request!"
            )
        else:
            return  # still running, skip reply

        await post_reply(tweet_id, reply_text)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Startup helper — called from lifespan
# ---------------------------------------------------------------------------

async def start_twitter_poll():
    """Start the background poll loop if Twitter creds are configured."""
    global _poll_task
    if not twitter_configured():
        logger.info("Twitter credentials not configured — auto-poll disabled")
        return
    if _poll_task is not None:
        return  # already running
    _poll_task = asyncio.create_task(_poll_loop())
    logger.info("Twitter auto-poll task created")


async def stop_twitter_poll():
    """Cancel the background poll task."""
    global _poll_task
    if _poll_task is not None:
        _poll_task.cancel()
        _poll_task = None
        logger.info("Twitter auto-poll task cancelled")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status")
async def twitter_status():
    """Get Twitter polling status."""
    return {
        "configured": twitter_configured(),
        "api_poll_active": _poll_task is not None and not _poll_task.done(),
        "scraper_active": twitter_scraper._running,
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
    }


@router.post("/poll")
async def poll_mentions(session: Session = Depends(get_session)):
    """Manually trigger a mention check."""
    latest = session.exec(
        select(Mention).order_by(Mention.created_at.desc()).limit(1)
    ).first()
    since_id = latest.tweet_id if latest else None

    mentions = await search_mentions(since_id=since_id)
    new_count = 0
    builds_created = []

    for m in mentions:
        existing = session.exec(
            select(Mention).where(Mention.tweet_id == m["tweet_id"])
        ).first()
        if existing:
            continue

        raw_text = m["tweet_text"]
        prompt = raw_text.replace("@builddy", "").replace("@Builddy", "").strip()
        if not prompt:
            continue

        mention = Mention(
            tweet_id=m["tweet_id"],
            tweet_text=raw_text,
            twitter_username=m["twitter_username"],
            processed=False,
        )
        session.add(mention)
        session.commit()
        session.refresh(mention)

        build = Build(
            tweet_id=m["tweet_id"],
            tweet_text=raw_text,
            twitter_username=m["twitter_username"],
            prompt=prompt,
            status="pending",
        )
        session.add(build)
        session.commit()
        session.refresh(build)

        mention.build_id = build.id
        mention.processed = True
        session.add(mention)
        session.commit()

        # Concurrent with other ingests / dashboard builds; see GLM_MAX_CONCURRENT_REQUESTS.
        asyncio.create_task(_build_and_reply(build.id, m["tweet_id"], m["twitter_username"]))

        new_count += 1
        builds_created.append(build.id)

    return {
        "mentions_found": len(mentions),
        "new_mentions": new_count,
        "builds_created": builds_created,
    }


# ---------------------------------------------------------------------------
# Ingest endpoint — called by the Playwright scraper
# ---------------------------------------------------------------------------

class ScrapedMention(BaseModel):
    tweet_id: str
    tweet_text: str
    twitter_username: str
    parent_screenshot: str | None = None   # base64 PNG of the parent tweet's content
    parent_text: str | None = None         # text from the parent tweet


@router.post("/ingest")
async def ingest_mention(data: ScrapedMention, session: Session = Depends(get_session)):
    """Receive a scraped mention from the Playwright scraper and trigger a build.

    If parent_screenshot is provided (reply to a design tweet), uses the
    screenshot-to-app pipeline instead of the text pipeline.
    """
    # Skip duplicates
    existing = session.exec(
        select(Mention).where(Mention.tweet_id == data.tweet_id)
    ).first()
    if existing:
        return {"status": "duplicate", "tweet_id": data.tweet_id}

    raw_text = data.tweet_text
    prompt = raw_text.replace("@builddy", "").replace("@Builddy", "").strip()

    # If it's a reply with parent context, enrich the prompt
    has_screenshot = bool(data.parent_screenshot)
    if data.parent_text:
        prompt = f"{prompt}\n\nOriginal post: {data.parent_text}" if prompt else data.parent_text

    if not prompt and not has_screenshot:
        return {"status": "skipped", "reason": "empty prompt and no screenshot"}

    build_type = "screenshot" if has_screenshot else "text"
    logger.info(
        "Ingested %s mention from @%s: %s%s",
        build_type, data.twitter_username, prompt[:80],
        " (with parent screenshot)" if has_screenshot else "",
    )

    mention = Mention(
        tweet_id=data.tweet_id,
        tweet_text=raw_text,
        twitter_username=data.twitter_username,
        processed=False,
    )
    session.add(mention)
    session.commit()
    session.refresh(mention)

    build = Build(
        tweet_id=data.tweet_id,
        tweet_text=raw_text,
        twitter_username=data.twitter_username,
        prompt=prompt or "Build this app based on the screenshot",
        status="pending",
        build_type=build_type,
    )
    session.add(build)
    session.commit()
    session.refresh(build)

    mention.build_id = build.id
    mention.processed = True
    session.add(mention)
    session.commit()

    # Playwright scraper often submits several mentions in one poll; each create_task is a
    # concurrent pipeline. Mention polling itself does not call GLM — only these tasks do.
    if has_screenshot:
        asyncio.create_task(
            _build_screenshot_and_reply(
                build.id, data.tweet_id, data.twitter_username,
                data.parent_screenshot, prompt or "Build this app",
            )
        )
    else:
        asyncio.create_task(_build_and_reply(build.id, data.tweet_id, data.twitter_username))

    return {"status": "created", "build_id": build.id, "tweet_id": data.tweet_id, "type": build_type}


@router.get("/mentions")
async def get_mentions(
    limit: int = 20,
    session: Session = Depends(get_session),
):
    """Get recent mentions with their build status."""
    mentions = session.exec(
        select(Mention).order_by(Mention.created_at.desc()).limit(limit)
    ).all()
    results = []
    for m in mentions:
        build = session.get(Build, m.build_id) if m.build_id else None
        results.append({
            "id": m.id,
            "tweet_id": m.tweet_id,
            "tweet_text": m.tweet_text,
            "twitter_username": m.twitter_username,
            "processed": m.processed,
            "build_id": m.build_id,
            "build_status": build.status if build else None,
            "deploy_url": build.deploy_url if build else None,
            "created_at": m.created_at.isoformat(),
        })
    return results
