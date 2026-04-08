"""Autopilot Error Recovery — iteratively fixes failing apps until they work."""

import asyncio
import logging

from agent.llm import chat_with_reasoning, vision_chat, chat
from agent.prompts import AUTOPILOT_FIX_SYSTEM, VISUAL_FIX_SYSTEM
from config import settings

logger = logging.getLogger(__name__)

MAX_AUTOPILOT_ITERATIONS = 3


async def autopilot_fix_loop(
    code: str,
    on_iteration: callable | None = None,
) -> tuple[str, int]:
    """Run the app in a headless browser, detect errors, fix them, repeat.

    Returns (fixed_code, iterations_used).
    The on_iteration callback is called with (iteration, errors_found, screenshot_available)
    for progress reporting.
    """
    current_code = code
    iterations = 0

    for i in range(MAX_AUTOPILOT_ITERATIONS):
        iterations = i + 1

        # Step 1: Validate in headless browser
        try:
            from services.visual_validator import validate_html
            result = await asyncio.wait_for(
                validate_html(current_code, viewport_width=1280, viewport_height=800),
                timeout=30,
            )
        except Exception as e:
            logger.warning("Autopilot browser validation failed on iteration %d: %s", iterations, e)
            break

        errors = result.get("console_errors", [])
        screenshot_b64 = result.get("screenshot_base64")
        has_errors = result.get("has_errors", False)

        if on_iteration:
            on_iteration(iterations, len(errors), bool(screenshot_b64))

        # Step 2: If no errors and we have a screenshot, we're done
        if not has_errors:
            logger.info("Autopilot: app is clean after %d iteration(s)", iterations)
            break

        logger.info("Autopilot iteration %d: found %d error(s), attempting fix", iterations, len(errors))

        # Step 3: Fix using vision model (screenshot + errors + code)
        error_context = "\n".join(f"  - {e}" for e in errors[:10])
        fixed_code = await _attempt_fix(current_code, error_context, screenshot_b64)

        if not fixed_code or fixed_code == current_code:
            logger.info("Autopilot: fix attempt returned same/empty code, stopping")
            break

        current_code = fixed_code

    return current_code, iterations


async def _attempt_fix(code: str, error_context: str, screenshot_b64: str | None) -> str:
    """Attempt to fix code using vision model (if screenshot available) or text model."""

    if screenshot_b64:
        # Vision-based fix (most accurate)
        try:
            result = await asyncio.wait_for(
                vision_chat(
                    images_base64=[screenshot_b64],
                    text_prompt=(
                        f"{AUTOPILOT_FIX_SYSTEM}\n\n"
                        f"CONSOLE ERRORS:\n{error_context}\n\n"
                        f"SOURCE CODE:\n```html\n{code}\n```\n\n"
                        f"Fix ALL issues. Output the complete fixed HTML."
                    ),
                    temperature=0.3,
                    max_tokens=16384,
                ),
                timeout=120,
            )
            fixed = _strip_fences(result["content"])
            if fixed and len(fixed) > 100:
                return fixed
        except Exception as e:
            logger.warning("Vision-based fix failed: %s", e)

    # Text-based fallback
    try:
        result = await asyncio.wait_for(
            chat_with_reasoning(
                messages=[
                    {"role": "system", "content": AUTOPILOT_FIX_SYSTEM},
                    {"role": "user", "content": (
                        f"CONSOLE ERRORS:\n{error_context}\n\n"
                        f"SOURCE CODE:\n```html\n{code}\n```\n\n"
                        f"Fix ALL issues. Output the complete fixed HTML."
                    )},
                ],
                temperature=0.3,
                max_tokens=16384,
            ),
            timeout=120,
        )
        fixed = _strip_fences(result["content"])
        if fixed and len(fixed) > 100:
            return fixed
    except Exception as e:
        logger.warning("Text-based fix failed: %s, trying fast model", e)

    # Last resort: fast model
    try:
        raw = await asyncio.wait_for(
            chat(
                messages=[
                    {"role": "system", "content": AUTOPILOT_FIX_SYSTEM},
                    {"role": "user", "content": (
                        f"Fix these errors in the HTML app:\n{error_context}\n\n"
                        f"```html\n{code}\n```"
                    )},
                ],
                temperature=0.3,
                max_tokens=8192,
                thinking=False,
                model=settings.GLM_FAST_MODEL,
            ),
            timeout=120,
        )
        fixed = _strip_fences(raw)
        if fixed and len(fixed) > 100:
            return fixed
    except Exception as e:
        logger.warning("Fast model fix also failed: %s", e)

    return ""


def _strip_fences(text: str) -> str:
    """Extract code from markdown fences."""
    text = text.strip()
    for tag in ("```html", "```"):
        if tag in text:
            start = text.find(tag) + len(tag)
            if start < len(text) and text[start] == "\n":
                start += 1
            closing = text.rfind("```", start)
            if closing != -1:
                return text[start:closing].strip()
            return text[start:].strip()
    return text
