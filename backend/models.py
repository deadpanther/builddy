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
    thumbnail_url: Optional[str] = Field(default=None)  # CogView-4 generated thumbnail
    reasoning_log: Optional[str] = Field(default=None)  # JSON array of reasoning from thinking mode
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
