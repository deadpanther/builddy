"""Tests for agent/autopilot.py — covering the fix loop and _attempt_fix."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestStripFences:
    def test_html_fence(self):
        from agent.autopilot import _strip_fences
        assert _strip_fences("```html\n<div>Hi</div>\n```") == "<div>Hi</div>"

    def test_generic_fence(self):
        from agent.autopilot import _strip_fences
        assert _strip_fences("```\ncode\n```") == "code"

    def test_no_fence(self):
        from agent.autopilot import _strip_fences
        assert _strip_fences("<div>raw</div>") == "<div>raw</div>"

    def test_no_closing(self):
        from agent.autopilot import _strip_fences
        assert "code" in _strip_fences("```html\ncode without close")


class TestAutopilotFixLoop:
    @pytest.mark.asyncio
    async def test_clean_on_first_check(self):
        """No errors on first validation — returns immediately."""
        from agent.autopilot import autopilot_fix_loop

        with patch("services.visual_validator.validate_html", new=AsyncMock(return_value={
            "console_errors": [], "has_errors": False, "screenshot_base64": None,
        })):
            code, iters = await autopilot_fix_loop("<h1>Good</h1>")
        assert iters == 1

    @pytest.mark.asyncio
    async def test_fix_on_second_iteration(self):
        """First check has errors, fix succeeds, second check is clean."""
        from agent.autopilot import autopilot_fix_loop

        call_count = 0
        async def mock_validate(code, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"console_errors": ["TypeError: x is undefined"], "has_errors": True, "screenshot_base64": None}
            return {"console_errors": [], "has_errors": False, "screenshot_base64": None}

        with patch("services.visual_validator.validate_html", side_effect=mock_validate), \
             patch("agent.autopilot._attempt_fix", new=AsyncMock(return_value="<h1>Fixed code that is long enough to pass the check</h1>")):
            code, iters = await autopilot_fix_loop("<h1>Broken</h1>")
        assert "Fixed" in code
        assert iters == 2

    @pytest.mark.asyncio
    async def test_browser_validation_fails(self):
        """Browser validation throws exception — loop breaks."""
        from agent.autopilot import autopilot_fix_loop

        with patch("services.visual_validator.validate_html", new=AsyncMock(side_effect=Exception("Browser crashed"))):
            code, iters = await autopilot_fix_loop("<h1>Test</h1>")
        assert code == "<h1>Test</h1>"

    @pytest.mark.asyncio
    async def test_fix_returns_same_code_stops(self):
        """Fix returns same code — loop stops (line 62)."""
        from agent.autopilot import autopilot_fix_loop

        with patch("services.visual_validator.validate_html", new=AsyncMock(return_value={
            "console_errors": ["Error"], "has_errors": True, "screenshot_base64": None,
        })), \
             patch("agent.autopilot._attempt_fix", new=AsyncMock(return_value="<h1>Same</h1>")):
            code, iters = await autopilot_fix_loop("<h1>Same</h1>")
        assert iters == 1

    @pytest.mark.asyncio
    async def test_with_callback(self):
        """Callback is invoked — covers line 47-48."""
        from agent.autopilot import autopilot_fix_loop

        callbacks = []
        def on_iter(it, errors, screenshot):
            callbacks.append((it, errors))

        with patch("services.visual_validator.validate_html", new=AsyncMock(return_value={
            "console_errors": [], "has_errors": False, "screenshot_base64": None,
        })):
            code, iters = await autopilot_fix_loop("<h1>Good</h1>", on_iteration=on_iter)
        assert len(callbacks) == 1


class TestAttemptFix:
    @pytest.mark.asyncio
    async def test_vision_fix_succeeds(self):
        """Covers lines 73-92 — vision-based fix with screenshot."""
        from agent.autopilot import _attempt_fix

        with patch("agent.autopilot.vision_chat", new=AsyncMock(return_value={
            "content": "```html\n" + "<div>" + "x" * 200 + "</div>\n```",
            "reasoning": "visual fix",
        })):
            result = await _attempt_fix("<h1>Broken</h1>", "TypeError: x", "base64screenshot")
        assert len(result) > 100

    @pytest.mark.asyncio
    async def test_vision_fix_too_short_falls_to_text(self):
        """Vision returns short code — falls to text model (line 91-92)."""
        from agent.autopilot import _attempt_fix

        with patch("agent.autopilot.vision_chat", new=AsyncMock(return_value={
            "content": "```html\nshort\n```", "reasoning": "",
        })), \
             patch("agent.autopilot.chat_with_reasoning", new=AsyncMock(return_value={
            "content": "```html\n" + "<div>" + "y" * 200 + "</div>\n```", "reasoning": "",
        })):
            result = await _attempt_fix("<h1>Broken</h1>", "Error", "base64img")
        assert len(result) > 100

    @pytest.mark.asyncio
    async def test_text_fix_succeeds(self):
        """Covers lines 96-115 — text-based fix without screenshot."""
        from agent.autopilot import _attempt_fix

        with patch("agent.autopilot.chat_with_reasoning", new=AsyncMock(return_value={
            "content": "```html\n" + "<div>" + "z" * 200 + "</div>\n```", "reasoning": "",
        })):
            result = await _attempt_fix("<h1>Broken</h1>", "Error", None)
        assert len(result) > 100

    @pytest.mark.asyncio
    async def test_all_fail_returns_empty(self):
        """Covers lines 116-143 — all models fail."""
        from agent.autopilot import _attempt_fix

        with patch("agent.autopilot.vision_chat", new=AsyncMock(side_effect=Exception("fail"))), \
             patch("agent.autopilot.chat_with_reasoning", new=AsyncMock(side_effect=Exception("fail"))), \
             patch("agent.autopilot.chat", new=AsyncMock(side_effect=Exception("fail"))):
            result = await _attempt_fix("<h1>Broken</h1>", "Error", "base64img")
        assert result == ""

    @pytest.mark.asyncio
    async def test_fast_model_succeeds(self):
        """Covers lines 119-139 — fast model fallback succeeds."""
        from agent.autopilot import _attempt_fix

        with patch("agent.autopilot.chat_with_reasoning", new=AsyncMock(side_effect=Exception("fail"))), \
             patch("agent.autopilot.chat", new=AsyncMock(return_value="```html\n" + "<p>" + "a" * 200 + "</p>\n```")):
            result = await _attempt_fix("<h1>Broken</h1>", "Error", None)
        assert len(result) > 100
