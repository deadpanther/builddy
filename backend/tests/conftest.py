"""Shared test fixtures for the Builddy backend test suite."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure the backend package root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Override DATABASE_URL before any app module touches it
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db.name}"
os.environ["GLM_API_KEY"] = "test-key-not-real"
os.environ["TWITTER_BEARER_TOKEN"] = ""
os.environ["ENABLE_TWITTER_SCRAPER"] = "false"


# ---------------------------------------------------------------------------
# Patch heavyweight services BEFORE importing app modules
# ---------------------------------------------------------------------------

# Import httpx first (needed by services)
import httpx  # noqa: E402

# Import services modules so they can be patched

# Patch twitter scraper to avoid real network calls at import time
_twitter_scraper_mock = MagicMock()
_twitter_scraper_mock.start = MagicMock()
_twitter_scraper_mock.stop = MagicMock()

_twitter_search_mock = AsyncMock(return_value=[])
_twitter_configured_mock = MagicMock(return_value=False)
_twitter_reply_mock = AsyncMock(return_value=None)

_process_mgr_mock = MagicMock()
_process_mgr_mock.start_cleanup_loop = AsyncMock()
_process_mgr_mock.stop_all = AsyncMock()
_process_mgr_mock.list_running = MagicMock(return_value=[])

# Apply patches at module level so they're active when main.py is imported
_patches = [
    patch("services.twitter_scraper.scraper", _twitter_scraper_mock),
    patch("services.twitter.search_mentions", _twitter_search_mock),
    patch("services.twitter.twitter_configured", _twitter_configured_mock),
    patch("services.twitter.post_reply", _twitter_reply_mock),
    patch("services.process_manager.process_manager", _process_mgr_mock),
]

for p in _patches:
    p.start()

# NOW import app modules (after environment and patches are in place)
from database import create_db_and_tables, engine  # noqa: E402
from main import app  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    """Create all DB tables once for the test session."""
    create_db_and_tables()
    yield


def _reset_slowapi_limiters() -> None:
    """Clear rate-limit counters so tests do not share one 127.0.0.1 bucket."""
    from rate_limiter import limiter as lim

    try:
        lim.reset()
    except Exception:
        try:
            lim._storage.reset()
        except Exception:
            pass


@pytest.fixture(autouse=True)
def _reset_rate_limiters_between_tests():
    _reset_slowapi_limiters()
    yield


@pytest.fixture()
def db_engine():
    """Expose the test database engine."""
    return engine


@pytest.fixture()
def db_session():
    """Provide a SQLModel session for direct DB manipulation in tests."""
    from sqlmodel import Session
    with Session(engine) as session:
        yield session


@pytest.fixture()
async def client():
    """Async test client using httpx.AsyncClient with the ASGI app transport.

    Each test gets a fresh client. The lifespan context is NOT invoked here
    because create_db_and_tables is handled by the session-scoped fixture above.
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


@pytest.fixture()
def mock_pipeline():
    """Mock the run_pipeline function so tests don't hit the real GLM API.

    Returns the mock so tests can inspect calls.
    """
    async def _fake_pipeline(build_id: str):
        pass  # no-op

    with patch("routers.builds.run_pipeline", new=AsyncMock(side_effect=_fake_pipeline)) as m:
        yield m


@pytest.fixture()
def mock_all_pipelines():
    """Mock every pipeline function used in the builds router."""
    with (
        patch("routers.builds.run_pipeline", new=AsyncMock()) as m_run,
        patch("routers.builds.run_modify_pipeline", new=AsyncMock()) as m_mod,
        patch("routers.builds.run_screenshot_pipeline", new=AsyncMock()) as m_ss,
        patch("routers.builds.run_modify_fullstack_pipeline", new=AsyncMock()) as m_fs,
        patch("routers.builds.run_retry_pipeline", new=AsyncMock()) as m_retry,
    ):
        yield {
            "run_pipeline": m_run,
            "run_modify_pipeline": m_mod,
            "run_screenshot_pipeline": m_ss,
            "run_modify_fullstack_pipeline": m_fs,
            "run_retry_pipeline": m_retry,
        }


@pytest.fixture()
def mock_glm():
    """Mock the GLM chat function to return a canned response."""
    async def _fake_chat(*args, **kwargs):
        return '{"prompt": "test app", "app_type": "tool", "app_name": "TestApp", "delight_features": [], "aesthetic": "minimal"}'

    with patch("agent.llm.chat", new=AsyncMock(side_effect=_fake_chat)) as m:
        yield m
