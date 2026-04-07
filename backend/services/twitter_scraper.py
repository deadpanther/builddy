"""
Playwright-based Twitter mention scraper.

Runs as a background thread, opens a persistent Chromium browser logged into
@builddy's X account, and polls the notifications/mentions tab for new tweets.
New mentions are forwarded to the backend API to trigger builds.

No paid Twitter API tier needed — Free tier still allows posting replies via
OAuth 1.0a, which the existing twitter.py service handles.
"""

import asyncio
import json
import logging
import re
import threading
import time
from pathlib import Path

import httpx
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from config import settings

logger = logging.getLogger(__name__)

# Persistent browser state so we stay logged in across restarts
BROWSER_STATE_DIR = Path(__file__).parent.parent / ".twitter_browser_state"
BRAVE_PATH = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"

# Backend API base
BACKEND_BASE = f"http://127.0.0.1:{settings.PORT}"

POLL_INTERVAL = 45  # seconds between checks
MENTIONS_URL = "https://x.com/notifications/mentions"
LOGIN_URL = "https://x.com/i/flow/login"


class TwitterMentionScraper:
    """Scrapes @builddy mentions from X using a real browser session."""

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._seen_tweet_ids: set[str] = set()
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def _ensure_browser(self, pw):
        """Launch Brave browser with persistent context (keeps login cookies)."""
        BROWSER_STATE_DIR.mkdir(parents=True, exist_ok=True)

        self._context = await pw.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_STATE_DIR),
            headless=False,  # visible for hackathon demo
            executable_path=BRAVE_PATH,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        # Use existing page or create one
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()

    async def _check_logged_in(self) -> bool:
        """Check if we're logged into X."""
        try:
            await self._page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=15000)
            await self._page.wait_for_timeout(3000)
            url = self._page.url
            # If redirected to login, we're not logged in
            if "login" in url or "flow" in url:
                return False
            # Check for the compose tweet button or home timeline
            home_indicator = await self._page.query_selector('[data-testid="SideNav_NewTweet_Button"]')
            return home_indicator is not None
        except Exception as e:
            logger.error("Login check failed: %s", e)
            return False

    async def _wait_for_manual_login(self):
        """Navigate to login page and wait for the user to log in manually."""
        logger.warning(
            "Not logged into @builddy on X. "
            "Please log in manually in the browser window that just opened."
        )
        await self._page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)

        # Wait up to 5 minutes for login
        for _ in range(60):
            await self._page.wait_for_timeout(5000)
            if await self._check_logged_in():
                logger.info("Successfully logged into X!")
                return True
        logger.error("Timed out waiting for manual X login")
        return False

    async def _scrape_mentions(self) -> list[dict]:
        """Navigate to mentions tab and extract new tweets."""
        mentions = []
        try:
            await self._page.goto(MENTIONS_URL, wait_until="domcontentloaded", timeout=20000)
            await self._page.wait_for_timeout(4000)

            # Find tweet articles on the mentions page
            articles = await self._page.query_selector_all('article[data-testid="tweet"]')
            logger.info("Found %d tweet articles on mentions page", len(articles))

            for article in articles[:15]:  # only check latest 15
                try:
                    mention = await self._parse_tweet_article(article)
                    if mention and mention["tweet_id"] not in self._seen_tweet_ids:
                        mentions.append(mention)
                except Exception as e:
                    logger.debug("Failed to parse tweet article: %s", e)
                    continue

        except Exception as e:
            logger.error("Failed to scrape mentions: %s", e)

        return mentions

    async def _parse_tweet_article(self, article) -> dict | None:
        """Extract tweet data from an article element."""
        # Get the tweet link to extract tweet ID
        # Tweet links look like: /username/status/1234567890
        links = await article.query_selector_all('a[href*="/status/"]')
        tweet_id = None
        for link in links:
            href = await link.get_attribute("href")
            if href and "/status/" in href:
                match = re.search(r"/status/(\d+)", href)
                if match:
                    tweet_id = match.group(1)
                    break

        if not tweet_id:
            return None

        # Get tweet text
        tweet_text_el = await article.query_selector('[data-testid="tweetText"]')
        tweet_text = ""
        if tweet_text_el:
            tweet_text = await tweet_text_el.inner_text()

        # Get username from the article
        username_els = await article.query_selector_all('a[role="link"] span')
        twitter_username = "unknown"
        for el in username_els:
            text = await el.inner_text()
            if text.startswith("@"):
                twitter_username = text.lstrip("@")
                break

        if not tweet_text:
            return None

        return {
            "tweet_id": tweet_id,
            "tweet_text": tweet_text,
            "twitter_username": twitter_username,
        }

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
                    logger.warning(
                        "Backend rejected mention: %s %s",
                        resp.status_code, resp.text[:200],
                    )
        except Exception as e:
            logger.error("Failed to submit mention to backend: %s", e)

    async def _poll_loop(self):
        """Main async loop: scrape mentions → submit to backend."""
        async with async_playwright() as pw:
            await self._ensure_browser(pw)

            # Check / wait for login
            if not await self._check_logged_in():
                logged_in = await self._wait_for_manual_login()
                if not logged_in:
                    logger.error("Cannot start scraper without X login")
                    return

            logger.info("Twitter scraper running — checking mentions every %ds", POLL_INTERVAL)

            while self._running:
                try:
                    mentions = await self._scrape_mentions()
                    for m in mentions:
                        self._seen_tweet_ids.add(m["tweet_id"])
                        await self._submit_mention_to_backend(m)

                    if mentions:
                        logger.info("Processed %d new mentions", len(mentions))

                except Exception as e:
                    logger.error("Scraper poll error: %s", e)

                await asyncio.sleep(POLL_INTERVAL)

            # Cleanup
            if self._context:
                await self._context.close()

    def _run_in_thread(self):
        """Entry point for the background thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._poll_loop())
        except Exception as e:
            logger.error("Scraper thread crashed: %s", e)
        finally:
            loop.close()

    def start(self):
        """Start the scraper in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_in_thread, daemon=True)
        self._thread.start()
        logger.info("Twitter scraper thread started")

    def stop(self):
        """Signal the scraper to stop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None
        logger.info("Twitter scraper stopped")


# Singleton
scraper = TwitterMentionScraper()
