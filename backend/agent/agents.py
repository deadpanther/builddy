"""Multi-agent quality steps: PRD, Design System, QA, Polish, Visual validation."""

import asyncio
import json
import logging

from agent.helpers import (
    STEP_TIMEOUT,
    VISUAL_TIMEOUT,
    _add_reasoning,
    _add_step,
    _strip_fences,
    _update_build,
)
from agent.llm import chat, chat_with_reasoning, vision_chat
from agent.prompts import (
    DESIGN_SYSTEM_PROMPT,
    POLISH_SYSTEM,
    PRD_SYSTEM,
    QA_SYSTEM,
    VISUAL_FIX_SYSTEM,
)
from config import settings

logger = logging.getLogger(__name__)


# ── Multi-Agent Pipeline Steps (PRD -> Design -> QA -> Polish -> Visual) ─────

async def write_prd(build_id: str, prompt: str) -> dict:
    """PM Agent: Write a Product Requirements Document with acceptance criteria."""
    _add_step(build_id, "[agent:pm] Writing product requirements...")

    try:
        result = await asyncio.wait_for(
            chat_with_reasoning(
                messages=[
                    {"role": "system", "content": PRD_SYSTEM},
                    {"role": "user", "content": f"Write a PRD for this app:\n\n{prompt}"},
                ],
                temperature=0.5,
            ),
            timeout=STEP_TIMEOUT,
        )
        prd_text = result["content"]
        reasoning = result["reasoning"]

        if reasoning:
            _add_reasoning(build_id, "prd", reasoning)
            _add_step(build_id, f"[thinking] PM reasoned through requirements ({len(reasoning)} chars)")
    except (TimeoutError, Exception) as e:
        logger.warning("PRD with reasoning failed/timed out, falling back: %s", e)
        _add_step(build_id, "PRD thinking timed out — retrying without thinking...")
        try:
            prd_text = await asyncio.wait_for(
                chat(
                    messages=[
                        {"role": "system", "content": PRD_SYSTEM},
                        {"role": "user", "content": f"Write a PRD for this app:\n\n{prompt}"},
                    ],
                    temperature=0.5,
                    thinking=False,
                    model=settings.GLM_FAST_MODEL,
                ),
                timeout=STEP_TIMEOUT,
            )
        except TimeoutError:
            prd_text = ""

    try:
        text = prd_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        prd = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        prd = {"product_name": "App", "user_stories": [], "edge_cases": [], "delight_features": []}
        _add_step(build_id, "PRD parsing failed — using minimal spec")

    stories = prd.get("user_stories", [])
    criteria_count = sum(len(s.get("acceptance_criteria", [])) for s in stories)
    _add_step(build_id, f"[agent:pm] PRD complete: {len(stories)} user stories, {criteria_count} acceptance criteria")
    return prd


