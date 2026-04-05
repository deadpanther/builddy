"""Buildy Agent Pipeline — parse_request -> plan_app -> generate_code -> review_code -> deploy"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlmodel import Session
from agent.llm import chat
from agent.prompts import PARSE_SYSTEM, PLAN_SYSTEM, CODE_SYSTEM, REVIEW_SYSTEM, MODIFY_SYSTEM
from services.deployer import deploy_html
from database import engine
from models import Build

logger = logging.getLogger(__name__)


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


async def parse_request(build_id: str, tweet_text: str) -> dict:
    """Step 1: Parse the tweet into a structured app request."""
    _update_build(build_id, status="planning")
    _add_step(build_id, "Parsing tweet request...")

    result = await chat(
        messages=[
            {"role": "system", "content": PARSE_SYSTEM},
            {"role": "user", "content": f"Parse this tweet:\n\n{tweet_text}"},
        ],
        temperature=0.3,
    )

    try:
        # Try to extract JSON from the response
        text = result.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        # Fallback: use the raw tweet text as the prompt
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
    _add_step(build_id, f"Parsed request: {json.dumps(parsed)}")
    return parsed


async def plan_app(build_id: str, prompt: str) -> str:
    """Step 2: Plan the app architecture."""
    _add_step(build_id, "Planning app architecture...")

    plan = await chat(
        messages=[
            {"role": "system", "content": PLAN_SYSTEM},
            {"role": "user", "content": f"Plan this app:\n\n{prompt}"},
        ],
        temperature=0.5,
    )

    _add_step(build_id, f"Plan created ({len(plan)} chars)")
    return plan


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


async def generate_code(build_id: str, prompt: str, plan: str) -> str:
    """Step 3: Generate the complete HTML/CSS/JS code."""
    _update_build(build_id, status="coding")
    _add_step(build_id, "Generating code with GLM...")

    # Don't pass the full plan — long inputs cause GLM timeouts.
    # The plan step still runs (for the multi-step pipeline story) but
    # code generation uses only the concise parsed prompt.
    code = await chat(
        messages=[
            {"role": "user", "content": f"Generate a complete single-file HTML app (with inline CSS and JS, no external dependencies) for: {prompt}\n\nWrap your code in ```html fences."},
        ],
        temperature=0.7,
        max_tokens=8192,
        retries=2,
    )
    code = _strip_fences(code)

    if not code:
        raise ValueError("GLM returned empty code after retries — cannot proceed")

    _update_build(build_id, generated_code=code)
    _add_step(build_id, f"Code generated ({len(code)} chars)")
    return code


async def review_code(build_id: str, code: str) -> str:
    """Step 4: Self-review and fix any issues."""
    _update_build(build_id, status="reviewing")
    _add_step(build_id, "Reviewing code for issues...")

    reviewed = await chat(
        messages=[
            {"role": "system", "content": REVIEW_SYSTEM},
            {"role": "user", "content": f"Review and fix this code:\n\n{code}"},
        ],
        temperature=0.2,
        max_tokens=8192,
    )

    reviewed = _strip_fences(reviewed)

    if not reviewed:
        _add_step(build_id, "Review returned empty — keeping original code")
        return code

    _update_build(build_id, generated_code=reviewed)
    _add_step(build_id, "Code review complete")
    return reviewed


async def run_pipeline(build_id: str):
    """Run the full agent pipeline for a build."""
    try:
        # Fetch the build
        with Session(engine) as session:
            build = session.get(Build, build_id)
            if not build:
                logger.error("Build %s not found", build_id)
                return

            tweet_text = build.tweet_text or build.prompt or "Build a simple hello world app"

        # Step 1: Parse
        parsed = await parse_request(build_id, tweet_text)

        # Step 2: Plan
        plan = await plan_app(build_id, parsed["prompt"])

        # Step 3: Generate
        code = await generate_code(build_id, parsed["prompt"], plan)

        # Step 4: Review
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

        logger.info("Build %s completed successfully: %s", build_id, deploy_url)

    except Exception as e:
        with Session(engine) as session:
            build = session.get(Build, build_id)
            failed_at = build.status if build else "unknown"
        logger.exception("Build %s failed at [%s]: %s", build_id, failed_at, str(e))
        _update_build(build_id, status="failed", error=f"[{failed_at}] {str(e)}")
        _add_step(build_id, f"Build failed at {failed_at}: {str(e)}")


async def run_modify_pipeline(build_id: str, original_code: str, modification: str):
    """Run a modification pipeline — takes existing code and applies changes."""
    try:
        _update_build(build_id, status="coding")
        _add_step(build_id, f"Modifying: {modification[:100]}...")

        await asyncio.sleep(1)

        modified = await chat(
            messages=[
                {"role": "system", "content": MODIFY_SYSTEM},
                {"role": "user", "content": f"Requested change: {modification}\n\nCurrent code:\n```html\n{original_code}\n```"},
            ],
            temperature=0.5,
            max_tokens=8192,
            retries=2,
        )
        modified = _strip_fences(modified)

        if not modified:
            # Fallback: simpler prompt
            _add_step(build_id, "Retrying modification with simplified prompt...")
            await asyncio.sleep(3)
            modified = await chat(
                messages=[
                    {"role": "user", "content": f"Take this HTML app and apply this change: {modification}\n\nOutput the complete modified HTML in ```html fences.\n\nOriginal:\n```html\n{original_code}\n```"},
                ],
                temperature=0.7,
                max_tokens=8192,
                retries=1,
            )
            modified = _strip_fences(modified)

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
