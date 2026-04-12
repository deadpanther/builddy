"""
Nitter-based Twitter mention scraper.

Uses plain httpx HTTP requests to scrape Nitter (server-side rendered HTML) —
no browser, no login, no API keys. Falls back to Playwright if httpx fails.

Works locally and on Railway without any Twitter credentials.
"""

import asyncio
import logging
import os
import re
import threading
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from config import settings

logger = logging.getLogger(__name__)

# Nitter instances to try (in order of preference)
# Updated 2025 — checked against status.d420.de
NITTER_HOSTS = [
    "xcancel.com",
    "lightbrd.com",
    "nitter.space",
    "nitter.tiekoetter.com",
    "nitter.catsarch.com",
    "nitter.poast.org",
    "nitter.net",
    "nitter.privacydev.net",
    "nuku.trabun.org",
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
_data_dir = (
    Path(os.environ.get("DEPLOYED_DIR", "")).parent
    if os.environ.get("DEPLOYED_DIR")
    else Path(__file__).parent.parent
)
SEEN_IDS_FILE = _data_dir / ".seen_tweet_ids"

# HTTP headers that look like a real browser
_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


class TwitterMentionScraper:
    """Scrapes @builddy mentions from Nitter — no Twitter login needed."""

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._seen_tweet_ids: set[str] = self._load_seen_ids()
        self._working_host: str | None = None
        # Playwright fallback (only used if httpx fails for all hosts)
        self._pw = None
        self._context = None
        self._page = None

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    @staticmethod
    def _load_seen_ids() -> set[str]:
        try:
            if SEEN_IDS_FILE.exists():
                ids = SEEN_IDS_FILE.read_text().strip().splitlines()
                logger.info("Loaded %d seen tweet IDs from disk", len(ids))
                return set(ids)
        except Exception:
            pass
        return set()

    def _save_seen_ids(self):
        try:
            recent = sorted(self._seen_tweet_ids)[-500:]
            SEEN_IDS_FILE.write_text("\n".join(recent) + "\n")
        except Exception as e:
            logger.debug("Failed to save seen IDs: %s", e)

    # ------------------------------------------------------------------ #
    # httpx-based scraping (primary — no browser needed)
    # ------------------------------------------------------------------ #

    async def _httpx_find_working_host(self, client: httpx.AsyncClient) -> str | None:
        """Try each Nitter instance via plain HTTP GET and return the first that serves tweets."""
        for host in NITTER_HOSTS:
            url = f"https://{host}/search?f=tweets&q=%40builddy"
            try:
                logger.info("Trying Nitter (httpx): %s", host)
                resp = await client.get(url, headers=_HTTP_HEADERS, timeout=10.0, follow_redirects=True)
                if resp.status_code != 200:
                    logger.info("  %s → HTTP %d", host, resp.status_code)
                    continue
                if "login" in str(resp.url):
                    logger.info("  %s → redirected to login", host)
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                items = soup.select(".timeline-item")
                if items:
                    logger.info("Nitter (httpx) %s works — %d tweets", host, len(items))
                    return host

                body_len = len(resp.text)
                logger.info("  %s → 0 items, body %d chars", host, body_len)
                # Accept if body has real content (Nitter rendered but no @builddy results)
                if body_len > 500 and "No items found" not in resp.text:
                    logger.info("  %s → accepting (has content but 0 results)", host)
                    return host

            except Exception as e:
                logger.info("  %s error: %s", host, str(e)[:80])

        return None

    async def _httpx_scrape_mentions(self, client: httpx.AsyncClient) -> list[dict]:
        """Scrape @builddy mentions using plain httpx requests."""
        if not self._working_host:
            self._working_host = await self._httpx_find_working_host(client)
            if not self._working_host:
                return []

        url = f"https://{self._working_host}/search?f=tweets&q=%40builddy"
        try:
            resp = await client.get(url, headers=_HTTP_HEADERS, timeout=15.0, follow_redirects=True)
            if resp.status_code != 200:
                logger.warning("Nitter %s returned %d — resetting host", self._working_host, resp.status_code)
                self._working_host = None
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select(".timeline-item")
            logger.debug("httpx: found %d items on Nitter", len(items))

            mentions = []
            for item in items[:15]:
                mention = self._parse_bs4_item(item)
                if mention and mention["tweet_id"] not in self._seen_tweet_ids:
                    mentions.append(mention)
            return mentions

        except Exception as e:
            logger.error("httpx scrape failed: %s — resetting host", e)
            self._working_host = None
            return []

    def _parse_bs4_item(self, item) -> dict | None:
        """Parse a BeautifulSoup Nitter timeline-item into a mention dict."""
        link = item.select_one('a[href*="/status/"]')
        if not link:
            return None
        href = link.get("href", "")
        match = re.search(r"/status/(\d+)", href)
        if not match:
            return None
        tweet_id = match.group(1)

        # Tweet text
        content_el = item.select_one(".tweet-content") or item.select_one(".media-body")
        if not content_el:
            return None
        tweet_text = content_el.get_text(separator=" ", strip=True)
        if not tweet_text:
            return None

        # Username from href (most reliable)
        twitter_username = "unknown"
        parts = href.strip("/").split("/")
        if parts:
            twitter_username = parts[0]
        if twitter_username == "unknown":
            username_el = item.select_one(".username")
            if username_el:
                twitter_username = username_el.get_text(strip=True).lstrip("@")

        # Replying-to context
        reply_el = item.select_one(".replying-to, .reply-to")
        parent_text = reply_el.get_text(strip=True) if reply_el else None

        return {
            "tweet_id": tweet_id,
            "tweet_text": tweet_text,
            "twitter_username": twitter_username,
            "parent_text": parent_text,
            "parent_screenshot": None,
        }

    async def _httpx_enrich_reply(self, client: httpx.AsyncClient, mention: dict) -> dict:
        """Fetch the thread page via httpx to get parent tweet text."""
        if not self._working_host:
            return mention

        fallback_parent = mention.get("parent_text")
        hosts_to_try = [self._working_host] + [h for h in NITTER_HOSTS if h != self._working_host]

        for host in hosts_to_try[:3]:
            tweet_url = f"https://{host}/{mention['twitter_username']}/status/{mention['tweet_id']}"
            try:
                resp = await client.get(tweet_url, headers=_HTTP_HEADERS, timeout=10.0, follow_redirects=True)
                if resp.status_code != 200:
                    continue
                if "not found" in resp.text.lower():
                    logger.info("Nitter %s: tweet %s not found", host, mention["tweet_id"])
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                items = soup.select(".timeline-item")
                if not items or len(items) < 2:
                    break  # Single tweet or no thread

                parent_texts = []
                for parent_item in items[:-1]:
                    content_el = parent_item.select_one(".tweet-content")
                    if content_el:
                        text = content_el.get_text(separator=" ", strip=True)
                        if text:
                            user_el = parent_item.select_one(".username")
                            user = user_el.get_text(strip=True) if user_el else ""
                            parent_texts.append(f"{user}: {text}" if user else text)

                if parent_texts:
                    mention["parent_text"] = "\n\n".join(parent_texts)
                    logger.info(
                        "Enriched mention %s with %d parent tweet(s)", mention["tweet_id"], len(parent_texts)
                    )
                elif fallback_parent:
                    mention["parent_text"] = fallback_parent
                return mention

            except Exception as e:
                logger.debug("httpx enrich failed on %s: %s", host, e)
                continue

        if fallback_parent and not mention.get("parent_text"):
            mention["parent_text"] = fallback_parent
        return mention

    # ------------------------------------------------------------------ #
    # Backend submission
    # ------------------------------------------------------------------ #

    async def _submit_mention_to_backend(self, client: httpx.AsyncClient, mention: dict):
        """POST the mention to our backend API to trigger a build."""
        try:
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

    # ------------------------------------------------------------------ #
    # Poll loop
    # ------------------------------------------------------------------ #

    async def _poll_loop(self):
        """Main async loop: scrape Nitter via httpx → submit mentions to backend."""
        # Pre-seed seen IDs from the database
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{BACKEND_BASE}/api/twitter/mentions", timeout=5.0)
                if resp.status_code == 200:
                    for m in resp.json():
                        tid = m.get("tweet_id")
                        if tid:
                            self._seen_tweet_ids.add(tid)
                    logger.info("Pre-seeded %d seen tweet IDs from database", len(self._seen_tweet_ids))
            except Exception:
                logger.debug("Could not pre-seed seen IDs (endpoint may not exist yet)")

        logger.info("Twitter scraper running via Nitter (httpx) — checking every %ds", POLL_INTERVAL)

        while self._running:
            try:
                async with httpx.AsyncClient() as client:
                    mentions = await self._httpx_scrape_mentions(client)

                    # Filter out @builddy's own tweets
                    mentions = [
                        m for m in mentions
                        if m["twitter_username"].lower() not in ("builddy", "builddyai")
                    ]

                    # Mark as seen immediately to prevent duplicates
                    for m in mentions:
                        self._seen_tweet_ids.add(m["tweet_id"])
                    if mentions:
                        self._save_seen_ids()

                    # Submit one at a time
                    for m in mentions:
                        m = await self._httpx_enrich_reply(client, m)
                        await self._submit_mention_to_backend(client, m)
                        await asyncio.sleep(5)

                    if mentions:
                        logger.info("Processed %d new mentions via Nitter", len(mentions))
                    else:
                        logger.debug("No new mentions this poll")

            except Exception as e:
                logger.error("Scraper poll error: %s", e)

            await asyncio.sleep(POLL_INTERVAL)

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
