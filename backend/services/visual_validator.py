"""
Playwright-based visual validator.

Loads generated HTML in a headless browser, captures console errors and a
screenshot, then feeds both back to GLM-5V-Turbo for self-correction.
"""

import base64
import logging
import tempfile
from pathlib import Path

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


async def validate_html(html_code: str, viewport_width: int = 1280, viewport_height: int = 900) -> dict:
    """Load HTML in headless Chromium, capture errors + screenshot.

    Returns:
        {
            "console_errors": ["error1", "error2"],
            "screenshot_base64": "base64-encoded PNG",
            "page_title": "...",
            "has_errors": bool,
        }
    """
    console_errors: list[str] = []
    screenshot_b64 = ""
    page_title = ""

    # Write HTML to a temp file
    tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
    tmp.write(html_code)
    tmp.close()
    tmp_path = Path(tmp.name)

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": viewport_width, "height": viewport_height},
            )
            page = await context.new_page()

            # Capture console errors
            page.on("console", lambda msg: (
                console_errors.append(f"[{msg.type}] {msg.text}")
                if msg.type in ("error", "warning") else None
            ))

            # Capture uncaught exceptions
            page.on("pageerror", lambda exc: console_errors.append(f"[exception] {exc}"))

            # Load the page
            file_url = f"file://{tmp_path.resolve()}"
            await page.goto(file_url, wait_until="networkidle", timeout=15000)

            # Wait a bit for animations and async init
            await page.wait_for_timeout(2000)

            # Get page title
            page_title = await page.title()

            # Take screenshot
            screenshot_bytes = await page.screenshot(full_page=True)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            await browser.close()

    except Exception as e:
        logger.error("Visual validation failed: %s", e)
        console_errors.append(f"[validator] Failed to load page: {e}")
    finally:
        tmp_path.unlink(missing_ok=True)

    return {
        "console_errors": console_errors,
        "screenshot_base64": screenshot_b64,
        "page_title": page_title,
        "has_errors": len(console_errors) > 0,
    }


async def validate_deployed_url(url: str, viewport_width: int = 1280, viewport_height: int = 900) -> dict:
    """Same as validate_html but loads from a live URL."""
    console_errors: list[str] = []
    screenshot_b64 = ""
    page_title = ""

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": viewport_width, "height": viewport_height},
            )
            page = await context.new_page()

            page.on("console", lambda msg: (
                console_errors.append(f"[{msg.type}] {msg.text}")
                if msg.type in ("error", "warning") else None
            ))
            page.on("pageerror", lambda exc: console_errors.append(f"[exception] {exc}"))

            await page.goto(url, wait_until="networkidle", timeout=15000)
            await page.wait_for_timeout(2000)

            page_title = await page.title()
            screenshot_bytes = await page.screenshot(full_page=True)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            await browser.close()

    except Exception as e:
        logger.error("Visual validation of %s failed: %s", url, e)
        console_errors.append(f"[validator] Failed to load page: {e}")

    return {
        "console_errors": console_errors,
        "screenshot_base64": screenshot_b64,
        "page_title": page_title,
        "has_errors": len(console_errors) > 0,
    }
