"""Test Nitter-based @builddy mention scraping with thread enrichment.

Usage: uv run python test_twitter_login.py
"""
import asyncio
import re
from playwright.async_api import async_playwright

NITTER_URL = "https://nitter.net/search?f=tweets&q=%40builddy"
NITTER_HOST = "nitter.net"


async def test():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        print(f"[1] Loading {NITTER_URL}")
        await page.goto(NITTER_URL, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(3000)

        items = await page.query_selector_all(".timeline-item")
        if not items:
            print("    No items — refreshing...")
            await page.reload(wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(4000)
            items = await page.query_selector_all(".timeline-item")

        print(f"    Found {len(items)} tweets\n")

        # Parse all mentions from the search page
        mentions = []
        for i, item in enumerate(items[:10]):
            link = await item.query_selector('a[href*="/status/"]')
            href = await link.get_attribute("href") if link else ""
            match = re.search(r"/status/(\d+)", href or "")
            tid = match.group(1) if match else None
            if not tid:
                continue

            user_el = await item.query_selector(".username")
            user = (await user_el.inner_text()).lstrip("@") if user_el else "unknown"

            text_el = await item.query_selector(".tweet-content")
            text = await text_el.inner_text() if text_el else ""

            # Check if it's a reply
            reply_el = await item.query_selector(".replying-to")
            is_reply = reply_el is not None

            mentions.append({
                "tweet_id": tid,
                "username": user,
                "text": text.strip(),
                "is_reply": is_reply,
            })
            print(f"  [{i+1}] @{user} (tweet {tid}) {'[REPLY]' if is_reply else ''}")
            print(f"      {text.strip()[:150]}")

        # Now click into each mention to get full thread context
        print(f"\n{'='*60}")
        print("Enriching mentions with thread context...\n")

        for m in mentions:
            tweet_url = f"https://{NITTER_HOST}/{m['username']}/status/{m['tweet_id']}"
            print(f"  --- @{m['username']} tweet {m['tweet_id']} ---")
            print(f"  Loading: {tweet_url}")

            try:
                await page.goto(tweet_url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(3000)

                # Refresh if needed
                thread_items = await page.query_selector_all(".timeline-item, .main-tweet, .reply")
                if not thread_items:
                    await page.reload(wait_until="domcontentloaded", timeout=15000)
                    await page.wait_for_timeout(3000)
                    thread_items = await page.query_selector_all(".timeline-item, .main-tweet, .reply")

                print(f"  Thread items: {len(thread_items)}")

                # The main tweet and any parent tweets
                for j, ti in enumerate(thread_items):
                    ti_text_el = await ti.query_selector(".tweet-content")
                    ti_text = await ti_text_el.inner_text() if ti_text_el else ""
                    ti_user_el = await ti.query_selector(".username")
                    ti_user = await ti_user_el.inner_text() if ti_user_el else "?"

                    # Check for images/media
                    media = await ti.query_selector(".still-image, .gallery-row, .video-container, .card-container")
                    has_media = media is not None

                    label = "PARENT" if j < len(thread_items) - 1 else "MENTION"
                    print(f"    [{label}] {ti_user}: {ti_text.strip()[:200]} {'[HAS MEDIA]' if has_media else ''}")

                    # Screenshot the parent tweet if it has media
                    if label == "PARENT" and has_media:
                        try:
                            screenshot = await media.screenshot()
                            print(f"    [SCREENSHOT] Captured parent media ({len(screenshot)} bytes)")
                        except Exception:
                            print(f"    [SCREENSHOT] Failed to capture")

            except Exception as e:
                print(f"  Error: {e}")

            print()

        print("Browser open 30s...")
        await page.wait_for_timeout(30000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
