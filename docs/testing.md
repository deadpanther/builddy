# Testing Guide

## Overview

- **447 tests** across 11 test files
- **80% code coverage**
- Runtime: ~75 seconds (full suite)
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

# Skip flaky rate-limiting tests
uv run pytest tests/ --ignore=tests/test_rate_limiting.py
```

## Test Files

| File | Tests | What it covers |
|------|-------|---------------|
| `test_builds_endpoints.py` | ~30 | Build CRUD, modify, remix, deploy, download, retry, delete, chain, files |
| `test_builds_extra.py` | ~10 | List builds, cloud deploy status, chain traversal, get/create build |
| `test_prompts_router.py` | ~15 | Prompt versions CRUD, experiments, assignments, record-result |
| `test_llm_coverage.py` | ~15 | Chat, streaming, vision, image gen, rate-limit retry, model fallback |
| `test_cloud_deploy_coverage.py` | ~10 | deploy_to_cloud, get_deploy_status, manual instructions |
| `test_test_gen.py` | ~20 | _extract_code, generate_tests, fullstack test generation, fallbacks |
| `test_autopilot.py` | ~15 | autopilot_fix_loop, _attempt_fix (vision/text/fast), _strip_fences |
| `test_rate_limiting.py` | ~5 | Rate limit enforcement (flaky - cross-test contamination) |

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

### Lazy Imports

Many services use lazy imports inside functions. Patch at the source module:

```python
# Wrong:
patch("agent.pipeline.deploy_html", ...)

# Right:
patch("services.deployer.deploy_html", ...)
```

## Adding New Tests

1. Create `tests/test_your_feature.py`
2. Import fixtures from existing conftest or create new ones
3. Use `@pytest.mark.asyncio` for async tests
4. Mock all external calls (LLM, file system, network)
5. Run: `uv run pytest tests/test_your_feature.py -v`

## Coverage Requirements

- Target: 80%+ overall coverage
- Check: `uv run pytest tests/ --cov=. --cov-report=term-missing`
- Focus on uncovered lines shown in the `term-missing` report

## Known Issues

- `test_rate_limiting.py` has cross-test contamination from Slowapi state -- run in isolation or skip
