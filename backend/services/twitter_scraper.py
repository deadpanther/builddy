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
    "nitter.cz",
    "nitter.1d4.us",
    "nitter.woodland.cafe",
]

POLL_INTERVAL = 40  # seconds between checks

# Backend API base
BACKEND_BASE = f"http://127.0.0.1:{settings.PORT}"

# Detect environment
IS_RAILWAY = bool(os.environ.get("RAILWAY_ENVIRONMENT"))


# Persist seen IDs on Railway volume (/app/data), or local backend dir
_data_dir = Path(os.environ.get("DEPLOYED_DIR", "")).parent if os.environ.get("DEPLOYED_DIR") else Path(__file__).parent.parent
SEEN_IDS_FILE = _data_dir / ".seen_tweet_ids"

# Chrome args for containerized/headless environments
CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-setuid-sandbox",
    "--no-zygote",
    "--single-process",
]


class TwitterMentionScraper:
    """Scrapes @builddy mentions from Nitter — no Twitter login needed."""

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._seen_tweet_ids: set[str] = self._load_seen_ids()
        self._context = None
        self._page = None
        self._pw = None
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

    def _clean_chrome_locks(self, state_dir: Path):
        """Remove stale Chrome lock files left by a crashed browser."""
        for lock_file in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
            lock_path = state_dir / lock_file
            if lock_path.exists():
                try:
                    lock_path.unlink()
                    logger.info("Removed stale Chrome lock: %s", lock_file)
                except Exception:
                    pass

    async def _ensure_browser(self):
        """Launch (or re-launch) the Chromium browser."""
        if not self._pw:
            raise RuntimeError("Playwright not started")

        # Close any existing context first
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
            self._page = None

        state_dir = (
            _data_dir / ".nitter_browser_state"
            if IS_RAILWAY
            else Path(__file__).parent.parent / ".nitter_browser_state"
        )
        state_dir.mkdir(parents=True, exist_ok=True)
        self._clean_chrome_locks(state_dir)

        try:
            self._context = await self._pw.chromium.launch_persistent_context(
                user_data_dir=str(state_dir),
                headless=True,  # always headless (Railway has no display)
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                ),
                args=CHROMIUM_ARGS,
            )
            self._page = (
                self._context.pages[0]
                if self._context.pages
                else await self._context.new_page()
            )
            logger.info("Browser launched (state=%s)", state_dir)
        except Exception as e:
            logger.error("Failed to launch browser: %s", e)
            raise

    def _is_browser_alive(self) -> bool:
        """Return True if the page is still usable."""
        try:
            return self._page is not None and not self._page.is_closed()
        except Exception:
            return False

    async def _find_working_host(self) -> str | None:
        """Try Nitter instances until one works."""
        for host in NITTER_HOSTS:
            url = f"https://{host}/search?f=tweets&q=%40builddy"
            try:
                logger.info("Trying Nitter instance: %s", host)
                resp = await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await self._page.wait_for_timeout(3000)

                status = resp.status if resp else 0
                current_url = self._page.url

                if status != 200:
                    logger.info("  %s returned HTTP %d", host, status)
                    continue
                if "login" in current_url:
                    logger.info("  %s redirected to login", host)
                    continue

                # Nitter sometimes needs a refresh on first load
                items = await self._page.query_selector_all(".timeline-item")
                if not items:
                    logger.info("  %s: no items on first load, refreshing...", host)
                    await self._page.reload(wait_until="domcontentloaded", timeout=15000)
                    await self._page.wait_for_timeout(4000)
                    items = await self._page.query_selector_all(".timeline-item")

                if items:
                    logger.info("Nitter instance %s works! Found %d tweets", host, len(items))
                    return host

                # Check if page has any content at all
                body = await self._page.inner_text("body")
                body_len = len(body.strip())
                logger.info(
                    "  %s: %d items, body %d chars. First 200: %s",
                    host, len(items), body_len, body[:200],
                )

                if body_len > 200 and "No items found" not in body:
                    logger.info("Nitter %s has content (body looks valid)", host)
                    return host

            except Exception as e:
                err = str(e)
                logger.info("  %s error: %s", host, err[:100])
                # If the browser itself died, bail early — poll loop will restart it
                if "closed" in err.lower():
                    logger.warning("Browser closed during host search — aborting")
                    return None

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

        # Get username from the status link (most reliable)
        # href is like /Neelkamalshah/status/12345
        twitter_username = "unknown"
        if href:
            parts = href.strip("/").split("/")
            if parts:
                twitter_username = parts[0]
        # Fallback: try .username element
        if twitter_username == "unknown":
            username_el = await item.query_selector(".username")
            if username_el:
                raw = await username_el.inner_text()
                twitter_username = raw.lstrip("@").strip()

        # Check if it's a reply — capture the "Replying to @someone" text
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

        # For replies without media: screenshot the whole card as visual context
        if reply_el and not tweet_screenshot:
            try:
                import base64
                card_bytes = await item.screenshot()
                if card_bytes:
                    tweet_screenshot = base64.b64encode(card_bytes).decode("utf-8")
                    logger.info("Captured search card screenshot for reply tweet %s (%d bytes)", tweet_id, len(card_bytes))
            except Exception:
                pass

        return {
            "tweet_id": tweet_id,
            "tweet_text": tweet_text,
            "twitter_username": twitter_username,
            "parent_screenshot": tweet_screenshot,
            "parent_text": parent_text,
        }

    async def _enrich_reply(self, mention: dict) -> dict:
        """Click into the tweet on Nitter to get full thread context.

        Extracts parent tweet text and screenshots any media in the parent.
        Falls back to the "Replying to" text from the search page if Nitter
        can't load the individual tweet (returns "Tweet not found").
        """
        if not self._working_host:
            return mention

        # Save the search-page parent_text as fallback (e.g. "Replying to @someone")
        fallback_parent = mention.get("parent_text")

        try:
            # Try multiple Nitter hosts for thread pages (some hosts can't find certain tweets)
            hosts_to_try = [self._working_host] + [h for h in NITTER_HOSTS if h != self._working_host]
            items = []

            for host in hosts_to_try[:3]:  # try up to 3 hosts
                tweet_url = f"https://{host}/{mention['twitter_username']}/status/{mention['tweet_id']}"
                try:
                    await self._page.goto(tweet_url, wait_until="domcontentloaded", timeout=12000)
                    await self._page.wait_for_timeout(3000)

                    body_text = await self._page.inner_text("body")
                    if "not found" in body_text.lower():
                        logger.info("Nitter %s can't find tweet %s, trying next host", host, mention["tweet_id"])
                        continue

                    items = await self._page.query_selector_all(".timeline-item")
                    if not items:
                        await self._page.reload(wait_until="domcontentloaded", timeout=12000)
                        await self._page.wait_for_timeout(3000)
                        items = await self._page.query_selector_all(".timeline-item")

                    if items:
                        logger.info("Thread loaded from %s for tweet %s: %d items", host, mention["tweet_id"], len(items))
                        break
                except Exception:
                    continue

            if not items:
                logger.warning("No Nitter host could load tweet %s — using search page context", mention["tweet_id"])
                mention["parent_text"] = fallback_parent
                return mention

            logger.info("Thread for tweet %s: %d items", mention["tweet_id"], len(items))

            if len(items) < 2:
                return mention  # No parent — single tweet, not a reply

            # Everything except the last item is a parent tweet
            parent_texts = []
            for parent_item in items[:-1]:
                content_el = await parent_item.query_selector(".tweet-content")
                if content_el:
                    text = (await content_el.inner_text()).strip()
                    if text:
                        user_el = await parent_item.query_selector(".username")
                        user = (await user_el.inner_text()).strip() if user_el else ""
                        parent_texts.append(f"{user}: {text}" if user else text)

                # Screenshot media in the parent
                if not mention.get("parent_screenshot"):
                    media = await parent_item.query_selector(
                        ".still-image, .gallery-row, .video-container, .card-container, .attachments"
                    )
                    if media:
                        try:
                            import base64
                            screenshot_bytes = await media.screenshot()
                            if screenshot_bytes:
                                mention["parent_screenshot"] = base64.b64encode(screenshot_bytes).decode("utf-8")
                                logger.info("Captured parent media screenshot (%d bytes)", len(screenshot_bytes))
                        except Exception:
                            pass

            if parent_texts:
                mention["parent_text"] = "\n\n".join(parent_texts)
                logger.info("Enriched mention %s with %d parent tweet(s)", mention["tweet_id"], len(parent_texts))
            elif fallback_parent:
                # Thread loaded but no parent content extracted — use search page fallback
                mention["parent_text"] = fallback_parent

        except Exception as e:
            logger.warning("Failed to enrich reply %s: %s — keeping search page context", mention["tweet_id"], e)
            # Preserve the fallback from search page
            if fallback_parent and not mention.get("parent_text"):
                mention["parent_text"] = fallback_parent

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
                    if data.get("status") == "duplicate":
                        logger.debug("Skipped duplicate mention: tweet %s", mention["tweet_id"])
                    else:
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
            self._pw = pw
            await self._ensure_browser()

            # Pre-seed seen IDs from the database (mentions already ingested)
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"{BACKEND_BASE}/api/twitter/mentions", timeout=5.0)
                    if resp.status_code == 200:
                        for m in resp.json():
                            tid = m.get("tweet_id")
                            if tid:
                                self._seen_tweet_ids.add(tid)
                        logger.info("Pre-seeded %d seen tweet IDs from database", len(self._seen_tweet_ids))
            except Exception:
                logger.debug("Could not pre-seed seen IDs from database (endpoint may not exist)")

            logger.info("Twitter scraper running via Nitter — checking every %ds (no login needed)", POLL_INTERVAL)

            while self._running:
                try:
                    # Restart browser if it died
                    if not self._is_browser_alive():
                        logger.warning("Browser page is closed — restarting browser...")
                        await self._ensure_browser()
                        self._working_host = None

                    mentions = await self._scrape_mentions()

                    # Filter out @builddy's own tweets (promo tweets, not build requests)
                    mentions = [
                        m for m in mentions
                        if m["twitter_username"].lower() not in ("builddy", "builddyai")
                    ]

                    # Mark all as seen IMMEDIATELY (before submitting) to prevent
                    # duplicates if the next poll fires before submission finishes
                    for m in mentions:
                        self._seen_tweet_ids.add(m["tweet_id"])
                    if mentions:
                        self._save_seen_ids()

                    # Submit one at a time with delay to avoid GLM rate limit storms
                    for m in mentions:
                        # Enrich ALL mentions with thread context (click into each tweet)
                        m = await self._enrich_reply(m)
                        await self._submit_mention_to_backend(m)
                        # Wait between submissions so builds don't all hit GLM at once
                        await asyncio.sleep(5)

                    if mentions:
                        logger.info("Processed %d new mentions via Nitter", len(mentions))

                except Exception as e:
                    err_str = str(e)
                    if "closed" in err_str.lower():
                        logger.warning("Browser context died during poll: %s — restarting", e)
                        try:
                            await self._ensure_browser()
                            self._working_host = None
                        except Exception as restart_err:
                            logger.error("Failed to restart browser: %s", restart_err)
                    else:
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
