"""Build CRUD endpoints — text builds, screenshot builds, and modifications."""

import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from models import Build
from agent.pipeline import run_pipeline, run_modify_pipeline, run_screenshot_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/builds", tags=["builds"])


class BuildCreate(BaseModel):
    tweet_id: Optional[str] = None
    tweet_text: Optional[str] = None
    twitter_username: Optional[str] = None
    prompt: Optional[str] = None


class ScreenshotBuildCreate(BaseModel):
    image_base64: str | list[str]  # single base64 or list of base64 images
    prompt: Optional[str] = ""  # text instructions (what the app should do)


class ModifyRequest(BaseModel):
    modification: str


class BuildResponse(BaseModel):
    id: str
    tweet_id: Optional[str] = None
    tweet_text: Optional[str] = None
    twitter_username: Optional[str] = None
    app_name: Optional[str] = None
    app_description: Optional[str] = None
    prompt: Optional[str] = None
    status: str
    generated_code: Optional[str] = None
    deploy_url: Optional[str] = None
    parent_build_id: Optional[str] = None
    build_type: str = "text"
    thumbnail_url: Optional[str] = None
    reasoning_log: Optional[str] = None
    steps: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    deployed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.post("", response_model=BuildResponse)
async def create_build(data: BuildCreate, session: Session = Depends(get_session)):
    """Trigger a new text-to-app build."""
    build = Build(
        tweet_id=data.tweet_id,
        tweet_text=data.tweet_text,
        twitter_username=data.twitter_username,
        prompt=data.prompt or data.tweet_text,
        build_type="text",
        status="pending",
    )
    session.add(build)
    session.commit()
    session.refresh(build)

    asyncio.create_task(_run_build_pipeline(build.id))
    return build


@router.post("/from-image", response_model=BuildResponse)
async def create_build_from_image(data: ScreenshotBuildCreate, session: Session = Depends(get_session)):
    """Trigger a screenshot-to-app build using GLM-5V-Turbo."""
    # Normalize to list of base64 strings
    raw_images = data.image_base64 if isinstance(data.image_base64, list) else [data.image_base64]
    images_b64 = []
    for img in raw_images:
        if "," in img and img.startswith("data:"):
            img = img.split(",", 1)[1]
        images_b64.append(img)

    prompt_text = data.prompt or ""
    # Derive app name from prompt
    app_name = prompt_text.split(".")[0].strip()[:60] if prompt_text else "App from Screenshot"
    if not app_name:
        app_name = "App from Screenshot"

    build = Build(
        tweet_text=prompt_text or "Screenshot-to-App build",
        prompt=prompt_text or "Build a fully functional app from the provided screenshot(s)",
        app_name=app_name,
        build_type="screenshot",
        status="pending",
    )
    session.add(build)
    session.commit()
    session.refresh(build)

    asyncio.create_task(run_screenshot_pipeline(build.id, images_b64, prompt_text))
    return build


@router.get("", response_model=list[BuildResponse])
async def list_builds(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    """List all builds with optional status filter."""
    statement = select(Build).order_by(Build.created_at.desc())
    if status:
        statement = statement.where(Build.status == status)
    statement = statement.offset(offset).limit(limit)
    builds = session.exec(statement).all()
    return builds


@router.get("/{build_id}", response_model=BuildResponse)
async def get_build(build_id: str, session: Session = Depends(get_session)):
    """Get build details."""
    build = session.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    return build


@router.get("/{build_id}/steps")
async def get_build_steps(build_id: str, session: Session = Depends(get_session)):
    """Get agent steps for a build."""
    build = session.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    steps = json.loads(build.steps) if build.steps else []
    return {"build_id": build_id, "status": build.status, "steps": steps}


@router.post("/{build_id}/deploy", response_model=BuildResponse)
async def deploy_build(build_id: str, session: Session = Depends(get_session)):
    """Manually trigger deploy for a build."""
    build = session.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    if not build.generated_code:
        raise HTTPException(status_code=400, detail="No generated code to deploy")

    from services.deployer import deploy_html
    deploy_url = deploy_html(build_id, build.generated_code)
    build.deploy_url = deploy_url
    build.status = "deployed"
    build.deployed_at = datetime.now(timezone.utc)
    build.updated_at = datetime.now(timezone.utc)
    session.add(build)
    session.commit()
    session.refresh(build)
    return build


@router.post("/{build_id}/modify", response_model=BuildResponse)
async def modify_build(build_id: str, data: ModifyRequest, session: Session = Depends(get_session)):
    """Create a modified version of an existing build."""
    original = session.get(Build, build_id)
    if not original:
        raise HTTPException(status_code=404, detail="Build not found")
    if not original.generated_code:
        raise HTTPException(status_code=400, detail="Original build has no code to modify")

    new_build = Build(
        tweet_text=data.modification,
        app_name=f"{original.app_name or 'App'} (modified)",
        app_description=data.modification,
        prompt=data.modification,
        parent_build_id=build_id,
        build_type=original.build_type,
        status="pending",
    )
    session.add(new_build)
    session.commit()
    session.refresh(new_build)

    asyncio.create_task(run_modify_pipeline(new_build.id, original.generated_code, data.modification))
    return new_build


async def _run_build_pipeline(build_id: str):
    """Run the agent pipeline in background."""
    try:
        await run_pipeline(build_id)
    except Exception as e:
        logger.exception("Pipeline failed for build %s: %s", build_id, e)
