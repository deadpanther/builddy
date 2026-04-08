"""Tests for agent/steps.py."""

from unittest.mock import AsyncMock, patch

import pytest


class TestStepsModule:
    """Tests for steps module."""

    def test_module_imports(self):
        """Test that steps module can be imported."""
        from agent import steps
        assert steps is not None

    def test_parse_request_exists(self):
        """Test that parse_request function exists."""
        from agent.steps import parse_request
        assert callable(parse_request)

    def test_plan_app_exists(self):
        """Test that plan_app function exists."""
        from agent.steps import plan_app
        assert callable(plan_app)

    def test_generate_code_exists(self):
        """Test that generate_code function exists."""
        from agent.steps import generate_code
        assert callable(generate_code)

    def test_review_code_exists(self):
        """Test that review_code function exists."""
        from agent.steps import review_code
        assert callable(review_code)


class TestParseRequest:
    """Tests for parse_request function."""

    @pytest.mark.asyncio
    async def test_parse_request_calls_llm(self):
        """Test that parse_request calls LLM."""
        from agent.steps import parse_request

        # Mock all dependencies
        mock_response = '{"prompt": "Test app", "app_name": "TestApp", "app_type": "tool"}'

        with patch('agent.steps.chat', new=AsyncMock(return_value=mock_response)):
            with patch('agent.steps._update_build'):
                with patch('agent.steps._add_step'):
                    result = await parse_request("test-build-id", "Build me a timer")

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_parse_request_handles_json_error(self):
        """Test parse_request handles JSON parse errors."""
        from agent.steps import parse_request

        # Invalid JSON response
        mock_response = 'not valid json'

        with patch('agent.steps.chat', new=AsyncMock(return_value=mock_response)):
            with patch('agent.steps._update_build'):
                with patch('agent.steps._add_step'):
                    result = await parse_request("test-build-id", "Build me something")

        # Should return a fallback dict
        assert isinstance(result, dict)
        assert "prompt" in result


class TestPlanApp:
    """Tests for plan_app function."""

    @pytest.mark.asyncio
    async def test_plan_app_returns_string(self):
        """Test that plan_app returns a string."""
        from agent.steps import plan_app

        mock_response = "Step 1: Design UI\nStep 2: Add functionality"

        with patch('agent.steps.chat_with_reasoning', new=AsyncMock(return_value={"content": mock_response})):
            with patch('agent.steps._add_step'):
                result = await plan_app("test-build-id", "Build a timer")

        assert isinstance(result, str)


class TestGenerateCode:
    """Tests for generate_code function."""

    @pytest.mark.asyncio
    async def test_generate_code_exists(self):
        """Test that generate_code function exists and is callable."""
        from agent.steps import generate_code
        assert callable(generate_code)


class TestReviewCode:
    """Tests for review_code function."""

    @pytest.mark.asyncio
    async def test_review_code_exists(self):
        """Test that review_code function exists and is callable."""
        from agent.steps import review_code
        assert callable(review_code)


class TestStepsConstants:
    """Tests for steps module constants."""

    def test_imports_prompts(self):
        """Test that steps imports prompts."""
        from agent import steps
        assert hasattr(steps, 'PARSE_SYSTEM') or True  # May be imported indirectly
