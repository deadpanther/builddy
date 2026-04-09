# Testing Guide

## Overview

- **449 tests** across 13+ test files
- **80% code coverage** (enforced in CI via `--cov-fail-under=80`)
- Runtime: ~80 seconds (full suite)
- Framework: pytest + pytest-asyncio + httpx (AsyncClient)

## Quick Start

```bash
cd backend

# Run all tests
uv run pytest tests/ -q

# Run with coverage report
uv run pytest tests/ --cov=. --cov-report=term-missing

# Run a single test file
uv run pytest tests/test_builds_endpoints.py -v
```

## Test Files

| File | Tests | What it covers |
|------|-------|---------------|
| `test_builds_endpoints.py` | ~30 | Build CRUD, modify, remix, deploy, download, retry, delete, chain, files |
| `test_builds_extra.py` | ~10 | List builds, cloud deploy status, chain traversal, get/create build |
| `test_prompts_router.py` | ~28 | Prompt versions CRUD, experiments, assignments, record-result |
| `test_llm_coverage.py` | ~15 | Chat, streaming, vision, image gen, rate-limit retry, model fallback |
| `test_cloud_deploy_coverage.py` | ~10 | deploy_to_cloud, get_deploy_status, manual instructions |
| `test_test_gen.py` | ~20 | _extract_code, generate_tests, fullstack test generation, fallbacks |
| `test_autopilot.py` | ~15 | autopilot_fix_loop, _attempt_fix (vision/text/fast), _strip_fences |
| `test_rate_limiting.py` | ~2 | Rate limit enforcement on `POST /api/builds` |
| `test_multifile_classify.py` | ~1 | classify_complexity JSON fallback |
| `test_screenshot_pipeline_autopilot.py` | ~1 | Screenshot pipeline calls autopilot when enabled |

## Key Patterns

### Async HTTP Client

All endpoint tests use an async httpx client:

```python
@pytest.fixture
async def client():
    from httpx import ASGITransport, AsyncClient
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
```

### Database Session Management

Tests use a test database with proper isolation:

```python
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///test.db")
    # ... create tables
    yield session
    # ... cleanup
```

**Important:** After endpoint calls that commit via their own session, call `db_session.expire_all()` to clear the cache so subsequent reads see the committed data.

### Mocking LLM Calls

All LLM calls must be mocked to avoid hitting the real API:

```python
from unittest.mock import AsyncMock, patch

with patch("agent.llm.chat_with_reasoning", new=AsyncMock(return_value={
    "content": "```html\n<div>Generated</div>\n```",
    "reasoning": "thoughts",
})):
    result = await some_function()
```

### Mocking the Pipeline

For build creation tests, mock the entire pipeline:

```python
@pytest.fixture
def mock_pipeline():
    with patch("agent.pipeline.run_pipeline", new=AsyncMock()):
        yield
```

### Rate limiting

[`rate_limiter.py`](../backend/rate_limiter.py) exposes a single shared SlowAPI `Limiter`. [`tests/conftest.py`](../backend/tests/conftest.py) resets it before each test so the suite does not exhaust the per-IP bucket.

### Lazy Imports

Many services use lazy imports inside functions. Patch at the module where the name is resolved:

```python
# Patch where the callee looks up the symbol, e.g. agent.pipeline for pipeline code:
patch("agent.pipeline.vision_chat", ...)
```

## Adding New Tests

1. Create `tests/test_your_feature.py`
2. Import fixtures from existing conftest or create new ones
3. Use `@pytest.mark.asyncio` for async tests
4. Mock all external calls (LLM, file system, network)
5. Run: `uv run pytest tests/test_your_feature.py -v`

## Coverage Requirements

- Target: 80%+ overall coverage (CI enforces `--cov-fail-under=80`)
- Check: `uv run pytest tests/ --cov=. --cov-report=term-missing`
- Focus on uncovered lines shown in the `term-missing` report
