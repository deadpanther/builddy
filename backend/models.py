"""SQLModel models for Buildy — Build and Mention tables."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


def utcnow():
    return datetime.now(timezone.utc)


class Build(SQLModel, table=True):
    __tablename__ = "builds"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tweet_id: Optional[str] = Field(default=None, index=True)
    tweet_text: Optional[str] = Field(default=None)
    twitter_username: Optional[str] = Field(default=None)
    app_name: Optional[str] = Field(default=None)
    app_description: Optional[str] = Field(default=None)
    prompt: Optional[str] = Field(default=None)
    status: str = Field(default="pending")  # pending, planning, coding, reviewing, deploying, deployed, failed
    generated_code: Optional[str] = Field(default=None)
    deploy_url: Optional[str] = Field(default=None)
    parent_build_id: Optional[str] = Field(default=None)  # links to original build for modifications
    build_type: str = Field(default="text")  # text or screenshot
    complexity: Optional[str] = Field(default="simple")  # simple, standard, fullstack
    thumbnail_url: Optional[str] = Field(default=None)  # CogView-4 generated thumbnail
    reasoning_log: Optional[str] = Field(default=None)  # JSON array of reasoning from thinking mode
    file_manifest: Optional[str] = Field(default=None)  # JSON: [{path, purpose, dependencies}]
    generated_files: Optional[str] = Field(default=None)  # JSON: {filepath: content}
    zip_url: Optional[str] = Field(default=None)  # /downloads/{build_id}/project.zip
    tech_stack: Optional[str] = Field(default=None)  # JSON: {frontend, backend, db, ...}
    remix_count: int = Field(default=0)  # how many times this build has been remixed
    deploy_provider: Optional[str] = Field(default=None)  # railway, render, or None
    deploy_external_url: Optional[str] = Field(default=None)  # live production URL
    deploy_status: Optional[str] = Field(default=None)  # pending, deploying, live, failed
    steps: Optional[str] = Field(default=None)  # JSON array
    error: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    deployed_at: Optional[datetime] = Field(default=None)


class Mention(SQLModel, table=True):
    __tablename__ = "mentions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tweet_id: str = Field(unique=True, index=True)
    tweet_text: Optional[str] = Field(default=None)
    twitter_username: Optional[str] = Field(default=None)
    processed: bool = Field(default=False)
    build_id: Optional[str] = Field(default=None, foreign_key="builds.id")
    created_at: datetime = Field(default_factory=utcnow)
