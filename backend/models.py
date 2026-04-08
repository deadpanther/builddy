"""SQLModel models for Buildy — Build and Mention tables."""

import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def utcnow():
    return datetime.now(UTC)


class Build(SQLModel, table=True):
    __tablename__ = "builds"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tweet_id: str | None = Field(default=None, index=True)
    tweet_text: str | None = Field(default=None)
    twitter_username: str | None = Field(default=None)
    app_name: str | None = Field(default=None)
    app_description: str | None = Field(default=None)
    prompt: str | None = Field(default=None)
    status: str = Field(default="pending")  # pending, planning, coding, reviewing, deploying, deployed, failed
    generated_code: str | None = Field(default=None)
    deploy_url: str | None = Field(default=None)
    parent_build_id: str | None = Field(default=None)  # links to original build for modifications
    build_type: str = Field(default="text")  # text or screenshot
    complexity: str | None = Field(default="simple")  # simple, standard, fullstack
    thumbnail_url: str | None = Field(default=None)  # CogView-4 generated thumbnail
    reasoning_log: str | None = Field(default=None)  # JSON array of reasoning from thinking mode
    file_manifest: str | None = Field(default=None)  # JSON: [{path, purpose, dependencies}]
    generated_files: str | None = Field(default=None)  # JSON: {filepath: content}
    zip_url: str | None = Field(default=None)  # /downloads/{build_id}/project.zip
    tech_stack: str | None = Field(default=None)  # JSON: {frontend, backend, db, ...}
    remix_count: int = Field(default=0)  # how many times this build has been remixed
    deploy_provider: str | None = Field(default=None)  # railway, render, or None
    deploy_external_url: str | None = Field(default=None)  # live production URL
    deploy_status: str | None = Field(default=None)  # pending, deploying, live, failed
    steps: str | None = Field(default=None)  # JSON array
    error: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    deployed_at: datetime | None = Field(default=None)


class Mention(SQLModel, table=True):
    __tablename__ = "mentions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tweet_id: str = Field(unique=True, index=True)
    tweet_text: str | None = Field(default=None)
    twitter_username: str | None = Field(default=None)
    processed: bool = Field(default=False)
    build_id: str | None = Field(default=None, foreign_key="builds.id")
    created_at: datetime = Field(default_factory=utcnow)
