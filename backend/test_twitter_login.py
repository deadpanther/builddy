"""Test fetching a reply thread from multiple Nitter instances.

Usage: uv run python test_twitter_login.py
"""
import asyncio
from playwright.async_api import async_playwright

TWEET_ID = "2042541159986401557"
USERNAME = "keval_shah14"

NITTER_HOSTS = ["nitter.net", "nitter.poast.org", "xcancel.com", "nitter.privacydev.net"]


async def test():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        for host in NITTER_HOSTS:
            url = f"https://{host}/{USERNAME}/status/{TWEET_ID}"
            print(f"\n{'='*60}")
            print(f"Trying: {url}")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(3000)

                body = await page.inner_text("body")
                if "not found" in body.lower():
                    # Try refresh
                    await page.reload(wait_until="domcontentloaded", timeout=15000)
                    await page.wait_for_timeout(3000)
                    body = await page.inner_text("body")

                if "not found" in body.lower():
                    print(f"  {host}: Tweet not found")
                    continue

                items = await page.query_selector_all(".timeline-item")
                print(f"  {host}: {len(items)} thread items")

                for i, item in enumerate(items):
                    user_el = await item.query_selector(".username")
                    text_el = await item.query_selector(".tweet-content")
                    user = await user_el.inner_text() if user_el else "?"
                    text = (await text_el.inner_text()).strip()[:150] if text_el else "?"
                    label = "PARENT" if i < len(items) - 1 else "MENTION"
                    print(f"  [{label}] {user}: {text}")

                if items:
                    print(f"\n  SUCCESS with {host}!")
                    print("  Browser open 30s...")
                    await page.wait_for_timeout(30000)
                    await browser.close()
                    return

            except Exception as e:
                print(f"  {host}: Error — {e}")

        print("\nAll hosts failed. Browser open 30s...")
        await page.wait_for_timeout(30000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