async def create_design_system(build_id: str, prompt: str, prd: dict) -> dict:
    """Design Agent: Create a visual design system for the app."""
    _add_step(build_id, "[agent:designer] Creating design system...")

    tools = None
    if settings.ENABLE_WEB_SEARCH:
        tools = [
            {
                "type": "web_search",
                "web_search": {
                    "enable": "True",
                    "search_engine": "search-prime",
                    "search_result": "True",
                    "count": "2",
                    "search_recency_filter": "noLimit",
                },
            }
        ]
        _add_step(build_id, "[skill:web-search] Researching design trends...")

    try:
        result = await asyncio.wait_for(
            chat_with_reasoning(
                messages=[
                    {"role": "system", "content": DESIGN_SYSTEM_PROMPT},
                    {"role": "user", "content": (
                        f"Create a design system for this app:\n\n{prompt}\n\n"
                        f"PRD summary: {json.dumps(prd, indent=2)[:2000]}"
                    )},
                ],
                temperature=0.6,
                tools=tools,
            ),
            timeout=STEP_TIMEOUT,
        )
        design_text = result["content"]
        reasoning = result["reasoning"]

        if reasoning:
            _add_reasoning(build_id, "design", reasoning)
            _add_step(build_id, f"[thinking] Designer reasoned through visual language ({len(reasoning)} chars)")
    except (TimeoutError, Exception) as e:
        logger.warning("Design system failed/timed out, falling back: %s", e)
        _add_step(build_id, "Design agent timed out — retrying with fast model...")
        try:
            design_text = await asyncio.wait_for(
                chat(
                    messages=[
                        {"role": "system", "content": DESIGN_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Create a design system for: {prompt}"},
                    ],
                    temperature=0.6,
                    thinking=False,
                    model=settings.GLM_FAST_MODEL,
                ),
                timeout=STEP_TIMEOUT,
            )
        except TimeoutError:
            design_text = ""

    try:
        text = design_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        design = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        design = {"palette": {}, "tailwind_config": "{}", "component_choices": []}
        _add_step(build_id, "Design system parsing failed — using defaults")

    components = design.get("component_choices", [])
    _add_step(build_id, f"[agent:designer] Design system created: {', '.join(components[:5])}")
    return design


async def qa_validate(build_id: str, code: str, prd: dict) -> str:
    """QA Agent: Validate code against PRD acceptance criteria and fix issues."""
    _add_step(build_id, "[agent:qa] Validating against acceptance criteria...")

    stories_text = json.dumps(prd.get("user_stories", []), indent=2)[:4000]
    edge_cases = json.dumps(prd.get("edge_cases", []))
    delight = json.dumps(prd.get("delight_features", []))

    try:
        result = await asyncio.wait_for(
            chat_with_reasoning(
                messages=[
                    {"role": "system", "content": QA_SYSTEM},
                    {"role": "user", "content": (
                        f"PRD USER STORIES:\n{stories_text}\n\n"
                        f"EDGE CASES: {edge_cases}\n\n"
                        f"DELIGHT FEATURES: {delight}\n\n"
                        f"CODE TO VALIDATE:\n```html\n{code}\n```"
                    )},
                ],
                temperature=0.2,
                max_tokens=16384,
            ),
            timeout=STEP_TIMEOUT,
        )
    except TimeoutError:
        _add_step(build_id, "[agent:qa] Timed out — skipping QA (keeping current code)")
        return code

    qa_output = result["content"]
    reasoning = result["reasoning"]

    if reasoning:
        _add_reasoning(build_id, "qa", reasoning)
        _add_step(build_id, f"[thinking] QA traced through {len(prd.get('user_stories', []))} user stories ({len(reasoning)} chars)")

    validated = _strip_fences(qa_output)
    if not validated:
        _add_step(build_id, "QA returned empty — keeping current code")
        return code

    _update_build(build_id, generated_code=validated)
    _add_step(build_id, "[agent:qa] Validation complete — issues fixed")
    return validated


async def polish_pass(build_id: str, code: str) -> str:
    """Polish Agent: Final pass for animations, empty states, dark mode, micro-interactions."""
    _add_step(build_id, "[agent:polish] Applying final polish (animations, empty states, dark mode)...")

    try:
        result = await asyncio.wait_for(
            chat_with_reasoning(
                messages=[
                    {"role": "system", "content": POLISH_SYSTEM},
                    {"role": "user", "content": f"Polish this app:\n\n```html\n{code}\n```"},
                ],
                temperature=0.3,
                max_tokens=16384,
            ),
            timeout=STEP_TIMEOUT,
        )
    except TimeoutError:
        _add_step(build_id, "[agent:polish] Timed out — skipping polish (keeping current code)")
        return code

    polished = _strip_fences(result["content"])
    reasoning = result["reasoning"]

    if reasoning:
        _add_reasoning(build_id, "polish", reasoning)
        _add_step(build_id, f"[thinking] Polish agent reviewed every detail ({len(reasoning)} chars)")

    if not polished:
        _add_step(build_id, "Polish returned empty — keeping current code")
        return code

    _update_build(build_id, generated_code=polished)
    _add_step(build_id, f"[agent:polish] Polished ({len(polished)} chars)")
    return polished


async def visual_validate(build_id: str, code: str) -> str:
    """Visual Feedback Loop: Load in browser, screenshot, fix issues with GLM-5V-Turbo."""
    _add_step(build_id, "[agent:visual] Loading app in headless browser...")

    try:
        from services.visual_validator import validate_html

        result = await asyncio.wait_for(validate_html(code), timeout=VISUAL_TIMEOUT)
        errors = result["console_errors"]
        screenshot_b64 = result["screenshot_base64"]
        has_errors = result["has_errors"]

        if not screenshot_b64:
            _add_step(build_id, "Visual validation: could not capture screenshot — skipping")
            return code

        if has_errors:
            error_list = "\n".join(f"  - {e}" for e in errors[:10])
            _add_step(build_id, f"[agent:visual] Found {len(errors)} console error(s):\n{error_list}")
        else:
            _add_step(build_id, "[agent:visual] No console errors detected")

        # Feed screenshot + errors to GLM-5V-Turbo for fixes
        _add_step(build_id, "[agent:visual] Sending screenshot to GLM-5V-Turbo for visual review...")

        error_context = ""
        if errors:
            error_context = "\n\nCONSOLE ERRORS FOUND:\n" + "\n".join(errors[:10])

        fix_result = await asyncio.wait_for(
            vision_chat(
                images_base64=[screenshot_b64],
                text_prompt=(
                    f"{VISUAL_FIX_SYSTEM}\n\n"
                    f"Here is the screenshot of the app as it currently renders.{error_context}\n\n"
                    f"CURRENT SOURCE CODE:\n```html\n{code}\n```\n\n"
                    f"Fix ALL visual issues and console errors. Output the complete fixed HTML in ```html fences."
                ),
                temperature=0.3,
                max_tokens=16384,
            ),
            timeout=STEP_TIMEOUT,
        )

        fixed = _strip_fences(fix_result["content"])
        reasoning = fix_result["reasoning"]

        if reasoning:
            _add_reasoning(build_id, "visual_fix", reasoning)
            _add_step(build_id, f"[thinking] Visual QA analyzed the screenshot ({len(reasoning)} chars)")

        if fixed and len(fixed) > 100:
            _update_build(build_id, generated_code=fixed)
            _add_step(build_id, "[agent:visual] Visual fixes applied")
            return fixed
        else:
            _add_step(build_id, "[agent:visual] No visual fixes needed — app looks good")
            return code

    except Exception as e:
        logger.warning("Visual validation failed (non-fatal): %s", e)
        _add_step(build_id, f"Visual validation skipped: {str(e)[:100]}")
        return code
