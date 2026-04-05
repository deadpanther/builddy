"""Database setup with SQLAlchemy async"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, String, Text, DateTime, JSON
from datetime import datetime
from config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Autopsy(Base):
    __tablename__ = "autopsies"
    id = Column(String, primary_key=True)
    repo_url = Column(String, nullable=False)
    repo_name = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, cloning, analyzing, complete, failed
    cause_of_death = Column(Text, nullable=True)
    contributing_factors = Column(JSON, nullable=True)
    timeline = Column(JSON, nullable=True)
    fatal_commits = Column(JSON, nullable=True)
    findings = Column(JSON, nullable=True)
    lessons_learned = Column(JSON, nullable=True)
    death_certificate = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(String, primary_key=True)
    autopsy_id = Column(String, nullable=False, index=True)
    phase = Column(String, nullable=False)  # cloning, ingestion, analysis, report
    tool_name = Column(String, nullable=True)
    tool_input = Column(JSON, nullable=True)
    observation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
