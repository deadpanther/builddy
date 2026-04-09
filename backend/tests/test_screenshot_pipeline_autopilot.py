"""Tests for screenshot pipeline autopilot parity."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import settings


@pytest.mark.asyncio
async def test_screenshot_pipeline_invokes_autopilot_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_AUTOPILOT", True)
    monkeypatch.setattr(settings, "ENABLE_AUTO_TEST_GEN", False)

    from agent.pipeline import run_screenshot_pipeline

    fake_html = "<html><body>ok</body></html>"
    autopilot_mock = AsyncMock(return_value=(fake_html, 1))
    with (
        patch(
            "agent.pipeline.vision_chat",
            new=AsyncMock(
                return_value={
                    "content": f"```html\n{fake_html}\n```",
                    "reasoning": "",
                }
            ),
        ),
        patch("agent.pipeline.review_code", new=AsyncMock(return_value=fake_html)),
        patch("agent.pipeline.autopilot_fix_loop", new=autopilot_mock),
        patch("agent.pipeline.deploy_html", return_value="http://test/deploy"),
        patch("agent.pipeline._safe_thumbnail", new=AsyncMock()),
        patch("agent.pipeline._update_build", MagicMock()),
        patch("agent.pipeline._add_step", MagicMock()),
    ):
        await run_screenshot_pipeline("screenshot-build-1", ["aGVsbG8="], "")

    autopilot_mock.assert_awaited_once()
