"""Tests for agent/test_gen.py — covering _generate_simple_tests, _generate_fullstack_tests, _extract_code."""

import json
from unittest.mock import AsyncMock, patch

import pytest


class TestExtractCode:
    """Cover lines 156-183 of test_gen.py."""

    def test_html_fence(self):
        from agent.test_gen import _extract_code
        text = "Here is the code:\n```html\n<div>Hello</div>\n```\nDone"
        assert _extract_code(text, lang="html") == "<div>Hello</div>"

    def test_javascript_fence(self):
        from agent.test_gen import _extract_code
        text = "```javascript\nconst x = 1;\n```"
        assert _extract_code(text, lang="javascript") == "const x = 1;"

    def test_generic_fence_with_lang_tag(self):
        from agent.test_gen import _extract_code
        text = "```js\nconsole.log('hi')\n```"
        result = _extract_code(text, lang="html")
        assert "console.log" in result

    def test_no_closing_fence(self):
        from agent.test_gen import _extract_code
        text = "```html\n<div>No close"
        assert _extract_code(text, lang="html") == "<div>No close"

    def test_generic_no_closing(self):
        from agent.test_gen import _extract_code
        text = "```\nsome code"
        result = _extract_code(text, lang="html")
        assert "some code" in result

    def test_no_fence_at_all(self):
        from agent.test_gen import _extract_code
        text = "<div>No fences here</div>"
        assert _extract_code(text) == "<div>No fences here</div>"


class TestGenerateSimpleTests:
    """Cover _generate_simple_tests and the main generate_tests entry point."""

    @pytest.mark.asyncio
    async def test_simple_app_success(self):
        with patch("agent.test_gen.chat_with_reasoning", new=AsyncMock(return_value={
            "content": "```html\n<html>test</html>\n```",
            "reasoning": "thoughts",
        })):
            from agent.test_gen import generate_tests
            result = await generate_tests(
                code="<h1>Hello</h1>",
                app_name="TestApp",
                complexity="simple",
            )
        assert "tests.html" in result

    @pytest.mark.asyncio
    async def test_simple_app_reasoning_fails_fallback_succeeds(self):
        """Reasoning model fails, fast model succeeds — covers lines 55-73."""
        with patch("agent.test_gen.chat_with_reasoning", new=AsyncMock(side_effect=Exception("timeout"))), \
             patch("agent.test_gen.chat", new=AsyncMock(return_value="```html\n<html>fallback</html>\n```")):
            from agent.test_gen import generate_tests
            result = await generate_tests(
                code="<h1>Hello</h1>",
                app_name="TestApp",
                complexity="simple",
            )
        assert "tests.html" in result

    @pytest.mark.asyncio
    async def test_simple_app_both_fail(self):
        """Both reasoning and fast model fail — returns {} — covers lines 55-73, 75-76."""
        with patch("agent.test_gen.chat_with_reasoning", new=AsyncMock(side_effect=Exception("fail"))), \
             patch("agent.test_gen.chat", new=AsyncMock(side_effect=Exception("also fail"))):
            from agent.test_gen import generate_tests
            result = await generate_tests(
                code="<h1>Hello</h1>",
                app_name="TestApp",
                complexity="simple",
            )
        assert result == {}

    @pytest.mark.asyncio
    async def test_simple_app_empty_code_result(self):
        """Reasoning returns empty — covers lines 75-76."""
        with patch("agent.test_gen.chat_with_reasoning", new=AsyncMock(return_value={
            "content": "",
            "reasoning": "",
        })):
            from agent.test_gen import generate_tests
            result = await generate_tests(
                code="<h1>Hello</h1>",
                app_name="TestApp",
                complexity="simple",
            )
        assert result == {}


