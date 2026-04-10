"""
Playwright-based Twitter mention scraper.

Runs as a background thread, opens a persistent Chromium browser logged into
@builddy's X account, and polls the notifications/mentions tab for new tweets.
New mentions are forwarded to the backend API to trigger builds.

No paid Twitter API tier needed — Free tier still allows posting replies via
OAuth 1.0a, which the existing twitter.py service handles.
"""

import asyncio
import logging
import os
import re
import threading
from pathlib import Path

import httpx
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from config import settings

logger = logging.getLogger(__name__)

# Persistent browser state so we stay logged in across restarts
BROWSER_STATE_DIR = Path(__file__).parent.parent / ".twitter_browser_state"
BRAVE_PATH = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"

# Detect environment: use Brave locally (macOS), Playwright Chromium on Railway/Linux
import platform
IS_RAILWAY = bool(os.environ.get("RAILWAY_ENVIRONMENT")) or not Path(BRAVE_PATH).exists()
IS_HEADLESS = IS_RAILWAY or platform.system() != "Darwin"

# Backend API base
BACKEND_BASE = f"http://127.0.0.1:{settings.PORT}"

POLL_INTERVAL = 120  # seconds between checks (was 45 — reduced to avoid log noise)
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
        """Launch browser with persistent context (keeps login cookies).

        Uses Brave on macOS (local dev), Playwright Chromium on Railway/Linux.
        """
        BROWSER_STATE_DIR.mkdir(parents=True, exist_ok=True)

        launch_kwargs = {
            "user_data_dir": str(BROWSER_STATE_DIR),
            "headless": IS_HEADLESS,
            "viewport": {"width": 1280, "height": 900},
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        }
        # Use Brave on macOS, Playwright's Chromium elsewhere
        if not IS_RAILWAY and Path(BRAVE_PATH).exists():
            launch_kwargs["executable_path"] = BRAVE_PATH

        self._context = await pw.chromium.launch_persistent_context(**launch_kwargs)
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

    async def _auto_login(self) -> bool:
        """Log into X automatically using credentials from env vars.

        Falls back to waiting for manual login if credentials aren't set
        or if Twitter presents a challenge (captcha, 2FA, etc).
        """
        username = settings.TWITTER_USERNAME
        password = settings.TWITTER_PASSWORD

        if not username or not password:
            if IS_HEADLESS:
                logger.error(
                    "TWITTER_USERNAME and TWITTER_PASSWORD required for headless login. "
                    "Set them in .env or Railway env vars."
                )
                return False
            # Local dev: wait for manual login in visible browser
            logger.warning("No Twitter credentials — please log in manually in the browser window.")
            await self._page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
            for _ in range(60):
                await self._page.wait_for_timeout(5000)
                if await self._check_logged_in():
                    logger.info("Successfully logged into X!")
                    return True
            logger.error("Timed out waiting for manual X login")
            return False

        # ── Auto-login flow ──
        logger.info("Attempting auto-login to X as %s...", username)
        try:
            await self._page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
            await self._page.wait_for_timeout(5000)  # extra wait for JS to render login form

            # Debug: log what we see
            page_url = self._page.url
            page_title = await self._page.title()
            logger.info("Login page loaded: url=%s title=%s", page_url, page_title[:60])

            # Step 1: Find and fill username — try multiple selectors
            username_input = None
            username_selectors = [
                'input[autocomplete="username"]',
                'input[name="text"]',
                'input[name="session[username_or_email]"]',
                'input[type="text"]',
            ]
            for sel in username_selectors:
                try:
                    username_input = await self._page.wait_for_selector(sel, timeout=5000, state="visible")
                    if username_input:
                        logger.info("Found username input with selector: %s", sel)
                        break
                except Exception:
                    continue

            if not username_input:
                # Last resort: find any visible input on the page
                all_inputs = await self._page.query_selector_all("input:visible")
                logger.warning("No username selector matched. Found %d visible inputs.", len(all_inputs))
                if all_inputs:
                    username_input = all_inputs[0]
                else:
                    logger.error("No input fields found on login page at all")
                    return False

            await username_input.click()
            # Use type() instead of fill() — simulates real keystrokes so Twitter
            # enables the Next button (fill() doesn't trigger input events properly)
            await username_input.type(username, delay=50)
            await self._page.wait_for_timeout(1000)

            # Click "Next" button — use JS click as fallback since normal click
            # sometimes doesn't register on Twitter's React buttons
            next_btn = None
            for sel in ['[role="button"]:has-text("Next")', 'button:has-text("Next")', '[data-testid="LoginForm_Next_Button"]']:
                next_btn = await self._page.query_selector(sel)
                if next_btn:
                    logger.info("Found Next button with selector: %s", sel)
                    break
            if next_btn:
                # Try JS click first (more reliable on SPAs), fall back to regular click
                await next_btn.evaluate("el => el.click()")
                logger.info("Clicked Next button via JS")
            else:
                logger.info("No Next button found, pressing Enter")
                await self._page.keyboard.press("Enter")
            await self._page.wait_for_timeout(5000)

            logger.info("After Next — URL: %s", self._page.url)

            # Step 2: Check for unusual activity / phone verification challenge
            challenge_input = await self._page.query_selector(
                'input[data-testid="ocfEnterTextTextInput"]'
            )
            if challenge_input:
                logger.warning("Twitter verification challenge detected — entering username as answer")
                await challenge_input.fill(username)
                verify_btn = await self._page.query_selector(
                    '[data-testid="ocfEnterTextNextButton"], [role="button"]:has-text("Next")'
                )
                if verify_btn:
                    await verify_btn.click()
                await self._page.wait_for_timeout(3000)

            # Step 3: Enter password — wait with retries for the page to transition
            password_input = None
            password_selectors = ['input[name="password"]', 'input[type="password"]', 'input[autocomplete="current-password"]']
            for attempt in range(3):  # retry up to 3 times (12s total)
                for sel in password_selectors:
                    try:
                        password_input = await self._page.wait_for_selector(sel, timeout=4000, state="visible")
                        if password_input:
                            logger.info("Found password input with selector: %s (attempt %d)", sel, attempt + 1)
                            break
                    except Exception:
                        continue
                if password_input:
                    break
                logger.info("Password field not found yet (attempt %d/3), waiting...", attempt + 1)
                await self._page.wait_for_timeout(2000)

            if not password_input:
                # Log page content for debugging
                page_text = await self._page.inner_text("body")
                logger.error(
                    "Could not find password field. URL: %s | Page text (first 500 chars): %s",
                    self._page.url, page_text[:500],
                )
                return False

            await password_input.click()
            await password_input.type(password, delay=30)
            await self._page.wait_for_timeout(1000)

            # Click "Log in" button
            login_btn = None
            for sel in ['[data-testid="LoginForm_Login_Button"]', '[role="button"]:has-text("Log in")', 'button:has-text("Log in")']:
                login_btn = await self._page.query_selector(sel)
                if login_btn:
                    break
            if login_btn:
                await login_btn.evaluate("el => el.click()")
                logger.info("Clicked Log in button via JS")
            else:
                await self._page.keyboard.press("Enter")

            # Wait for redirect
            await self._page.wait_for_timeout(6000)

            if await self._check_logged_in():
                logger.info("Auto-login to X successful!")
                return True

            logger.warning(
                "Auto-login didn't reach home — Twitter may require 2FA or captcha. "
                "Current URL: %s", self._page.url
            )
            return False

        except Exception as e:
            logger.error("Auto-login failed: %s", e)
            return False

    async def _scrape_mentions(self) -> list[dict]:
        """Navigate to mentions tab and extract new tweets."""
        mentions = []
        try:
            await self._page.goto(MENTIONS_URL, wait_until="domcontentloaded", timeout=20000)
            await self._page.wait_for_timeout(4000)

            # Find tweet articles on the mentions page
            articles = await self._page.query_selector_all('article[data-testid="tweet"]')
            logger.debug("Found %d tweet articles on mentions page", len(articles))

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
            "parent_screenshot": None,  # filled by _enrich_reply
            "parent_text": None,
        }

    async def _enrich_reply(self, mention: dict) -> dict:
        """If the mention is a reply to another tweet, screenshot the parent tweet's content."""
        try:
            # Navigate to the mention tweet to see the parent
            tweet_url = f"https://x.com/i/status/{mention['tweet_id']}"
            await self._page.goto(tweet_url, wait_until="domcontentloaded", timeout=15000)
            await self._page.wait_for_timeout(3000)

            # Find all tweet articles — the parent tweet is typically the FIRST one
            articles = await self._page.query_selector_all('article[data-testid="tweet"]')
            if len(articles) < 2:
                return mention  # not a reply or can't find parent

            parent_article = articles[0]

            # Get parent tweet text
            parent_text_el = await parent_article.query_selector('[data-testid="tweetText"]')
            if parent_text_el:
                mention["parent_text"] = await parent_text_el.inner_text()

            # Also grab any link card title/description (e.g. "Turn any TV into a retro split-flap display")
            card_title = await parent_article.query_selector('[data-testid="card.layoutLarge.detail"] span, [data-testid="card.layoutSmall.detail"] span')
            if card_title:
                card_text = await card_title.inner_text()
                if card_text and mention["parent_text"]:
                    mention["parent_text"] += f"\n\nLinked page: {card_text}"
                elif card_text:
                    mention["parent_text"] = card_text

            # Screenshot the parent tweet's media (images, videos, cards)
            # Look for media container
            media = await parent_article.query_selector('[data-testid="tweetPhoto"], [data-testid="videoPlayer"], [data-testid="card.wrapper"]')
            if media:
                screenshot_bytes = await media.screenshot()
            else:
                # Screenshot the whole parent tweet article
                screenshot_bytes = await parent_article.screenshot()

            if screenshot_bytes:
                import base64
                mention["parent_screenshot"] = base64.b64encode(screenshot_bytes).decode("utf-8")
                logger.info(
                    "Captured parent tweet screenshot for @%s (%d bytes)",
                    mention["twitter_username"], len(screenshot_bytes),
                )

        except Exception as e:
            logger.warning("Failed to enrich reply for tweet %s: %s", mention["tweet_id"], e)

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
                logged_in = await self._auto_login()
                if not logged_in:
                    logger.error("Cannot start scraper without X login")
                    return

            logger.info("Twitter scraper running — checking mentions every %ds", POLL_INTERVAL)

            while self._running:
                try:
                    # Scraping uses Playwright + httpx only — no GLM. Each successful ingest
                    # starts a background pipeline on the server; many new mentions in one poll
                    # means many concurrent pipelines unless GLM_MAX_CONCURRENT_REQUESTS caps API use.
                    mentions = await self._scrape_mentions()
                    for m in mentions:
                        self._seen_tweet_ids.add(m["tweet_id"])
                        # If the mention text is short (e.g. "Build me" or "Build me this"),
                        # it's likely a reply to another tweet — screenshot the parent
                        prompt = m["tweet_text"].replace("@builddy", "").replace("@Builddy", "").strip()
                        if len(prompt) < 80 or "build" in prompt.lower():
                            m = await self._enrich_reply(m)
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
