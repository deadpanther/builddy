"""Database setup — SQLite + SQLModel."""

import logging
from sqlmodel import SQLModel, create_engine, Session, text
from config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _migrate_new_columns()


def _migrate_new_columns():
    """Add columns that may be missing from older DB versions."""
    new_columns = [
        ("builds", "build_type", "TEXT DEFAULT 'text'"),
        ("builds", "thumbnail_url", "TEXT"),
        ("builds", "reasoning_log", "TEXT"),
        ("builds", "parent_build_id", "TEXT"),
        ("builds", "complexity", "TEXT DEFAULT 'simple'"),
        ("builds", "file_manifest", "TEXT"),
        ("builds", "generated_files", "TEXT"),
        ("builds", "zip_url", "TEXT"),
        ("builds", "tech_stack", "TEXT"),
        ("builds", "remix_count", "INTEGER DEFAULT 0"),
        ("builds", "deploy_provider", "TEXT"),
        ("builds", "deploy_external_url", "TEXT"),
        ("builds", "deploy_status", "TEXT"),
    ]
    with Session(engine) as session:
        for table, column, col_type in new_columns:
            try:
                session.exec(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                session.commit()
                logger.info("Added column %s.%s", table, column)
            except Exception:
                session.rollback()  # Column already exists


def get_session():
    with Session(engine) as session:
        yield session


def get_new_session() -> Session:
    """Create a standalone session (for background tasks, not FastAPI deps)."""
    return Session(engine)
