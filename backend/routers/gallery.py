"""Gallery endpoints — public gallery of deployed apps."""


from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import Build

router = APIRouter(prefix="/api/gallery", tags=["Gallery"])


@router.get("")
async def gallery_list(
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    """Public gallery of all deployed apps."""
    builds = session.exec(
        select(Build)
        .where(Build.status == "deployed")
        .order_by(Build.deployed_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [
        {
            "id": b.id,
            "app_name": b.app_name,
            "app_description": b.app_description,
            "twitter_username": b.twitter_username,
            "tweet_text": b.tweet_text,
            "deploy_url": b.deploy_url,
            "build_type": b.build_type,
            "complexity": b.complexity,
            "thumbnail_url": b.thumbnail_url,
            "tech_stack": b.tech_stack,
            "zip_url": b.zip_url,
            "remix_count": b.remix_count,
            "deployed_at": str(b.deployed_at) if b.deployed_at else None,
        }
        for b in builds
    ]


@router.get("/{build_id}")
async def gallery_detail(build_id: str, session: Session = Depends(get_session)):
    """Single deployed app for gallery / OG metadata (no source code)."""
    build = session.get(Build, build_id)
    if not build or build.status != "deployed":
        raise HTTPException(status_code=404, detail="Build not found")
    return {
        "id": build.id,
        "app_name": build.app_name,
        "app_description": build.app_description,
        "twitter_username": build.twitter_username,
        "tweet_text": build.tweet_text,
        "deploy_url": build.deploy_url,
        "deploy_external_url": build.deploy_external_url,
        "status": build.status,
        "thumbnail_url": build.thumbnail_url,
        "remix_count": build.remix_count,
        "complexity": build.complexity,
        "deployed_at": str(build.deployed_at) if build.deployed_at else None,
    }
