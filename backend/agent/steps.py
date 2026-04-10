"""Simple pipeline steps: parse, plan, generate code, review, and thumbnail."""

import asyncio
import base64
import json
import logging

from agent.helpers import (
    STEP_TIMEOUT,
    _add_reasoning,
    _add_step,
    _strip_fences,
    _update_build,
)
from database import engine
from agent.llm import chat, chat_streaming, chat_with_reasoning, generate_image
from agent.prompts import (
    CODE_SYSTEM,
    IMAGE_PROMPT_TEMPLATE,
    PARSE_SYSTEM,
    PLAN_SYSTEM,
    REVIEW_SYSTEM,
)
from config import settings
from models import Build

logger = logging.getLogger(__name__)


# ── Pipeline Steps ───────────────────────────────────────────────────────────

async def parse_request(build_id: str, tweet_text: str) -> dict:
    """Step 1: Parse the request into a structured app request."""
    _update_build(build_id, status="planning")
    _add_step(build_id, "Parsing request with GLM 5.1...")

    constraints_block = ""
    from sqlmodel import Session

    with Session(engine) as session:
        b = session.get(Build, build_id)
        if b and b.build_options:
            try:
                opts = json.loads(b.build_options)
                if isinstance(opts, dict) and opts:
                    constraints_block = (
                        "\n\nUser constraints and options (must respect):\n"
                        + json.dumps(opts, indent=2)[:8000]
                    )
            except json.JSONDecodeError:
                pass

    result = await chat(
        messages=[
            {"role": "system", "content": PARSE_SYSTEM},
            {"role": "user", "content": f"Parse this request:\n\n{tweet_text}{constraints_block}"},
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
    """Step 3: Generate code with LIVE STREAMING so users see code appear in real time."""
    from agent.helpers import CODE_TIMEOUT
    from services.event_bus import publish as _pub

    _update_build(build_id, status="coding")
    _add_step(build_id, "Generating code with GLM 5.1...")

    user_content = (
        f"Build this app: {prompt}\n\n"
        f"Follow this architecture plan:\n{plan}\n\n"
        f"Generate the COMPLETE single-file HTML app using Tailwind CSS CDN. "
        f"Include: dark mode toggle, animations (fade-in, hover scale), empty states, toast notifications. "
        f"Wrap your code in ```html fences."
    )

    # Publish that we're starting to stream the file
    _pub(build_id, "file_streaming_start", {"file_path": "index.html"})

    _last_publish_len = 0

    async def _on_chunk(accumulated: str):
        nonlocal _last_publish_len
        if len(accumulated) - _last_publish_len >= 300:
            _pub(build_id, "file_chunk", {
                "file_path": "index.html",
                "content": accumulated,
                "done": False,
            })
            _last_publish_len = len(accumulated)

    # Primary: streaming with code model (glm-4.7 — best for coding + live output)
    code = ""
    try:
        raw = await asyncio.wait_for(
            chat_streaming(
                messages=[
                    {"role": "system", "content": CODE_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
                on_chunk=_on_chunk,
                temperature=0.7,
                max_tokens=16384,
                model=settings.GLM_CODE_MODEL,
            ),
            timeout=CODE_TIMEOUT,
        )
        code = _strip_fences(raw.strip())
    except TimeoutError:
        _add_step(build_id, "Code generation timed out — trying fallback...")

    if not code:
        # Fallback 1: non-streaming with thinking (deeper reasoning)
        _add_step(build_id, "Retrying with thinking mode...")
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
                ),
                timeout=CODE_TIMEOUT,
            )
            code = _strip_fences(result["content"])
            reasoning = result["reasoning"]
            if reasoning:
                _add_reasoning(build_id, "coding", reasoning)
                _add_step(build_id, f"[thinking] GLM reasoned through implementation ({len(reasoning)} chars)")
        except TimeoutError:
            _add_step(build_id, "Thinking mode also timed out...")

    if not code:
        # Fallback 2: fallback model, no thinking
        _add_step(build_id, "Retrying with fallback model...")
        try:
            code_text = await chat(
                messages=[
                    {"role": "system", "content": CODE_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.7,
                max_tokens=16384,
                retries=2,
                thinking=False,
                model=settings.GLM_FALLBACK_MODEL,
            )
            code = _strip_fences(code_text)
        except Exception:
            pass

    # Publish final content
    if code:
        _pub(build_id, "file_chunk", {"file_path": "index.html", "content": code, "done": True})
        _pub(build_id, "file_generated", {
            "file_path": "index.html",
            "file_count": 1,
            "total_files": 1,
            "chars": len(code),
        })

    if not code:
        _add_step(build_id, "All models failed to generate code — check rate limits and API key")
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
        from services.deployer import DEPLOYED_DIR
        from services.visual_validator import validate_html

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
