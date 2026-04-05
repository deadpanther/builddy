"""Build CRUD endpoints."""

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
from agent.pipeline import run_pipeline, run_modify_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/builds", tags=["builds"])


class BuildCreate(BaseModel):
    tweet_id: Optional[str] = None
    tweet_text: Optional[str] = None
    twitter_username: Optional[str] = None
    prompt: Optional[str] = None


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
    steps: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    deployed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.post("", response_model=BuildResponse)
async def create_build(data: BuildCreate, session: Session = Depends(get_session)):
    """Trigger a new build."""
    build = Build(
        tweet_id=data.tweet_id,
        tweet_text=data.tweet_text,
        twitter_username=data.twitter_username,
        prompt=data.prompt or data.tweet_text,
        status="pending",
    )
    session.add(build)
    session.commit()
    session.refresh(build)

    # Run the pipeline in the background
    asyncio.create_task(_run_build_pipeline(build.id))

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

    # Create a new build linked to the original
    new_build = Build(
        tweet_text=data.modification,
        app_name=f"{original.app_name or 'App'} (modified)",
        app_description=data.modification,
        prompt=data.modification,
        parent_build_id=build_id,
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
