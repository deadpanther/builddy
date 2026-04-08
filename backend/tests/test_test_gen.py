"""Tests for agent/test_gen.py."""

from unittest.mock import AsyncMock, patch

import pytest


class TestTestGenModule:
    """Tests for test_gen module."""

    def test_module_imports(self):
        """Test that test_gen module can be imported."""
        from agent import test_gen
        assert test_gen is not None

    def test_generate_tests_exists(self):
        """Test that generate_tests function exists."""
        from agent.test_gen import generate_tests
        assert callable(generate_tests)

    def test_extract_code_exists(self):
        """Test that _extract_code function exists."""
        from agent.test_gen import _extract_code
        assert callable(_extract_code)


class TestExtractCode:
    """Tests for _extract_code function."""

    def test_extract_html_fence(self):
        """Test extracting code from HTML fence."""
        from agent.test_gen import _extract_code

        text = "Here's the code:\n```html\n<div>Hello</div>\n```\nDone."
        result = _extract_code(text, lang="html")

        assert result == "<div>Hello</div>"

    def test_extract_javascript_fence(self):
        """Test extracting code from JavaScript fence."""
        from agent.test_gen import _extract_code

        text = "```javascript\nconsole.log('test');\n```"
        result = _extract_code(text, lang="javascript")

        assert result == "console.log('test');"

    def test_extract_generic_fence(self):
        """Test extracting code from generic fence."""
        from agent.test_gen import _extract_code

        text = "```\nsome code\n```"
        result = _extract_code(text)

        assert result == "some code"

    def test_extract_no_fence(self):
        """Test extracting code when no fence present."""
        from agent.test_gen import _extract_code

        text = "just plain text"
        result = _extract_code(text)

        assert result == "just plain text"

    def test_extract_empty_text(self):
        """Test extracting from empty text."""
        from agent.test_gen import _extract_code

        result = _extract_code("")
        assert result == ""

    def test_extract_whitespace_text(self):
        """Test extracting from whitespace text."""
        from agent.test_gen import _extract_code

        result = _extract_code("   \n  \n  ")
        assert result == ""

    def test_extract_multiple_fences(self):
        """Test extracting when multiple fences present."""
        from agent.test_gen import _extract_code

        text = "```html\n<div>First</div>\n```\nOther text\n```html\n<div>Second</div>\n```"
        result = _extract_code(text, lang="html")

        # Should get the first one
        assert "First" in result


class TestGenerateTests:
    """Tests for generate_tests function."""

    @pytest.mark.asyncio
    async def test_generate_simple_tests(self):
        """Test generating tests for simple app."""
        from agent.test_gen import generate_tests

        mock_response = {
            "content": "```html\n<html><body>Test</body></html>\n```"
        }

        with patch('agent.test_gen.chat_with_reasoning', new=AsyncMock(return_value=mock_response)):
            result = await generate_tests("<html><body>App</body></html>", app_name="TestApp")

        assert "tests.html" in result

    @pytest.mark.asyncio
    async def test_generate_tests_empty_code(self):
        """Test generating tests with empty code."""
        from agent.test_gen import generate_tests

        mock_response = {"content": ""}

        with patch('agent.test_gen.chat_with_reasoning', new=AsyncMock(return_value=mock_response)):
            result = await generate_tests("", app_name="EmptyApp")

        # Should return empty dict when no code extracted
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_generate_tests_timeout_falls_back(self):
        """Test that generate_tests falls back on timeout."""

        from agent.test_gen import generate_tests

        mock_response = "```html\n<html><body>Fallback Test</body></html>\n```"

        with patch('agent.test_gen.chat_with_reasoning', new=AsyncMock(side_effect=TimeoutError())):
            with patch('agent.test_gen.chat', new=AsyncMock(return_value=mock_response)):
                result = await generate_tests("<html><body>App</body></html>", app_name="TestApp")

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_generate_fullstack_tests_no_backend(self):
        """Test generating tests for fullstack app with no backend files."""
        from agent.test_gen import generate_tests

        mock_response = {
            "content": "```html\n<html><body>Simple Test</body></html>\n```"
        }

        # Call with complexity=fullstack but no backend files
        with patch('agent.test_gen.chat_with_reasoning', new=AsyncMock(return_value=mock_response)):
            result = await generate_tests(
                "<html><body>App</body></html>",
                app_name="FullstackApp",
                complexity="fullstack",
                manifest={},
                all_files={"frontend/index.html": "<html></html>"}
            )

        # Should fall back to simple tests
        assert "tests.html" in result


class TestGenerateSimpleTests:
    """Tests for _generate_simple_tests function."""

    @pytest.mark.asyncio
    async def test_generate_simple_returns_dict(self):
        """Test that _generate_simple_tests returns a dict."""
        from agent.test_gen import _generate_simple_tests

        mock_response = {"content": "```html\n<div>Test</div>\n```"}

        with patch('agent.test_gen.chat_with_reasoning', new=AsyncMock(return_value=mock_response)):
            result = await _generate_simple_tests("<html></html>", "TestApp")

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_generate_simple_handles_error(self):
        """Test that _generate_simple_tests handles errors."""
        from agent.test_gen import _generate_simple_tests

        with patch('agent.test_gen.chat_with_reasoning', new=AsyncMock(side_effect=Exception("API Error"))):
            with patch('agent.test_gen.chat', new=AsyncMock(side_effect=Exception("Fallback Error"))):
                result = await _generate_simple_tests("<html></html>", "TestApp")

        # Should return empty dict on error
        assert result == {}


class TestTestGenPrompt:
    """Tests for test_gen prompts."""

    def test_test_gen_system_exists(self):
        """Test TEST_GEN_SYSTEM prompt exists."""
        from agent.prompts import TEST_GEN_SYSTEM
        assert isinstance(TEST_GEN_SYSTEM, str)
        assert len(TEST_GEN_SYSTEM) > 0