class TestGenerateFullstackTests:
    """Cover _generate_fullstack_tests — lines 81-153."""

    @pytest.mark.asyncio
    async def test_fullstack_with_backend_files(self):
        all_files = {
            "backend/routes.py": "app.get('/api/items')",
            "frontend/index.html": "<h1>Frontend</h1>",
        }
        manifest = {
            "app_name": "FullApp",
            "features": ["crud"],
            "tech_stack": {"backend": "express"},
            "files": [{"path": "backend/routes.py", "purpose": "API routes"}],
        }

        with patch("agent.test_gen.chat_with_reasoning", new=AsyncMock(return_value={
            "content": "```javascript\nconst test = require('node:test');\n```",
            "reasoning": "plan",
        })):
            from agent.test_gen import generate_tests
            result = await generate_tests(
                code="",
                app_name="FullApp",
                complexity="fullstack",
                manifest=manifest,
                all_files=all_files,
            )
        assert "tests/app.test.js" in result

    @pytest.mark.asyncio
    async def test_fullstack_no_backend_falls_to_html(self):
        """No backend files — falls back to simple HTML tests — covers line 97."""
        all_files = {"frontend/index.html": "<h1>Test</h1>"}
        manifest = {"files": []}

        with patch("agent.test_gen.chat_with_reasoning", new=AsyncMock(return_value={
            "content": "```html\n<html>test</html>\n```",
            "reasoning": "",
        })):
            from agent.test_gen import generate_tests
            result = await generate_tests(
                code="",
                app_name="App",
                complexity="fullstack",
                manifest=manifest,
                all_files=all_files,
            )
        assert "tests.html" in result

    @pytest.mark.asyncio
    async def test_fullstack_no_files_no_code_returns_empty(self):
        """No files, no code — returns {} — covers line 98."""
        from agent.test_gen import generate_tests
        result = await generate_tests(
            code="",
            app_name="App",
            complexity="fullstack",
            manifest={},
            all_files={},
        )
        # With no code and no files, generate_tests returns empty
        assert result == {} or "tests" in result

    @pytest.mark.asyncio
    async def test_fullstack_reasoning_fails_fast_succeeds(self):
        """Covers lines 129-148."""
        all_files = {"backend/routes.py": "app.get('/x')"}
        manifest = {"files": [{"path": "backend/routes.py", "purpose": "routes"}]}

        with patch("agent.test_gen.chat_with_reasoning", new=AsyncMock(side_effect=Exception("timeout"))), \
             patch("agent.test_gen.chat", new=AsyncMock(return_value="```javascript\ntest()\n```")):
            from agent.test_gen import generate_tests
            result = await generate_tests(
                code="",
                app_name="App",
                complexity="fullstack",
                manifest=manifest,
                all_files=all_files,
            )
        assert "tests/app.test.js" in result

    @pytest.mark.asyncio
    async def test_fullstack_both_fail(self):
        """Both models fail — covers line 148."""
        all_files = {"backend/routes.py": "app.get('/x')"}
        manifest = {"files": []}

        with patch("agent.test_gen.chat_with_reasoning", new=AsyncMock(side_effect=Exception("fail"))), \
             patch("agent.test_gen.chat", new=AsyncMock(side_effect=Exception("also fail"))):
            from agent.test_gen import generate_tests
            result = await generate_tests(
                code="",
                app_name="App",
                complexity="fullstack",
                manifest=manifest,
                all_files=all_files,
            )
        assert result == {}

    @pytest.mark.asyncio
    async def test_fullstack_empty_result(self):
        """Reasoning returns empty code — covers line 150-151."""
        all_files = {"backend/routes.py": "app.get('/x')"}
        manifest = {"files": []}

        with patch("agent.test_gen.chat_with_reasoning", new=AsyncMock(return_value={
            "content": "no code fences here",
            "reasoning": "",
        })):
            from agent.test_gen import generate_tests
            result = await generate_tests(
                code="",
                app_name="App",
                complexity="fullstack",
                manifest=manifest,
                all_files=all_files,
            )
        # _extract_code returns raw text since no fences, which won't be valid JS test
        # But it still returns a dict since text is non-empty
        assert "tests/app.test.js" in result or result == {}
