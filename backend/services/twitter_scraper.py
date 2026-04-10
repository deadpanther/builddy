"""
Nitter-based Twitter mention scraper.

Scrapes @builddy mentions from Nitter (public Twitter frontend) — no login,
no API keys, no bot detection. Runs Playwright headless to render Nitter's
JavaScript, parses tweet cards, and forwards mentions to the backend API.

Works locally and on Railway without any Twitter credentials.
"""

import asyncio
import logging
import os
import re
import threading
from pathlib import Path

import httpx
from playwright.async_api import async_playwright

from config import settings

logger = logging.getLogger(__name__)

# Nitter instances to try (in order of preference)
NITTER_HOSTS = [
    "nitter.net",
    "xcancel.com",
    "nitter.poast.org",
    "nitter.privacydev.net",
]

POLL_INTERVAL = 10  # seconds between checks

# Backend API base
BACKEND_BASE = f"http://127.0.0.1:{settings.PORT}"

# Detect environment
IS_RAILWAY = bool(os.environ.get("RAILWAY_ENVIRONMENT"))


SEEN_IDS_FILE = Path(__file__).parent.parent / ".seen_tweet_ids"


class TwitterMentionScraper:
    """Scrapes @builddy mentions from Nitter — no Twitter login needed."""

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._seen_tweet_ids: set[str] = self._load_seen_ids()
        self._context = None
        self._page = None
        self._working_host: str | None = None

    @staticmethod
    def _load_seen_ids() -> set[str]:
        """Load previously seen tweet IDs from disk."""
        try:
            if SEEN_IDS_FILE.exists():
                ids = SEEN_IDS_FILE.read_text().strip().splitlines()
                logger.info("Loaded %d seen tweet IDs from disk", len(ids))
                return set(ids)
        except Exception:
            pass
        return set()

    def _save_seen_ids(self):
        """Persist seen tweet IDs to disk (keep last 500)."""
        try:
            # Keep only the most recent 500 to avoid unbounded growth
            recent = sorted(self._seen_tweet_ids)[-500:]
            SEEN_IDS_FILE.write_text("\n".join(recent) + "\n")
        except Exception as e:
            logger.debug("Failed to save seen IDs: %s", e)

    async def _ensure_browser(self, pw):
        """Launch a lightweight Chromium browser."""
        self._context = await pw.chromium.launch_persistent_context(
            user_data_dir=str(Path(__file__).parent.parent / ".nitter_browser_state"),
            headless=IS_RAILWAY,
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()

    async def _find_working_host(self) -> str | None:
        """Try Nitter instances until one works."""
        for host in NITTER_HOSTS:
            url = f"https://{host}/search?f=tweets&q=%40builddy"
            try:
                resp = await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await self._page.wait_for_timeout(3000)
                if resp and resp.status == 200 and "login" not in self._page.url:
                    # Nitter sometimes needs a refresh on first load
                    items = await self._page.query_selector_all(".timeline-item")
                    if not items:
                        await self._page.reload(wait_until="domcontentloaded", timeout=15000)
                        await self._page.wait_for_timeout(3000)
                    items = await self._page.query_selector_all(".timeline-item")
                    if items:
                        logger.info("Nitter instance %s works (%d tweets found)", host, len(items))
                        return host
                    # Maybe different structure
                    body = await self._page.inner_text("body")
                    if len(body) > 200 and "No items found" not in body:
                        logger.info("Nitter instance %s has content", host)
                        return host
                logger.debug("Nitter instance %s: no results", host)
            except Exception as e:
                logger.debug("Nitter instance %s failed: %s", host, e)
        return None

    async def _scrape_mentions(self) -> list[dict]:
        """Scrape @builddy mentions from Nitter search."""
        if not self._working_host:
            self._working_host = await self._find_working_host()
            if not self._working_host:
                logger.warning("No working Nitter instance found")
                return []

        url = f"https://{self._working_host}/search?f=tweets&q=%40builddy"
        mentions = []

        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await self._page.wait_for_timeout(3000)

            # Nitter sometimes needs a refresh to load results
            items = await self._page.query_selector_all(".timeline-item")
            if not items:
                logger.debug("No items on first load — refreshing Nitter page")
                await self._page.reload(wait_until="domcontentloaded", timeout=20000)
                await self._page.wait_for_timeout(4000)

            # Nitter uses .timeline-item for each tweet
            items = await self._page.query_selector_all(".timeline-item")
            if not items:
                # Fallback: try other selectors
                items = await self._page.query_selector_all(".tweet-body, article")

            logger.debug("Found %d items on Nitter", len(items))

            for item in items[:15]:
                try:
                    mention = await self._parse_nitter_item(item)
                    if mention and mention["tweet_id"] not in self._seen_tweet_ids:
                        mentions.append(mention)
                except Exception as e:
                    logger.debug("Failed to parse Nitter item: %s", e)

        except Exception as e:
            logger.error("Failed to scrape Nitter: %s", e)
            # Reset host so we try again next poll
            self._working_host = None

        return mentions

    async def _parse_nitter_item(self, item) -> dict | None:
        """Parse a Nitter timeline item into a mention dict.

        Also captures screenshots of any images/videos in the tweet itself.
        """
        # Get tweet link to extract tweet ID
        link = await item.query_selector('a[href*="/status/"]')
        if not link:
            return None
        href = await link.get_attribute("href") or ""
        match = re.search(r"/status/(\d+)", href)
        if not match:
            return None
        tweet_id = match.group(1)

        # Get tweet text
        content_el = await item.query_selector(".tweet-content, .media-body")
        if not content_el:
            content_el = item
        tweet_text = await content_el.inner_text()
        tweet_text = tweet_text.strip()

        if not tweet_text:
            return None

        # Get username
        username_el = await item.query_selector(".username, a[href^='/']")
        twitter_username = "unknown"
        if username_el:
            raw = await username_el.inner_text()
            twitter_username = raw.lstrip("@").strip()

        # Check if it's a reply
        reply_el = await item.query_selector(".replying-to, .reply-to")
        parent_text = None
        if reply_el:
            parent_text = await reply_el.inner_text()

        # Capture screenshot of any media (images/videos) in this tweet
        tweet_screenshot = None
        media = await item.query_selector(
            ".still-image, .gallery-row, .video-container, .card-container, .attachments"
        )
        if media:
            try:
                import base64
                screenshot_bytes = await media.screenshot()
                if screenshot_bytes:
                    tweet_screenshot = base64.b64encode(screenshot_bytes).decode("utf-8")
                    logger.info("Captured media screenshot from tweet %s (%d bytes)", tweet_id, len(screenshot_bytes))
            except Exception as e:
                logger.debug("Failed to screenshot media in tweet %s: %s", tweet_id, e)

        return {
            "tweet_id": tweet_id,
            "tweet_text": tweet_text,
            "twitter_username": twitter_username,
            "parent_screenshot": tweet_screenshot,  # media from THIS tweet (overridden by parent in _enrich_reply)
            "parent_text": parent_text,
        }

    async def _enrich_reply(self, mention: dict) -> dict:
        """Click into the tweet on Nitter to get full thread context.

        Extracts parent tweet text and screenshots any media in the parent.
        The thread on Nitter shows items in order: parent(s) first, then the mention last.
        """
        if not self._working_host:
            return mention
        try:
            tweet_url = f"https://{self._working_host}/{mention['twitter_username']}/status/{mention['tweet_id']}"
            await self._page.goto(tweet_url, wait_until="domcontentloaded", timeout=15000)
            await self._page.wait_for_timeout(3000)

            # Refresh if needed
            items = await self._page.query_selector_all(".timeline-item, .main-tweet, .reply")
            if not items:
                await self._page.reload(wait_until="domcontentloaded", timeout=15000)
                await self._page.wait_for_timeout(3000)
                items = await self._page.query_selector_all(".timeline-item, .main-tweet, .reply")

            if len(items) < 2:
                return mention  # No parent — single tweet, not a reply

            # Everything except the last item is a parent tweet
            parent_texts = []
            for parent_item in items[:-1]:
                content_el = await parent_item.query_selector(".tweet-content")
                if content_el:
                    text = (await content_el.inner_text()).strip()
                    if text:
                        # Get the parent's username for attribution
                        user_el = await parent_item.query_selector(".username")
                        user = (await user_el.inner_text()).strip() if user_el else ""
                        parent_texts.append(f"{user}: {text}" if user else text)

                # Screenshot media in the parent (images, videos, cards)
                if not mention.get("parent_screenshot"):
                    media = await parent_item.query_selector(
                        ".still-image, .gallery-row, .video-container, .card-container"
                    )
                    if media:
                        try:
                            screenshot_bytes = await media.screenshot()
                            if screenshot_bytes:
                                import base64
                                mention["parent_screenshot"] = base64.b64encode(screenshot_bytes).decode("utf-8")
                                logger.info("Captured parent media screenshot (%d bytes)", len(screenshot_bytes))
                        except Exception:
                            pass

            if parent_texts:
                mention["parent_text"] = "\n\n".join(parent_texts)
                logger.info(
                    "Enriched mention %s with %d parent tweet(s)",
                    mention["tweet_id"], len(parent_texts),
                )

        except Exception as e:
            logger.warning("Failed to enrich reply %s: %s", mention["tweet_id"], e)

        return mention

    async def _submit_mention_to_backend(self, mention: dict):
        """POST the mention to our backend API to trigger a build."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{BACKEND_BASE}/api/twitter/ingest",
                    json=mention,
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    logger.info(
                        "Submitted mention from @%s → build %s",
                        mention["twitter_username"],
                        data.get("build_id", "?"),
                    )
                else:
                    logger.warning("Backend rejected mention: %s %s", resp.status_code, resp.text[:200])
        except Exception as e:
            logger.error("Failed to submit mention to backend: %s", e)

    async def _poll_loop(self):
        """Main async loop: scrape Nitter → submit mentions to backend."""
        async with async_playwright() as pw:
            await self._ensure_browser(pw)

            logger.info("Twitter scraper running via Nitter — checking every %ds (no login needed)", POLL_INTERVAL)

            while self._running:
                try:
                    mentions = await self._scrape_mentions()
                    for m in mentions:
                        self._seen_tweet_ids.add(m["tweet_id"])
                        # Enrich replies with parent context
                        prompt = m["tweet_text"].replace("@builddy", "").replace("@Builddy", "").strip()
                        if len(prompt) < 80 or "build" in prompt.lower():
                            m = await self._enrich_reply(m)
                        await self._submit_mention_to_backend(m)

                    if mentions:
                        logger.info("Processed %d new mentions via Nitter", len(mentions))
                        self._save_seen_ids()

                except Exception as e:
                    logger.error("Scraper poll error: %s", e)

                await asyncio.sleep(POLL_INTERVAL)

            if self._context:
                await self._context.close()

    def _run_in_thread(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._poll_loop())
        except Exception as e:
            logger.error("Scraper thread crashed: %s", e)
        finally:
            loop.close()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_in_thread, daemon=True)
        self._thread.start()
        logger.info("Twitter scraper thread started")

    def stop(self):
        self._running = False


scraper = TwitterMentionScraper()
