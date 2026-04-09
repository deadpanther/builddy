"""Tests for agent/multifile.py — classify_complexity JSON fallback."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_classify_complexity_malformed_response_defaults_simple():
    """Non-JSON model output yields safe default classification."""
    from agent import multifile as mf

    with (
        patch.object(mf, "chat", new=AsyncMock(return_value="this is not valid json")),
        patch.object(mf, "_add_step", MagicMock()),
        patch.object(mf, "_update_build", MagicMock()),
    ):
        result = await mf.classify_complexity("build-test-1", "Build a todo app")

    assert result["complexity"] == "simple"
    assert "Failed to classify" in result["reasoning"]
    assert result.get("app_name") == "my-app"
