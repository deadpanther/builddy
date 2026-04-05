"""Builddy Agent Pipeline — powered by GLM 5.1 with thinking mode, vision, and image generation."""

import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlmodel import Session
from agent.llm import chat, chat_with_reasoning, vision_chat, generate_image
from agent.prompts import (
    PARSE_SYSTEM, PLAN_SYSTEM, CODE_SYSTEM, REVIEW_SYSTEM,
    MODIFY_SYSTEM, SCREENSHOT_SYSTEM, IMAGE_PROMPT_TEMPLATE,
)
from services.deployer import deploy_html
from database import engine
from models import Build
from config import settings

logger = logging.getLogger(__name__)


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


def _add_step(build_id: str, step: str):
    with Session(engine) as session:
        build = session.get(Build, build_id)
        if build:
            existing = json.loads(build.steps) if build.steps else []
            existing.append(step)
            build.steps = json.dumps(existing)
            build.updated_at = datetime.now(timezone.utc)
            session.add(build)
            session.commit()


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
    """Remove markdown code fences from generated code."""
    text = text.strip()
    if text.startswith("```html"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


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
        }

    _update_build(
        build_id,
        prompt=parsed.get("prompt", tweet_text),
        app_name=parsed.get("app_name", "my-app"),
        app_description=parsed.get("prompt", ""),
    )
    _add_step(build_id, f"Parsed: {parsed.get('app_name', 'app')} ({parsed.get('app_type', 'other')})")
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
        )

    _add_step(build_id, f"Plan created ({len(plan)} chars)")
    return plan


async def generate_code(build_id: str, prompt: str, plan: str) -> str:
    """Step 3: Generate the complete HTML/CSS/JS code with thinking mode."""
    _update_build(build_id, status="coding")
    _add_step(build_id, "Generating code with GLM 5.1...")

    result = await chat_with_reasoning(
        messages=[
            {"role": "user", "content": f"Generate a complete single-file HTML app (with inline CSS and JS, no external dependencies) for: {prompt}\n\nWrap your code in ```html fences."},
        ],
        temperature=0.7,
        max_tokens=16384,
        retries=2,
    )

    code = _strip_fences(result["content"])
    reasoning = result["reasoning"]

    if reasoning:
        _add_reasoning(build_id, "coding", reasoning)
        _add_step(build_id, f"[thinking] GLM reasoned through implementation ({len(reasoning)} chars)")

    if not code:
        # Fallback: try without thinking mode
        _add_step(build_id, "Retrying code generation...")
        code_text = await chat(
            messages=[
                {"role": "user", "content": f"Generate a complete single-file HTML app (with inline CSS and JS, no external dependencies) for: {prompt}\n\nWrap your code in ```html fences."},
            ],
            temperature=0.7,
            max_tokens=16384,
            retries=2,
        )
        code = _strip_fences(code_text)

    if not code:
        raise ValueError("GLM returned empty code after retries — cannot proceed")

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
    """Generate an app thumbnail using CogView-4."""
    if not settings.ENABLE_IMAGE_GEN:
        return

    _add_step(build_id, "Generating app thumbnail with CogView-4...")

    prompt = IMAGE_PROMPT_TEMPLATE.format(description=app_description[:200])
    url = await generate_image(prompt, size="1024x1024")

    if url:
        _update_build(build_id, thumbnail_url=url)
        _add_step(build_id, f"[image] Thumbnail generated with CogView-4")
    else:
        _add_step(build_id, "Thumbnail generation skipped")


# ── Full Pipelines ───────────────────────────────────────────────────────────

async def run_pipeline(build_id: str):
    """Run the full text-to-app agent pipeline."""
    try:
        with Session(engine) as session:
            build = session.get(Build, build_id)
            if not build:
                logger.error("Build %s not found", build_id)
                return
            tweet_text = build.tweet_text or build.prompt or "Build a simple hello world app"

        # Step 1: Parse
        parsed = await parse_request(build_id, tweet_text)

        # Step 2: Plan (with web search + thinking)
        plan = await plan_app(build_id, parsed["prompt"])

        # Step 3: Generate code (with thinking)
        code = await generate_code(build_id, parsed["prompt"], plan)

        # Step 4: Review (with thinking)
        code = await review_code(build_id, code)

        # Step 5: Deploy
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

        # Step 6: Generate thumbnail (non-blocking, after deploy)
        app_desc = parsed.get("prompt", tweet_text)
        asyncio.create_task(_safe_thumbnail(build_id, app_desc))

        logger.info("Build %s completed: %s", build_id, deploy_url)

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
            # Fallback: simpler prompt without thinking
            _add_step(build_id, "Retrying modification with simplified prompt...")
            await asyncio.sleep(3)
            modified_text = await chat(
                messages=[
                    {"role": "user", "content": f"Take this HTML app and apply this change: {modification}\n\nOutput the complete modified HTML in ```html fences.\n\nOriginal:\n```html\n{original_code}\n```"},
                ],
                temperature=0.7,
                max_tokens=16384,
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
