"""Shared constants and utility functions for the Builddy agent pipeline."""

import json
import logging
from datetime import UTC, datetime

from sqlmodel import Session

from database import engine
from models import Build
from services.event_bus import publish as _publish_event

logger = logging.getLogger(__name__)


# ── Constants ────────────────────────────────────────────────────────────────

STEP_TIMEOUT = 180      # 3 minutes for thinking steps (PRD, plan, QA, etc.)
CODE_TIMEOUT = 300      # 5 minutes for code generation (largest output)
FILE_TIMEOUT = 240      # 4 minutes for file generation
VISUAL_TIMEOUT = 60     # 1 minute for visual validation


# ── Helpers ──────────────────────────────────────────────────────────────────

def _update_build(build_id: str, **kwargs):
    with Session(engine) as session:
        build = session.get(Build, build_id)
        if build:
            for k, v in kwargs.items():
                setattr(build, k, v)
            build.updated_at = datetime.now(UTC)
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
            ev_existing = json.loads(build.step_events) if build.step_events else []
            ev_existing.append({"m": step, "t": datetime.now(UTC).isoformat()})
            build.step_events = json.dumps(ev_existing)
            build.updated_at = datetime.now(UTC)
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
