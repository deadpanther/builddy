"""Twitter poll and status endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from models import Build, Mention
from services.twitter import search_mentions, post_reply

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/twitter", tags=["twitter"])


@router.get("/status")
async def twitter_status():
    """Get Twitter polling status."""
    return {
        "status": "active",
        "message": "Twitter polling is available. Use POST /api/twitter/poll to check mentions.",
    }


@router.post("/poll")
async def poll_mentions(session: Session = Depends(get_session)):
    """Manually trigger mention check."""
    # Get the latest processed mention to use as since_id
    latest = session.exec(
        select(Mention).order_by(Mention.created_at.desc()).limit(1)
    ).first()
    since_id = latest.tweet_id if latest else None

    mentions = await search_mentions(since_id=since_id)
    new_count = 0
    builds_created = []

    for m in mentions:
        # Check if we've already processed this tweet
        existing = session.exec(
            select(Mention).where(Mention.tweet_id == m["tweet_id"])
        ).first()
        if existing:
            continue

        # Create mention record
        mention = Mention(
            tweet_id=m["tweet_id"],
            tweet_text=m["tweet_text"],
            twitter_username=m["twitter_username"],
            processed=False,
        )
        session.add(mention)
        session.commit()
        session.refresh(mention)

        # Create a build from this mention
        build = Build(
            tweet_id=m["tweet_id"],
            tweet_text=m["tweet_text"],
            twitter_username=m["twitter_username"],
            prompt=m["tweet_text"],
            status="pending",
        )
        session.add(build)
        session.commit()
        session.refresh(build)

        # Link mention to build
        mention.build_id = build.id
        mention.processed = True
        session.add(mention)
        session.commit()

        # Run the pipeline
        import asyncio
        from routers.builds import _run_build_pipeline
        asyncio.create_task(_run_build_pipeline(build.id))

        new_count += 1
        builds_created.append(build.id)

    return {
        "mentions_found": len(mentions),
        "new_mentions": new_count,
        "builds_created": builds_created,
    }


@router.get("/mentions")
async def get_mentions(
    limit: int = 20,
    session: Session = Depends(get_session),
):
    """Get recent mentions."""
    mentions = session.exec(
        select(Mention).order_by(Mention.created_at.desc()).limit(limit)
    ).all()
    return mentions
