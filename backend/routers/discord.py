"""Discord-style HTTP ingest: create builds from JSON payloads (shared secret)."""

import asyncio
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from agent.pipeline import run_pipeline
from config import settings
from database import get_session
from models import Build

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/discord", tags=["Discord"])


class DiscordIngestBody(BaseModel):
    """Minimal payload: plain text prompt to turn into a build."""

    content: str
    username: str | None = None


@router.post("/ingest")
async def discord_ingest_build(
    data: DiscordIngestBody,
    x_builddy_secret: str | None = Header(default=None, alias="X-Builddy-Secret"),
    session: Session = Depends(get_session),
):
    if not settings.DISCORD_INGEST_SECRET or x_builddy_secret != settings.DISCORD_INGEST_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing secret")

    prompt = (data.content or "").strip()
    if len(prompt) < 3:
        raise HTTPException(status_code=400, detail="content too short")

    build = Build(
        tweet_text=prompt,
        prompt=prompt,
        twitter_username=data.username,
        build_type="text",
        status="pending",
    )
    session.add(build)
    session.commit()
    session.refresh(build)

    asyncio.create_task(run_pipeline(build.id))
    return {"build_id": build.id, "status": "pending"}
