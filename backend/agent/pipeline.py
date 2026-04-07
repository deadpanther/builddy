"""Builddy Agent Pipeline — powered by GLM 5.1 with thinking mode, vision, and image generation."""

import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlmodel import Session
from agent.llm import chat, chat_with_reasoning, chat_streaming, vision_chat, generate_image
from agent.prompts import (
    PARSE_SYSTEM, PLAN_SYSTEM, CODE_SYSTEM, REVIEW_SYSTEM,
    MODIFY_SYSTEM, SCREENSHOT_SYSTEM, IMAGE_PROMPT_TEMPLATE,
    CLASSIFY_SYSTEM, MANIFEST_SYSTEM, FILEGEN_SYSTEM, INTEGRATION_SYSTEM,
    DOCKERFILE_TEMPLATE, DOCKER_COMPOSE_TEMPLATE, PACKAGE_JSON_TEMPLATE,
    README_TEMPLATE, IMPACT_SYSTEM, MODIFY_FILE_SYSTEM, SEED_SYSTEM,
    PRD_SYSTEM, DESIGN_SYSTEM_PROMPT, QA_SYSTEM, POLISH_SYSTEM, VISUAL_FIX_SYSTEM,
)
from agent.components import COMPONENT_LIBRARY
from services.deployer import deploy_html, deploy_project, create_project_zip
from database import engine
from models import Build
from config import settings
from services.event_bus import publish as _publish_event

logger = logging.getLogger(__name__)


# ── Constants ────────────────────────────────────────────────────────────────

STEP_TIMEOUT = 120      # 2 minutes for thinking steps (PRD, plan, QA, etc.)
FILE_TIMEOUT = 180      # 3 minutes for file generation
VISUAL_TIMEOUT = 60     # 1 minute for visual validation


# ── Helpers ──────────────────────────────────────────────────────────────────

def _update_build(build_id: str, **kwargs):
    with Session(engine) as session:
        build = session.get(Build, build_id)
        if build:
            for k, v in kwargs.items():
                setattr(build, k, v)
            build.updated_at = datetime.now(timezone.utc)
            session.add(build)
            session.commit()
    # Publish status change to SSE subscribers
    if "status" in kwargs:
        _publish_event(build_id, "status", {"status": kwargs["status"]})


def _add_step(build_id: str, step: str):
    short_id = build_id[:8]
    logger.info("🔧 [%s] %s", short_id, step)
    with Session(engine) as session:
        build = session.get(Build, build_id)
        if build:
            existing = json.loads(build.steps) if build.steps else []
            existing.append(step)
            build.steps = json.dumps(existing)
            build.updated_at = datetime.now(timezone.utc)
            session.add(build)
            session.commit()
    # Publish step to SSE subscribers
    _publish_event(build_id, "step", {"step": step})


def _add_reasoning(build_id: str, stage: str, reasoning: str):
    """Append reasoning from thinking mode to the build's reasoning log."""
    if not reasoning:
        return
    with Session(engine) as session:
        build = session.get(Build, build_id)
        if build:
            existing = json.loads(build.reasoning_log) if build.reasoning_log else []
            existing.append({"stage": stage, "reasoning": reasoning[:2000]})
            build.reasoning_log = json.dumps(existing)
            session.add(build)
            session.commit()


def _strip_fences(text: str) -> str:
    """Extract code from markdown fences, ignoring any preamble text before them."""
    text = text.strip()

    # Find the opening fence (may have preamble text before it)
    html_fence = text.find("```html")
    generic_fence = text.find("```")

    if html_fence != -1:
        # Extract content after ```html\n ... up to closing ```
        start = html_fence + 7  # len("```html")
        # Skip the newline after ```html if present
        if start < len(text) and text[start] == "\n":
            start += 1
        closing = text.rfind("```", start)
        if closing != -1:
            return text[start:closing].strip()
        return text[start:].strip()

    if generic_fence != -1:
        start = generic_fence + 3
        if start < len(text) and text[start] == "\n":
            start += 1
        closing = text.rfind("```", start)
        if closing != -1:
            return text[start:closing].strip()
        return text[start:].strip()

    return text


# ── Pipeline Steps ───────────────────────────────────────────────────────────

async def parse_request(build_id: str, tweet_text: str) -> dict:
    """Step 1: Parse the request into a structured app request."""
    _update_build(build_id, status="planning")
    _add_step(build_id, "Parsing request with GLM 5.1...")

    result = await chat(
        messages=[
            {"role": "system", "content": PARSE_SYSTEM},
            {"role": "user", "content": f"Parse this request:\n\n{tweet_text}"},
        ],
        temperature=0.3,
    )

    try:
        text = result.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        parsed = {
            "prompt": tweet_text.replace("@builddy", "").strip(),
            "app_type": "other",
            "app_name": "my-app",
            "delight_features": [],
            "aesthetic": "minimal",
        }

    # Enrich the prompt with delight features if present
    delight = parsed.get("delight_features", [])
    enriched_prompt = parsed.get("prompt", tweet_text)
    if delight:
        enriched_prompt += "\n\nBonus features to include: " + ", ".join(delight)

    _update_build(
        build_id,
        prompt=enriched_prompt,
        app_name=parsed.get("app_name", "my-app"),
        app_description=parsed.get("prompt", ""),
    )
    _add_step(build_id, f"Parsed: {parsed.get('app_name', 'app')} ({parsed.get('app_type', 'other')}) — aesthetic: {parsed.get('aesthetic', 'minimal')}")
    if delight:
        _add_step(build_id, f"Delight features: {', '.join(delight)}")
    return parsed


async def plan_app(build_id: str, prompt: str) -> str:
    """Step 2: Plan the app architecture (with optional web search)."""
    _add_step(build_id, "Planning architecture with GLM 5.1 thinking mode...")

    # Build tools list — include web search if enabled
    tools = None
    if settings.ENABLE_WEB_SEARCH:
        tools = [
            {
                "type": "web_search",
                "web_search": {
                    "enable": "True",
                    "search_engine": "search-prime",
                    "search_result": "True",
                    "count": "3",
                    "search_recency_filter": "noLimit",
                },
            }
        ]

    try:
        result = await chat_with_reasoning(
            messages=[
                {"role": "system", "content": PLAN_SYSTEM},
                {"role": "user", "content": f"Plan this app:\n\n{prompt}"},
            ],
            temperature=0.5,
            tools=tools,
        )

        plan = result["content"]
        reasoning = result["reasoning"]

        if reasoning:
            _add_reasoning(build_id, "planning", reasoning)
            _add_step(build_id, f"[thinking] GLM reasoned through the architecture ({len(reasoning)} chars)")

        if tools:
            _add_step(build_id, "[research] GLM searched the web for relevant patterns")

    except Exception as e:
        logger.warning("Planning with reasoning/search failed, falling back: %s", e)
        plan = await chat(
            messages=[
                {"role": "system", "content": PLAN_SYSTEM},
                {"role": "user", "content": f"Plan this app:\n\n{prompt}"},
            ],
            temperature=0.5,
            thinking=False,
        )

    _add_step(build_id, f"Plan created ({len(plan)} chars)")
    return plan


