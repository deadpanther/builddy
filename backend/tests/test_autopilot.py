"""Tests for agent/autopilot.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAutopilotModule:
    """Tests for autopilot module."""

    def test_module_imports(self):
        """Test that autopilot module can be imported."""
        from agent import autopilot
        assert autopilot is not None

    def test_autopilot_fix_loop_exists(self):
        """Test that autopilot_fix_loop function exists."""
        from agent.autopilot import autopilot_fix_loop
        assert callable(autopilot_fix_loop)

    def test_max_iterations_constant(self):
        """Test MAX_AUTOPILOT_ITERATIONS constant."""
        from agent.autopilot import MAX_AUTOPILOT_ITERATIONS
        assert MAX_AUTOPILOT_ITERATIONS == 3


class TestAutopilotFixLoop:
    """Tests for autopilot_fix_loop function."""

    @pytest.mark.asyncio
    async def test_fix_loop_no_errors(self):
        """Test fix loop when no errors are found."""
        from agent.autopilot import autopilot_fix_loop

        # Mock validate_html to return no errors
        mock_result = {
            "console_errors": [],
            "screenshot_base64": "abc123",
            "has_errors": False,
        }

        with patch('services.visual_validator.validate_html', new=AsyncMock(return_value=mock_result)):
            code, iterations = await autopilot_fix_loop("<html><body>Test</body></html>")

        assert iterations == 1

    @pytest.mark.asyncio
    async def test_fix_loop_with_callback(self):
        """Test fix loop calls callback."""
        from agent.autopilot import autopilot_fix_loop

        mock_result = {
            "console_errors": [],
            "screenshot_base64": "abc123",
            "has_errors": False,
        }

        callback = MagicMock()

        with patch('services.visual_validator.validate_html', new=AsyncMock(return_value=mock_result)):
            await autopilot_fix_loop("<html></html>", on_iteration=callback)

        # Callback should have been called
        assert callback.called

    @pytest.mark.asyncio
    async def test_fix_loop_handles_validation_error(self):
        """Test fix loop handles validation errors."""
        from agent.autopilot import autopilot_fix_loop

        with patch('services.visual_validator.validate_html', new=AsyncMock(side_effect=Exception("Browser error"))):
            code, iterations = await autopilot_fix_loop("<html></html>")

        # Should return original code on error
        assert code == "<html></html>"


class TestAttemptFix:
    """Tests for _attempt_fix function."""

    @pytest.mark.asyncio
    async def test_attempt_fix_with_screenshot(self):
        """Test _attempt_fix with screenshot."""
        from agent.autopilot import _attempt_fix

        mock_response = "```html\n<html><body>Fixed</body></html>\n```"

        with patch('agent.autopilot.vision_chat', new=AsyncMock(return_value=mock_response)):
            result = await _attempt_fix("<html></html>", "Test error", "screenshot_base64")

        assert "Fixed" in result or result is not None

    @pytest.mark.asyncio
    async def test_attempt_fix_without_screenshot(self):
        """Test _attempt_fix without screenshot."""
        from agent.autopilot import _attempt_fix

        mock_response = "```html\n<html><body>Fixed</body></html>\n```"

        with patch('agent.autopilot.chat', new=AsyncMock(return_value=mock_response)):
            result = await _attempt_fix("<html></html>", "Test error", None)

        assert result is not None


class TestAutopilotPrompts:
    """Tests for autopilot prompts."""

    def test_autopilot_fix_system_exists(self):
        """Test AUTOPILOT_FIX_SYSTEM prompt exists."""
        from agent.prompts import AUTOPILOT_FIX_SYSTEM
        assert isinstance(AUTOPILOT_FIX_SYSTEM, str)
        assert len(AUTOPILOT_FIX_SYSTEM) > 0

    def test_visual_fix_system_exists(self):
        """Test VISUAL_FIX_SYSTEM prompt exists."""
        from agent.prompts import VISUAL_FIX_SYSTEM
        assert isinstance(VISUAL_FIX_SYSTEM, str)
        assert len(VISUAL_FIX_SYSTEM) > 0