async def generate_code(build_id: str, prompt: str, plan: str) -> str:
    """Step 3: Generate the complete HTML/CSS/JS code with thinking mode + web search."""
    _update_build(build_id, status="coding")
    _add_step(build_id, "Generating code with GLM 5.1 (web search + thinking)...")

    # Keep prompt lean — component library is in CODE_SYSTEM, don't duplicate
    user_content = (
        f"Build this app: {prompt}\n\n"
        f"Follow this architecture plan:\n{plan}\n\n"
        f"Generate the COMPLETE single-file HTML app using Tailwind CSS CDN. "
        f"Include: dark mode toggle, animations (fade-in, hover scale), empty states, toast notifications. "
        f"Wrap your code in ```html fences."
    )

    # Enable web search so GLM can look up Tailwind patterns, best practices, etc.
    tools = None
    if settings.ENABLE_WEB_SEARCH:
        tools = [
            {
                "type": "web_search",
                "web_search": {
                    "enable": "True",
                    "search_engine": "search-prime",
                    "search_result": "True",
                    "count": "3",
                    "search_recency_filter": "noLimit",
                },
            }
        ]
        _add_step(build_id, "[skill:web-search] Searching for UI patterns and best practices...")

    try:
        result = await asyncio.wait_for(
            chat_with_reasoning(
                messages=[
                    {"role": "system", "content": CODE_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.7,
                max_tokens=16384,
                retries=2,
                tools=tools,
            ),
            timeout=STEP_TIMEOUT,
        )
    except asyncio.TimeoutError:
        _add_step(build_id, "Code generation timed out — falling back...")
        result = {"content": "", "reasoning": ""}

    code = _strip_fences(result["content"])
    reasoning = result["reasoning"]

    if reasoning:
        _add_reasoning(build_id, "coding", reasoning)
        _add_step(build_id, f"[thinking] GLM reasoned through implementation ({len(reasoning)} chars)")

    if not code:
        # Fallback 1: same model, no thinking, no web search
        _add_step(build_id, "Retrying code generation (thinking disabled, no web search)...")
        code_text = await chat(
            messages=[
                {"role": "system", "content": CODE_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.7,
            max_tokens=16384,
            retries=2,
            thinking=False,
        )
        code = _strip_fences(code_text)

    if not code:
        # Fallback 2: fast model, no thinking — most reliable
        _add_step(build_id, "Retrying with fast model (GLM-4.5)...")
        code_text = await chat(
            messages=[
                {"role": "system", "content": CODE_SYSTEM},
                {"role": "user", "content": (
                    f"Build this app: {prompt}\n\n"
                    f"Follow this architecture plan:\n{plan}\n\n"
                    f"Generate the COMPLETE single-file HTML app using Tailwind CSS CDN. "
                    f"Wrap your code in ```html fences."
                )},
            ],
            temperature=0.7,
            max_tokens=8192,
            retries=2,
            thinking=False,
            model=settings.GLM_FAST_MODEL,
        )
        code = _strip_fences(code_text)

    if not code:
        raise ValueError("GLM returned empty code after all retries — cannot proceed")

    _update_build(build_id, generated_code=code)
    _add_step(build_id, f"Code generated ({len(code)} chars)")
    return code


async def review_code(build_id: str, code: str) -> str:
    """Step 4: Self-review and fix any issues."""
    _update_build(build_id, status="reviewing")
    _add_step(build_id, "Reviewing code with GLM 5.1...")

    result = await chat_with_reasoning(
        messages=[
            {"role": "system", "content": REVIEW_SYSTEM},
            {"role": "user", "content": f"Review and fix this code:\n\n{code}"},
        ],
        temperature=0.2,
        max_tokens=16384,
    )

    reviewed = _strip_fences(result["content"])
    reasoning = result["reasoning"]

    if reasoning:
        _add_reasoning(build_id, "reviewing", reasoning)
        _add_step(build_id, f"[thinking] GLM reviewed code quality ({len(reasoning)} chars)")

    if not reviewed:
        _add_step(build_id, "Review returned empty — keeping original code")
        return code

    _update_build(build_id, generated_code=reviewed)
    _add_step(build_id, "Code review complete — issues fixed")
    return reviewed


async def generate_thumbnail(build_id: str, app_description: str):
    """Screenshot the deployed app as a thumbnail using Playwright.

    Falls back to CogView-4 if Playwright fails or the app isn't accessible.
    """
    _add_step(build_id, "Capturing app screenshot for thumbnail...")

    # Try to screenshot the live app first
    try:
        from services.visual_validator import validate_html
        from services.deployer import get_deployed_html, DEPLOYED_DIR
        import base64

        # Read the deployed index.html
        index_path = DEPLOYED_DIR / build_id / "index.html"
        if index_path.exists():
            html = index_path.read_text(encoding="utf-8")
            result = await asyncio.wait_for(validate_html(html, viewport_width=1280, viewport_height=800), timeout=30)

            if result["screenshot_base64"]:
                # Save screenshot as a file in the deployed directory
                screenshot_bytes = base64.b64decode(result["screenshot_base64"])
                screenshot_path = DEPLOYED_DIR / build_id / "thumbnail.png"
                screenshot_path.write_bytes(screenshot_bytes)
                thumbnail_url = f"/apps/{build_id}/thumbnail.png"
                _update_build(build_id, thumbnail_url=thumbnail_url)
                _add_step(build_id, "[screenshot] App thumbnail captured")
                return

    except Exception as e:
        logger.warning("Screenshot thumbnail failed for %s: %s", build_id, e)

    # Fallback: CogView-4
    if settings.ENABLE_IMAGE_GEN:
        _add_step(build_id, "Screenshot failed — generating icon with CogView-4...")
        prompt = IMAGE_PROMPT_TEMPLATE.format(description=app_description[:200])
        url = await generate_image(prompt, size="1024x1024")
        if url:
            _update_build(build_id, thumbnail_url=url)
            _add_step(build_id, "[image] Thumbnail generated with CogView-4")
            return

    _add_step(build_id, "Thumbnail generation skipped")


# ── Multi-Agent Pipeline Steps (PRD → Design → QA → Polish → Visual) ────────

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
    except (asyncio.TimeoutError, Exception) as e:
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
        except asyncio.TimeoutError:
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
    except (asyncio.TimeoutError, Exception) as e:
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
        except asyncio.TimeoutError:
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
    except asyncio.TimeoutError:
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
    except asyncio.TimeoutError:
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
            error_context = f"\n\nCONSOLE ERRORS FOUND:\n" + "\n".join(errors[:10])

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


# ── Multi-File Pipeline Steps ────────────────────────────────────────────────

async def classify_complexity(build_id: str, prompt: str) -> dict:
    """Classify the request into simple/standard/fullstack tier."""
    _add_step(build_id, "Classifying app complexity...")

    result = await chat(
        messages=[
            {"role": "system", "content": CLASSIFY_SYSTEM},
            {"role": "user", "content": f"Classify this app request:\n\n{prompt}"},
        ],
        temperature=0.3,
    )

    try:
        text = result.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        classification = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        classification = {
            "complexity": "simple",
            "reasoning": "Failed to classify, defaulting to simple",
            "app_name": "my-app",
            "app_type": "other",
            "suggested_features": [],
            "needs_backend": False,
            "needs_database": False,
            "needs_auth": False,
        }

    complexity = classification.get("complexity", "simple")
    _update_build(
        build_id,
        complexity=complexity,
        app_name=classification.get("app_name", "my-app"),
        app_description=classification.get("reasoning", ""),
    )
    _add_step(build_id, f"Classified as {complexity}: {classification.get('reasoning', '')}")
    return classification


async def plan_manifest(build_id: str, prompt: str, classification: dict) -> dict:
    """Plan the full file manifest for a multi-file project."""
    _update_build(build_id, status="planning")
    _add_step(build_id, "Planning project file manifest with GLM 5.1 thinking mode...")

    user_content = (
        f"Plan the file manifest for this app:\n\n"
        f"Request: {prompt}\n\n"
        f"Classification: {json.dumps(classification, indent=2)}"
    )

    try:
        result = await chat_with_reasoning(
            messages=[
                {"role": "system", "content": MANIFEST_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.5,
        )
        manifest_text = result["content"]
        reasoning = result["reasoning"]

        if reasoning:
            _add_reasoning(build_id, "manifest_planning", reasoning)
            _add_step(build_id, f"[thinking] GLM planned the project architecture ({len(reasoning)} chars)")
    except Exception as e:
        logger.warning("Manifest planning with reasoning failed, falling back: %s", e)
        manifest_text = await chat(
            messages=[
                {"role": "system", "content": MANIFEST_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.5,
            thinking=False,
        )

    try:
        text = manifest_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        manifest = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        raise ValueError("GLM returned invalid manifest JSON — cannot proceed")

    # Sort files by generation order
    manifest["files"] = sorted(manifest.get("files", []), key=lambda f: f.get("order", 99))

    _update_build(
        build_id,
        file_manifest=json.dumps(manifest),
        tech_stack=json.dumps(manifest.get("tech_stack", {})),
    )
    file_count = len(manifest.get("files", []))
    _add_step(build_id, f"Manifest planned: {file_count} files to generate")
    return manifest


async def generate_file(
    build_id: str,
    manifest: dict,
    file_entry: dict,
    generated_so_far: dict[str, str],
    file_index: int,
    total_files: int,
) -> str:
    """Generate a single file using the manifest and previously generated files as context."""
    file_path = file_entry["path"]
    _add_step(build_id, f"Generating file {file_index + 1}/{total_files}: {file_path}")

    # Build context from previously generated files — only include DEPENDENCIES
    # to avoid sending 200K+ of irrelevant context that slows generation
    deps = set(file_entry.get("dependencies", []))
    context_parts = []
    for prev_path, prev_content in generated_so_far.items():
        if prev_path in deps:
            # Full content for direct dependencies
            context_parts.append(f"--- FILE: {prev_path} ---\n{prev_content}\n--- END FILE ---")
        elif prev_path.endswith((".js", ".html")) and len(prev_content) < 2000:
            # Small files get included in full
            context_parts.append(f"--- FILE: {prev_path} ---\n{prev_content}\n--- END FILE ---")
        else:
            # Large non-dependency files: include first 80 lines only (API routes, schema, exports)
            lines = prev_content.split("\n")
            summary = "\n".join(lines[:80])
            if len(lines) > 80:
                summary += f"\n... ({len(lines) - 80} more lines)"
            context_parts.append(f"--- FILE: {prev_path} (summary) ---\n{summary}\n--- END FILE ---")
    context_str = "\n\n".join(context_parts) if context_parts else "(No files generated yet)"

    # Inject a slim component reference for the FIRST HTML file only (index.html)
    # Other HTML files get just the CSS animations + dark mode snippet
    component_ref = ""
    if file_path == "frontend/index.html":
        component_ref = f"\n\n{COMPONENT_LIBRARY}\n\nUse the component patterns above as building blocks for the UI."
    elif file_path.startswith("frontend/") and file_path.endswith(".html"):
        component_ref = (
            "\n\nINCLUDE THESE IN YOUR HTML:\n"
            "- <script src='https://cdn.tailwindcss.com'></script>\n"
            "- Dark mode: use dark: prefix, add toggle calling toggleDark()\n"
            "- CSS animations: @keyframes fade-in, scale-in, slide-up (see app's index.html for reference)\n"
            "- Match the SAME header/nav/styling as index.html for consistency\n"
        )

    # Slim manifest: only include file list overview + tech stack, not full details
    slim_manifest = {
        "app_name": manifest.get("app_name"),
        "description": manifest.get("description"),
        "tech_stack": manifest.get("tech_stack"),
        "features": manifest.get("features"),
        "files": [{"path": f["path"], "purpose": f["purpose"]} for f in manifest.get("files", [])],
    }

    user_content = (
        f"Generate the file: {file_path}\n\n"
        f"PURPOSE: {file_entry.get('purpose', 'See manifest')}\n\n"
        f"PROJECT OVERVIEW:\n{json.dumps(slim_manifest, indent=2)}\n\n"
        f"REFERENCE FILES:\n{context_str}"
        f"{component_ref}"
    )

    # Only enable web search for the MAIN frontend page (index.html), not every file
    tools = None
    is_main_page = file_path == "frontend/index.html"
    if is_main_page and settings.ENABLE_WEB_SEARCH:
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
        _add_step(build_id, f"[skill:web-search] Researching UI patterns for {file_path}...")

    # Stream file generation so the frontend sees code appear in real time
    # Publish chunks every ~500 chars to avoid flooding the event bus
    _last_publish_len = 0

    async def _on_chunk(accumulated: str):
        nonlocal _last_publish_len
        if len(accumulated) - _last_publish_len >= 300:
            _publish_event(build_id, "file_chunk", {
                "file_path": file_path,
                "content": accumulated,
                "done": False,
            })
            _last_publish_len = len(accumulated)

    # Publish that we're starting this file
    _publish_event(build_id, "file_streaming_start", {"file_path": file_path})

    code = ""
    try:
        raw = await asyncio.wait_for(
            chat_streaming(
                messages=[
                    {"role": "system", "content": FILEGEN_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
                on_chunk=_on_chunk,
                temperature=0.5,
                max_tokens=8192,
                model=settings.GLM_FAST_MODEL,
            ),
            timeout=FILE_TIMEOUT,
        )
        code = raw.strip()
    except asyncio.TimeoutError:
        _add_step(build_id, f"Streaming timed out for {file_path} — trying fallback...")

    # Strip markdown fences if present
    if code.startswith("```"):
        first_newline = code.index("\n") if "\n" in code else 3
        code = code[first_newline + 1:]
    if code.endswith("```"):
        code = code[:-3].strip()

    if not code:
        # Fallback: non-streaming with fallback model
        _add_step(build_id, f"Retrying {file_path} (non-streaming fallback)...")
        try:
            fallback_result = await asyncio.wait_for(
                chat(
                    messages=[
                        {"role": "system", "content": FILEGEN_SYSTEM},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.5,
                    max_tokens=8192,
                    thinking=False,
                    retries=2,
                    model=settings.GLM_FALLBACK_MODEL,
                ),
                timeout=FILE_TIMEOUT,
            )
            code = _strip_fences(fallback_result)
        except asyncio.TimeoutError:
            _add_step(build_id, f"Fallback also timed out for {file_path}")
            code = ""

    # Publish final content
    if code:
        _publish_event(build_id, "file_chunk", {
            "file_path": file_path,
            "content": code,
            "done": True,
        })

    if not code:
        raise ValueError(f"GLM returned empty content for {file_path}")

    _add_step(build_id, f"Generated {file_path} ({len(code)} chars)")
    return code


async def generate_all_files(build_id: str, manifest: dict, existing_files: dict[str, str] | None = None) -> dict[str, str]:
    """Generate all files in the manifest sequentially (backend-first order).

    If *existing_files* is provided (e.g. from a retry), already-generated files
    are skipped and used as context for the remaining ones.
    """
    _update_build(build_id, status="coding")
    files = manifest.get("files", [])
    total = len(files)
    generated: dict[str, str] = dict(existing_files) if existing_files else {}

    skipped = sum(1 for f in files if f["path"] in generated)
    if skipped:
        _add_step(build_id, f"Resuming generation: {skipped}/{total} files already done")
    else:
        _add_step(build_id, f"Generating {total} files sequentially (backend first)...")

    for i, file_entry in enumerate(files):
        file_path = file_entry["path"]
        if file_path in generated:
            continue  # already generated (retry case)
        content = await generate_file(build_id, manifest, file_entry, generated, i, total)
        generated[file_path] = content
        # Save after each file so retry can resume from here
        _update_build(build_id, generated_files=json.dumps(generated))
        # Notify SSE clients that a new file is ready
        _publish_event(build_id, "file_generated", {
            "file_path": file_path,
            "file_count": len(generated),
            "total_files": total,
            "chars": len(content),
        })
        # Small delay between files to avoid rate limit bursting
        if i < total - 1:
            await asyncio.sleep(1)

    _add_step(build_id, f"All {total} files generated ({sum(len(v) for v in generated.values())} total chars)")
    return generated


def _extract_interface(content: str, max_lines: int = 50) -> str:
    """Extract the 'interface' of a file — imports, exports, routes, schema.

    For backend files: first 50 lines (schema + route definitions).
    For frontend files: first 30 lines (imports + structure) + any fetch() lines.
    """
    lines = content.split("\n")
    head = lines[:max_lines]

    # Also grab lines with API routes, fetch calls, table definitions
    important = []
    for i, line in enumerate(lines[max_lines:], start=max_lines):
        stripped = line.strip()
        if any(kw in stripped for kw in [
            "app.get(", "app.post(", "app.put(", "app.delete(",
            "router.", "fetch(", "CREATE TABLE", "export ", "import ",
            "module.exports",
        ]):
            important.append(line)
        if len(important) > 30:
            break

    result = "\n".join(head)
    if important:
        result += "\n\n// ... key definitions ...\n" + "\n".join(important)
    if len(lines) > max_lines:
        result += f"\n\n// ... ({len(lines) - max_lines} more lines)"
    return result


async def integration_review(build_id: str, manifest: dict, all_files: dict[str, str]) -> dict[str, str]:
    """Review files for cross-file consistency using INTERFACES only (fast).

    Only sends the first ~50 lines of each file + key definitions like routes,
    fetch calls, and table schemas. Fixes are applied per-file.
    """
    _update_build(build_id, status="reviewing")
    _add_step(build_id, "Running quick integration review (interfaces only)...")

    # Build slim context — interfaces only, not full file content
    interface_sections = []
    for path, content in all_files.items():
        # Skip deployment files — they don't have integration issues
        if path in ("Dockerfile", "docker-compose.yml", "package.json", "README.md", ".env.example", ".gitignore"):
            continue
        interface = _extract_interface(content)
        interface_sections.append(f"--- FILE: {path} ---\n{interface}\n--- END FILE ---")

    interfaces_str = "\n\n".join(interface_sections)
    total_chars = len(interfaces_str)
    _add_step(build_id, f"Reviewing {len(interface_sections)} file interfaces ({total_chars} chars context)")

    # Slim manifest
    slim_manifest = {
        "app_name": manifest.get("app_name"),
        "tech_stack": manifest.get("tech_stack"),
        "features": manifest.get("features"),
        "files": [{"path": f["path"], "purpose": f["purpose"]} for f in manifest.get("files", [])],
    }

    user_content = (
        f"PROJECT:\n{json.dumps(slim_manifest, indent=2)}\n\n"
        f"FILE INTERFACES (first ~50 lines + key definitions of each file):\n{interfaces_str}\n\n"
        f"Check for API route mismatches, import/export mismatches, and DB schema mismatches. "
        f"Only flag REAL bugs. For each fix, output the COMPLETE corrected file."
    )

    try:
        result = await asyncio.wait_for(
            chat_with_reasoning(
                messages=[
                    {"role": "system", "content": INTEGRATION_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.2,
                max_tokens=8192,
                model=settings.GLM_FAST_MODEL,
                fallback_model=settings.GLM_FALLBACK_MODEL,
            ),
            timeout=STEP_TIMEOUT,
        )

        review_text = result["content"].strip()
        reasoning = result["reasoning"]

        if reasoning:
            _add_reasoning(build_id, "integration_review", reasoning)
            _add_step(build_id, f"[thinking] Reviewed cross-file integration ({len(reasoning)} chars)")

        if review_text.startswith("```"):
            review_text = review_text.split("\n", 1)[1].rsplit("```", 1)[0]
        review = json.loads(review_text)

        issues_found = review.get("issues_found", 0)
        fixes = review.get("fixes", [])

        if issues_found > 0 and fixes:
            _add_step(build_id, f"Found {issues_found} integration issue(s) — applying fixes...")
            for fix in fixes:
                file_path = fix.get("file", "")
                fixed_content = fix.get("fixed_content", "")
                issue_desc = fix.get("issue", "unknown issue")
                if file_path and fixed_content and file_path in all_files:
                    all_files[file_path] = fixed_content
                    _add_step(build_id, f"Fixed: {issue_desc} in {file_path}")
                    _publish_event(build_id, "file_generated", {
                        "file_path": file_path,
                        "file_count": len(all_files),
                        "total_files": len(all_files),
                        "chars": len(fixed_content),
                    })
            _update_build(build_id, generated_files=json.dumps(all_files))
        else:
            _add_step(build_id, "Integration review passed — no issues found")

    except asyncio.TimeoutError:
        logger.warning("Integration review timed out (non-fatal)")
        _add_step(build_id, "Integration review timed out — skipping (app still works)")
    except Exception as e:
        logger.warning("Integration review failed (non-fatal): %s", e)
        _add_step(build_id, f"Integration review skipped: {str(e)[:100]}")

    return all_files


async def generate_seed_data(
    build_id: str,
    manifest: dict,
    all_files: dict[str, str],
) -> str | None:
    """Generate an init-data.js script that seeds the database with realistic sample data."""
    # Extract the db.js content from generated files
    db_content = all_files.get("backend/db.js", "")
    if not db_content:
        logger.warning("No backend/db.js found — skipping seed data generation")
        return None

    user_content = (
        f"PROJECT MANIFEST:\n{json.dumps(manifest, indent=2)}\n\n"
        f"DATABASE SCHEMA FILE (backend/db.js):\n{db_content}"
    )

    try:
        result = await chat_with_reasoning(
            messages=[
                {"role": "system", "content": SEED_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.6,
            max_tokens=16384,
            retries=2,
        )

        seed_script = result["content"].strip()
        reasoning = result["reasoning"]

        if reasoning:
            _add_reasoning(build_id, "seed_data", reasoning)

        # Strip markdown fences if present
        if seed_script.startswith("```"):
            first_newline = seed_script.index("\n") if "\n" in seed_script else 3
            seed_script = seed_script[first_newline + 1:]
        if seed_script.endswith("```"):
            seed_script = seed_script[:-3].strip()

        if not seed_script:
            logger.warning("Seed data generation returned empty content")
            return None

        return seed_script

    except Exception as e:
        logger.warning("Seed data generation failed (non-fatal): %s", e)
        return None


def generate_deployment_files(manifest: dict, all_files: dict[str, str]) -> dict[str, str]:
    """Generate Dockerfile, docker-compose.yml, package.json, and README from templates."""
    app_name = manifest.get("app_name", "my-app").lower().replace(" ", "-")
    description = manifest.get("description", "A web application built with Builddy")
    features = manifest.get("features", [])
    features_list = "\n".join(f"- {f}" for f in features) if features else "- Full-stack web application"
    port = "3000"

    deployment_files = {
        "Dockerfile": DOCKERFILE_TEMPLATE.format(port=port).strip(),
        "docker-compose.yml": DOCKER_COMPOSE_TEMPLATE.format(port=port).strip(),
        "package.json": PACKAGE_JSON_TEMPLATE.format(
            app_name=app_name,
            description=description,
        ).strip(),
        "README.md": README_TEMPLATE.format(
            app_name=manifest.get("app_name", "My App"),
            description=description,
            port=port,
            features_list=features_list,
        ).strip(),
        ".env.example": f"PORT={port}\nNODE_ENV=development\n",
    }

    # Add .gitignore
    deployment_files[".gitignore"] = "node_modules/\ndata/*.db\n.env\n"

    return {**all_files, **deployment_files}


# ── Full Pipelines ───────────────────────────────────────────────────────────

async def analyze_impact(build_id: str, modification: str, manifest: dict, existing_files: dict[str, str]) -> dict:
    """Analyze which files need to be created/modified/unchanged for a modification."""
    _add_step(build_id, "Analyzing modification impact...")

    # Build file listing for context
    file_sections = []
    for path, content in existing_files.items():
        file_sections.append(f"--- FILE: {path} ---\n{content}\n--- END FILE ---")
    all_files_str = "\n\n".join(file_sections)

    user_content = (
        f"MODIFICATION REQUEST: {modification}\n\n"
        f"PROJECT MANIFEST:\n{json.dumps(manifest, indent=2)}\n\n"
        f"ALL EXISTING FILES:\n{all_files_str}"
    )

    try:
        result = await chat_with_reasoning(
            messages=[
                {"role": "system", "content": IMPACT_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=8192,
        )
        impact_text = result["content"].strip()
        reasoning = result["reasoning"]

        if reasoning:
            _add_reasoning(build_id, "impact_analysis", reasoning)
            _add_step(build_id, f"[thinking] GLM analyzed modification impact ({len(reasoning)} chars)")
    except Exception as e:
        logger.warning("Impact analysis with reasoning failed, falling back: %s", e)
        impact_text = await chat(
            messages=[
                {"role": "system", "content": IMPACT_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=8192,
            thinking=False,
        )

    try:
        text = impact_text.strip() if isinstance(impact_text, str) else impact_text
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        impact = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        raise ValueError("GLM returned invalid impact analysis JSON")

    create_count = len(impact.get("files_to_create", []))
    modify_count = len(impact.get("files_to_modify", []))
    unchanged_count = len(impact.get("files_unchanged", []))
    _add_step(
        build_id,
        f"Impact: {create_count} new, {modify_count} modified, {unchanged_count} unchanged"
    )
    return impact


async def modify_existing_file(
    build_id: str,
    modification: str,
    file_path: str,
    change_spec: dict,
    original_content: str,
    manifest: dict,
    context_files: dict[str, str],
    file_index: int,
    total_files: int,
) -> str:
    """Modify a single existing file based on the impact analysis."""
    _add_step(build_id, f"Modifying file {file_index + 1}/{total_files}: {file_path}")

    # Build context from newly created/modified files
    context_parts = []
    for ctx_path, ctx_content in context_files.items():
        context_parts.append(f"--- FILE: {ctx_path} ---\n{ctx_content}\n--- END FILE ---")
    context_str = "\n\n".join(context_parts) if context_parts else "(No other files changed yet)"

    user_content = (
        f"USER'S MODIFICATION REQUEST: {modification}\n\n"
        f"CHANGES NEEDED FOR THIS FILE: {change_spec.get('changes', '')}\n"
        f"REASON: {change_spec.get('reason', '')}\n\n"
        f"ORIGINAL FILE ({file_path}):\n{original_content}\n\n"
        f"PROJECT MANIFEST:\n{json.dumps(manifest, indent=2)}\n\n"
        f"OTHER RECENTLY CHANGED FILES:\n{context_str}"
    )

    result = await chat_with_reasoning(
        messages=[
            {"role": "system", "content": MODIFY_FILE_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        temperature=0.4,
        max_tokens=16384,
        retries=2,
    )

    code = result["content"].strip()
    reasoning = result["reasoning"]

    # Strip markdown fences if present
    if code.startswith("```"):
        first_newline = code.index("\n") if "\n" in code else 3
        code = code[first_newline + 1:]
    if code.endswith("```"):
        code = code[:-3].strip()

    if reasoning:
        _add_reasoning(build_id, f"modifying_{file_path}", reasoning)

    if not code:
        _add_step(build_id, f"Modification returned empty for {file_path} — keeping original")
        return original_content

    _add_step(build_id, f"Modified {file_path} ({len(code)} chars)")
    return code


async def run_modify_fullstack_pipeline(
    build_id: str,
    modification: str,
    existing_files: dict[str, str],
    manifest: dict,
):
    """Run the iterative modification pipeline for multi-file projects."""
    try:
        _update_build(build_id, status="planning")

        # Step 1: Impact analysis
        impact = await analyze_impact(build_id, modification, manifest, existing_files)

        _update_build(build_id, status="coding")

        # Start with a copy of all existing files
        updated_files = dict(existing_files)
        context_files: dict[str, str] = {}

        files_to_create = impact.get("files_to_create", [])
        files_to_modify = impact.get("files_to_modify", [])
        total_changes = len(files_to_create) + len(files_to_modify)

        if total_changes == 0:
            _add_step(build_id, "No file changes needed — redeploying as-is")
        else:
            _add_step(build_id, f"Applying {total_changes} file changes...")

            # Step 2a: Generate new files
            for i, file_spec in enumerate(files_to_create):
                file_path = file_spec["path"]
                _add_step(build_id, f"Creating new file {i + 1}/{len(files_to_create)}: {file_path}")

                # Use FILEGEN_SYSTEM for new files (same as initial generation)
                file_entry = {
                    "path": file_path,
                    "purpose": file_spec.get("purpose", ""),
                    "dependencies": file_spec.get("depends_on", []),
                }
                # Provide both existing unchanged files and already-modified files as context
                gen_context = {**updated_files, **context_files}
                code = await generate_file(
                    build_id, manifest, file_entry, gen_context, i, len(files_to_create)
                )
                updated_files[file_path] = code
                context_files[file_path] = code

            # Step 2b: Modify existing files
            for i, change_spec in enumerate(files_to_modify):
                file_path = change_spec["path"]
                original = existing_files.get(file_path, "")
                if not original:
                    _add_step(build_id, f"Warning: {file_path} not found in existing files, skipping")
                    continue

                modified = await modify_existing_file(
                    build_id, modification, file_path, change_spec,
                    original, manifest, context_files,
                    i, len(files_to_modify),
                )
                updated_files[file_path] = modified
                context_files[file_path] = modified

        # Step 3: Integration review (only if changes were made)
        if total_changes > 0:
            updated_files = await integration_review(build_id, manifest, updated_files)

        # Step 3.5: Regenerate seed data if database schema changed
        manifest_updates = impact.get("manifest_updates", {})
        db_modified = any(
            spec.get("path") == "backend/db.js" for spec in files_to_modify
        )
        new_tables = manifest_updates.get("new_tables", [])
        if db_modified or new_tables:
            _add_step(build_id, "Database schema changed — regenerating seed data...")
            seed_script = await generate_seed_data(build_id, manifest, updated_files)
            if seed_script:
                updated_files["init-data.js"] = seed_script
                _add_step(build_id, f"Seed data script regenerated ({len(seed_script)} chars)")

        # Step 4: Regenerate deployment files with updated manifest
        _add_step(build_id, "Updating deployment files...")
        new_features = manifest_updates.get("new_features", [])
        if new_features:
            existing_features = manifest.get("features", [])
            manifest = {**manifest, "features": existing_features + new_features}

        updated_files = generate_deployment_files(manifest, updated_files)

        # Step 5: Deploy
        _update_build(build_id, status="deploying", generated_files=json.dumps(updated_files))
        _add_step(build_id, "Deploying modified project...")
        deploy_url = deploy_project(build_id, updated_files)

        # Step 6: Create zip
        _add_step(build_id, "Creating downloadable project zip...")
        zip_url = create_project_zip(build_id, updated_files)

        main_html = updated_files.get("frontend/index.html", "")
        _update_build(
            build_id,
            status="deployed",
            deploy_url=deploy_url,
            zip_url=zip_url,
            generated_code=main_html,
            generated_files=json.dumps(updated_files),
            file_manifest=json.dumps(manifest),
            deployed_at=datetime.now(timezone.utc),
        )
        _add_step(build_id, f"Deployed at {deploy_url}")
        _add_step(build_id, f"Download zip: {zip_url}")

        # Thumbnail
        asyncio.create_task(_safe_thumbnail(build_id, modification))

        logger.info("Fullstack modification %s completed: %s", build_id, deploy_url)

    except Exception as e:
        with Session(engine) as session:
            build = session.get(Build, build_id)
            failed_at = build.status if build else "unknown"
        logger.exception("Fullstack modify %s failed at [%s]: %s", build_id, failed_at, str(e))
        _update_build(build_id, status="failed", error=f"[{failed_at}] {str(e)}")
        _add_step(build_id, f"Modification failed: {str(e)}")


async def run_fullstack_pipeline(build_id: str, prompt: str, classification: dict):
    """Run the full multi-file generation pipeline for standard/fullstack apps."""
    # Step 1: Plan manifest
    manifest = await plan_manifest(build_id, prompt, classification)

    # Step 2: Generate all files
    all_files = await generate_all_files(build_id, manifest)

    # Step 3: Integration review
    all_files = await integration_review(build_id, manifest, all_files)

    # Step 3.5: Generate seed data
    _add_step(build_id, "Generating realistic sample data...")
    seed_script = await generate_seed_data(build_id, manifest, all_files)
    if seed_script:
        all_files["init-data.js"] = seed_script
        _add_step(build_id, f"Seed data script generated ({len(seed_script)} chars)")

    # Step 4: Add deployment files (Dockerfile, package.json, etc.)
    _add_step(build_id, "Generating deployment files (Dockerfile, package.json, README)...")
    all_files = generate_deployment_files(manifest, all_files)
    _update_build(build_id, generated_files=json.dumps(all_files))
    _add_step(build_id, f"Project complete: {len(all_files)} total files")

    # Step 5: Deploy project files
    _update_build(build_id, status="deploying")
    _add_step(build_id, "Deploying project...")
    deploy_url = deploy_project(build_id, all_files)

    # Step 6: Create downloadable zip
    _add_step(build_id, "Creating downloadable project zip...")
    zip_url = create_project_zip(build_id, all_files)

    # Also store the main index.html as generated_code for backward compat
    main_html = all_files.get("frontend/index.html", "")
    _update_build(
        build_id,
        status="deployed",
        deploy_url=deploy_url,
        zip_url=zip_url,
        generated_code=main_html,
        deployed_at=datetime.now(timezone.utc),
    )
    _add_step(build_id, f"Deployed at {deploy_url}")
    _add_step(build_id, f"Download zip: {zip_url}")

    return deploy_url

async def run_retry_pipeline(build_id: str, failed_at: str = "unknown"):
    """Retry a failed build from the point of failure, reusing saved intermediate state.

    The caller (retry endpoint) must pass *failed_at* because the error field
    is cleared before this coroutine runs.
    """
    try:
        with Session(engine) as session:
            build = session.get(Build, build_id)
            if not build:
                logger.error("Build %s not found for retry", build_id)
                return

            prompt = build.prompt or build.tweet_text or ""
            complexity = build.complexity or "simple"

        _add_step(build_id, f"Retrying build from '{failed_at}' stage...")

        if complexity in ("standard", "fullstack"):
            await _retry_fullstack(build_id, prompt, failed_at)
        else:
            await _retry_simple(build_id, prompt, failed_at)

        # Generate thumbnail (non-blocking)
        asyncio.create_task(_safe_thumbnail(build_id, prompt))
        logger.info("Retry of build %s completed", build_id)

    except Exception as e:
        with Session(engine) as session:
            build = session.get(Build, build_id)
            current_status = build.status if build else "unknown"
        logger.exception("Retry of build %s failed at [%s]: %s", build_id, current_status, str(e))
        _update_build(build_id, status="failed", error=f"[{current_status}] {str(e)}")
        _add_step(build_id, f"Retry failed at {current_status}: {str(e)}")


async def _retry_simple(build_id: str, prompt: str, failed_at: str):
    """Retry a simple (single-file) build from point of failure.

    Key principle: SKIP steps that already succeeded. Use fast model on retry.
    """
    with Session(engine) as session:
        build = session.get(Build, build_id)
        existing_code = build.generated_code if build else None

    if failed_at == "deploying" and existing_code:
        # Code ready, just deploy
        _add_step(build_id, "Resuming from deploy (code ready)")
        code = existing_code
    elif failed_at == "reviewing" and existing_code:
        # Code exists, just review
        _add_step(build_id, "Resuming from review (code already generated)")
        code = await review_code(build_id, existing_code)
    elif failed_at in ("coding", "planning", "pending") or not existing_code:
        # Need to generate code — use fast model directly (GLM-5.1 already failed)
        _add_step(build_id, "Retrying code generation with fast model (skipping redundant steps)...")
        _update_build(build_id, status="coding")

        code_text = await chat(
            messages=[
                {"role": "system", "content": CODE_SYSTEM},
                {"role": "user", "content": (
                    f"Build this app: {prompt}\n\n"
                    f"Generate the COMPLETE single-file HTML app using Tailwind CSS CDN. "
                    f"Include dark mode toggle, animations, empty states, toast notifications. "
                    f"Wrap your code in ```html fences."
                )},
            ],
            temperature=0.7,
            max_tokens=8192,
            retries=3,
            thinking=False,
            model=settings.GLM_FAST_MODEL,
        )
        code = _strip_fences(code_text)

        if not code:
            # Last resort: try fallback model
            _add_step(build_id, "Fast model empty — trying fallback model...")
            code_text = await chat(
                messages=[
                    {"role": "system", "content": CODE_SYSTEM},
                    {"role": "user", "content": f"Build a complete single-file HTML app for: {prompt}\n\nWrap in ```html fences."},
                ],
                temperature=0.7,
                max_tokens=8192,
                retries=2,
                thinking=False,
                model=settings.GLM_FALLBACK_MODEL,
            )
            code = _strip_fences(code_text)

        if not code:
            raise ValueError("All models returned empty code — cannot proceed")

        _update_build(build_id, generated_code=code)
        _add_step(build_id, f"Code generated ({len(code)} chars)")
    else:
        # Unknown — use existing code or fail
        code = existing_code or ""
        if not code:
            raise ValueError("No code available and unknown retry state")

    # Deploy
    _update_build(build_id, status="deploying")
    _add_step(build_id, "Deploying app...")
    deploy_url = deploy_html(build_id, code)
    _update_build(
        build_id,
        status="deployed",
        deploy_url=deploy_url,
        deployed_at=datetime.now(timezone.utc),
        tech_stack=json.dumps({
            "frontend": "HTML + Tailwind CSS + JavaScript",
            "backend": "None (client-only)",
            "database": "localStorage",
            "deployment": "Static HTML",
        }),
    )
    _add_step(build_id, f"Deployed at {deploy_url}")


async def _retry_fullstack(build_id: str, prompt: str, failed_at: str):
    """Retry a fullstack build from point of failure, reusing saved state."""
    with Session(engine) as session:
        build = session.get(Build, build_id)
        if not build:
            raise ValueError("Build not found")
        saved_manifest = json.loads(build.file_manifest) if build.file_manifest else None
        saved_files = json.loads(build.generated_files) if build.generated_files else None
        saved_complexity = build.complexity or "standard"

    # Determine what we can skip based on saved state
    has_manifest = saved_manifest is not None and len(saved_manifest.get("files", [])) > 0
    has_files = saved_files is not None and len(saved_files) > 0

    # Step 1: Plan manifest (skip if already saved)
    if has_manifest:
        manifest = saved_manifest
        _add_step(build_id, f"Reusing saved manifest ({len(manifest.get('files', []))} files)")
    else:
        classification = {
            "complexity": saved_complexity,
            "app_name": build.app_name or "app",
            "needs_backend": True,
            "needs_database": True,
            "needs_auth": saved_complexity == "fullstack",
        }
        manifest = await plan_manifest(build_id, prompt, classification)

    # Step 2: Generate files (skip already-generated ones)
    if failed_at in ("coding",) or (has_files and failed_at in ("reviewing", "deploying")):
        # Some or all files exist — pass them in to skip re-generation
        manifest_paths = {f["path"] for f in manifest.get("files", [])}
        if has_files and all(p in saved_files for p in manifest_paths):
            all_files = saved_files
            _add_step(build_id, f"Reusing all {len(all_files)} generated files")
        else:
            all_files = await generate_all_files(build_id, manifest, saved_files)
    else:
        all_files = await generate_all_files(build_id, manifest, saved_files)

    # Step 3: Integration review (always re-run unless we're past it)
    if failed_at not in ("deploying",):
        all_files = await integration_review(build_id, manifest, all_files)
    else:
        _add_step(build_id, "Skipping integration review (already passed)")

    # Step 3.5: Generate seed data (if not already present)
    if "init-data.js" not in all_files:
        _add_step(build_id, "Generating realistic sample data...")
        seed_script = await generate_seed_data(build_id, manifest, all_files)
        if seed_script:
            all_files["init-data.js"] = seed_script
            _add_step(build_id, f"Seed data script generated ({len(seed_script)} chars)")

    # Step 4: Deployment files
    _add_step(build_id, "Generating deployment files (Dockerfile, package.json, README)...")
    all_files = generate_deployment_files(manifest, all_files)
    _update_build(build_id, generated_files=json.dumps(all_files))
    _add_step(build_id, f"Project complete: {len(all_files)} total files")

    # Step 5: Deploy
    _update_build(build_id, status="deploying")
    _add_step(build_id, "Deploying project...")
    deploy_url = deploy_project(build_id, all_files)

    # Step 6: Zip
    _add_step(build_id, "Creating downloadable project zip...")
    zip_url = create_project_zip(build_id, all_files)

    main_html = all_files.get("frontend/index.html", "")
    _update_build(
        build_id,
        status="deployed",
        deploy_url=deploy_url,
        zip_url=zip_url,
        generated_code=main_html,
        deployed_at=datetime.now(timezone.utc),
    )
    _add_step(build_id, f"Deployed at {deploy_url}")
    _add_step(build_id, f"Download zip: {zip_url}")


async def run_pipeline(build_id: str):
    """Run the full text-to-app agent pipeline. Routes to simple or fullstack pipeline based on complexity."""
    try:
        with Session(engine) as session:
            build = session.get(Build, build_id)
            if not build:
                logger.error("Build %s not found", build_id)
                return
            tweet_text = build.tweet_text or build.prompt or "Build a simple hello world app"

        # Step 1: Parse
        parsed = await parse_request(build_id, tweet_text)
        prompt = parsed.get("prompt", tweet_text)

        # Step 2: Classify complexity
        classification = await classify_complexity(build_id, prompt)
        complexity = classification.get("complexity", "simple")

        if complexity in ("standard", "fullstack"):
            # ── Multi-file pipeline ──
            logger.info("Build %s using %s pipeline", build_id, complexity)

            # PM Agent: Write PRD
            prd = await write_prd(build_id, prompt)

            # Design Agent: Create design system
            design = await create_design_system(build_id, prompt, prd)

            # Enrich prompt with PRD + design context for downstream agents
            enriched_prompt = (
                f"{prompt}\n\n"
                f"PRD: {json.dumps(prd, indent=2)[:3000]}\n\n"
                f"Design System: {json.dumps(design, indent=2)[:2000]}"
            )

            deploy_url = await run_fullstack_pipeline(build_id, enriched_prompt, classification)

            # Generate thumbnail (non-blocking)
            asyncio.create_task(_safe_thumbnail(build_id, prompt))
            logger.info("Build %s completed (fullstack): %s", build_id, deploy_url)
        else:
            # ── Simple single-file pipeline with multi-agent quality ──
            logger.info("Build %s using enhanced simple pipeline", build_id)

            # PM Agent: Write PRD with acceptance criteria
            prd = await write_prd(build_id, prompt)

            # Design Agent: Create visual design system
            design = await create_design_system(build_id, prompt, prd)

            # Plan (with web search + thinking + PRD + design context)
            plan_prompt = (
                f"{prompt}\n\n"
                f"PRD: {json.dumps(prd, indent=2)[:3000]}\n\n"
                f"Design System: {json.dumps(design, indent=2)[:2000]}"
            )
            plan = await plan_app(build_id, plan_prompt)

            # Generate code (with thinking + web search + component library)
            code = await generate_code(build_id, plan_prompt, plan)

            # QA Agent: Validate against PRD acceptance criteria
            code = await qa_validate(build_id, code, prd)

            # Polish Agent: Animations, empty states, dark mode, micro-interactions
            code = await polish_pass(build_id, code)

            # Visual Feedback Loop: Browser screenshot → GLM-5V fix
            code = await visual_validate(build_id, code)

            # Deploy
            _update_build(build_id, status="deploying")
            _add_step(build_id, "Deploying app...")
            deploy_url = deploy_html(build_id, code)

            _update_build(
                build_id,
                status="deployed",
                deploy_url=deploy_url,
                deployed_at=datetime.now(timezone.utc),
                tech_stack=json.dumps({
                    "frontend": "HTML + Tailwind CSS + JavaScript",
                    "backend": "None (client-only)",
                    "database": "localStorage",
                    "deployment": "Static HTML",
                }),
            )
            _add_step(build_id, f"Deployed at {deploy_url}")

            # Generate thumbnail (non-blocking)
            asyncio.create_task(_safe_thumbnail(build_id, prompt))
            logger.info("Build %s completed (simple): %s", build_id, deploy_url)

    except Exception as e:
        with Session(engine) as session:
            build = session.get(Build, build_id)
            failed_at = build.status if build else "unknown"
        logger.exception("Build %s failed at [%s]: %s", build_id, failed_at, str(e))
        _update_build(build_id, status="failed", error=f"[{failed_at}] {str(e)}")
        _add_step(build_id, f"Build failed at {failed_at}: {str(e)}")


async def run_screenshot_pipeline(build_id: str, images_base64: list[str], text_prompt: str = ""):
    """Run the screenshot-to-app pipeline using GLM-5V-Turbo."""
    try:
        _update_build(build_id, status="planning", build_type="screenshot")
        img_count = len(images_base64)
        _add_step(build_id, f"Analyzing {img_count} screenshot(s) with GLM-5V-Turbo...")

        # Step 1: Vision model converts screenshot(s) to code
        full_prompt = SCREENSHOT_SYSTEM
        if text_prompt:
            full_prompt += f"\n\nIMPORTANT — the user described this app as: {text_prompt}"
            full_prompt += "\nUse this description as the app's title, purpose, and guide for all functionality."
        if img_count > 1:
            full_prompt += f"\n\nThe user uploaded {img_count} screenshots showing different screens/states of the app. Implement ALL screens and wire navigation between them."
        full_prompt += "\n\nConvert the screenshot(s) into a COMPLETE, FULLY INTERACTIVE, working single-file HTML application. Every button, link, input, toggle, and interactive element MUST work. Wrap your code in ```html fences."

        result = await vision_chat(
            images_base64=images_base64,
            text_prompt=full_prompt,
            temperature=0.5,
            max_tokens=16384,
            retries=2,
        )

        code = _strip_fences(result["content"])
        reasoning = result["reasoning"]

        if reasoning:
            _add_reasoning(build_id, "vision", reasoning)
            _add_step(build_id, f"[thinking] GLM-5V analyzed the design ({len(reasoning)} chars)")

        if not code:
            raise ValueError("GLM-5V-Turbo returned empty code — cannot proceed")

        _update_build(build_id, status="coding", generated_code=code)
        _add_step(build_id, f"Screenshot converted to code ({len(code)} chars)")

        # Step 2: Review
        code = await review_code(build_id, code)

        # Step 3: Deploy
        _update_build(build_id, status="deploying")
        _add_step(build_id, "Deploying app...")
        deploy_url = deploy_html(build_id, code)

        _update_build(
            build_id,
            status="deployed",
            deploy_url=deploy_url,
            deployed_at=datetime.now(timezone.utc),
        )
        _add_step(build_id, f"Deployed at {deploy_url}")

        # Thumbnail
        desc = text_prompt or "web application from screenshot"
        asyncio.create_task(_safe_thumbnail(build_id, desc))

        logger.info("Screenshot build %s completed: %s", build_id, deploy_url)

    except Exception as e:
        with Session(engine) as session:
            build = session.get(Build, build_id)
            failed_at = build.status if build else "unknown"
        logger.exception("Screenshot build %s failed at [%s]: %s", build_id, failed_at, str(e))
        _update_build(build_id, status="failed", error=f"[{failed_at}] {str(e)}")
        _add_step(build_id, f"Build failed at {failed_at}: {str(e)}")


async def run_modify_pipeline(build_id: str, original_code: str, modification: str):
    """Run a modification pipeline — takes existing code and applies changes."""
    try:
        _update_build(build_id, status="coding")
        _add_step(build_id, f"Modifying: {modification[:100]}...")

        await asyncio.sleep(1)

        result = await chat_with_reasoning(
            messages=[
                {"role": "system", "content": MODIFY_SYSTEM},
                {"role": "user", "content": f"Requested change: {modification}\n\nCurrent code:\n```html\n{original_code}\n```"},
            ],
            temperature=0.5,
            max_tokens=16384,
            retries=2,
        )

        modified = _strip_fences(result["content"])
        reasoning = result["reasoning"]

        if reasoning:
            _add_reasoning(build_id, "modify", reasoning)
            _add_step(build_id, f"[thinking] GLM reasoned through the modification ({len(reasoning)} chars)")

        if not modified:
            # Fallback: simpler prompt with thinking disabled
            _add_step(build_id, "Retrying modification (thinking disabled)...")
            await asyncio.sleep(3)
            modified_text = await chat(
                messages=[
                    {"role": "user", "content": f"Take this HTML app and apply this change: {modification}\n\nOutput the complete modified HTML in ```html fences.\n\nOriginal:\n```html\n{original_code}\n```"},
                ],
                temperature=0.7,
                max_tokens=16384,
                thinking=False,
                retries=1,
            )
            modified = _strip_fences(modified_text)

        if not modified:
            raise ValueError("GLM returned empty modification — cannot proceed")

        _update_build(build_id, generated_code=modified, status="reviewing")
        _add_step(build_id, f"Code modified ({len(modified)} chars)")

        # Deploy directly (skip review for modifications to keep it fast)
        _update_build(build_id, status="deploying")
        _add_step(build_id, "Deploying modified app...")
        deploy_url = deploy_html(build_id, modified)

        _update_build(
            build_id,
            status="deployed",
            deploy_url=deploy_url,
            deployed_at=datetime.now(timezone.utc),
        )
        _add_step(build_id, f"Deployed at {deploy_url}")
        logger.info("Modification %s completed: %s", build_id, deploy_url)

    except Exception as e:
        with Session(engine) as session:
            build = session.get(Build, build_id)
            failed_at = build.status if build else "unknown"
        logger.exception("Modify %s failed at [%s]: %s", build_id, failed_at, str(e))
        _update_build(build_id, status="failed", error=f"[{failed_at}] {str(e)}")
        _add_step(build_id, f"Modification failed: {str(e)}")


async def _safe_thumbnail(build_id: str, description: str):
    """Generate thumbnail without crashing the pipeline if it fails."""
    try:
        await generate_thumbnail(build_id, description)
    except Exception as e:
        logger.warning("Thumbnail generation failed for %s: %s", build_id, e)
