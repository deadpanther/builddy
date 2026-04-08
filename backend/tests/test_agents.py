"""Tests for agent/agents.py."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestAgentsModule:
    """Tests for agents module."""

    def test_module_imports(self):
        """Test that agents module can be imported."""
        from agent import agents
        assert agents is not None

    def test_write_prd_exists(self):
        """Test that write_prd function exists."""
        from agent.agents import write_prd
        assert callable(write_prd)

    def test_create_design_system_exists(self):
        """Test that create_design_system function exists."""
        from agent.agents import create_design_system
        assert callable(create_design_system)

    def test_qa_validate_exists(self):
        """Test that qa_validate function exists."""
        from agent.agents import qa_validate
        assert callable(qa_validate)

    def test_polish_pass_exists(self):
        """Test that polish_pass function exists."""
        from agent.agents import polish_pass
        assert callable(polish_pass)

    def test_visual_validate_exists(self):
        """Test that visual_validate function exists."""
        from agent.agents import visual_validate
        assert callable(visual_validate)


class TestWritePrd:
    """Tests for write_prd function."""

    @pytest.mark.asyncio
    async def test_write_prd_returns_dict(self):
        """Test that write_prd returns a dict."""
        from agent.agents import write_prd
        
        mock_response = {
            "content": "# PRD\n## Overview\nThis is a test PRD.",
            "reasoning": "Thoughts about requirements",
        }
        
        with patch('agent.agents.chat_with_reasoning', new=AsyncMock(return_value=mock_response)):
            with patch('agent.agents._add_step'):
                with patch('agent.agents._add_reasoning'):
                    result = await write_prd("test-build-id", "Build a todo app")
        
        assert isinstance(result, dict)
        # Returns PRD data with product_name, user_stories, etc.
        assert "product_name" in result or "user_stories" in result

    @pytest.mark.asyncio
    async def test_write_prd_handles_timeout(self):
        """Test that write_prd handles timeout."""
        from agent.agents import write_prd
        import asyncio
        
        mock_response = "# Fallback PRD\n## Overview\nBasic requirements."
        
        with patch('agent.agents.chat_with_reasoning', new=AsyncMock(side_effect=asyncio.TimeoutError())):
            with patch('agent.agents.chat', new=AsyncMock(return_value=mock_response)):
                with patch('agent.agents._add_step'):
                    result = await write_prd("test-build-id", "Build a timer app")
        
        assert isinstance(result, dict)


class TestCreateDesignSystem:
    """Tests for create_design_system function."""

    @pytest.mark.asyncio
    async def test_create_design_system_returns_dict(self):
        """Test that create_design_system returns a dict."""
        from agent.agents import create_design_system
        
        mock_response = {
            "content": "Design tokens:\n- primary: blue\n- secondary: gray",
            "reasoning": None,
        }
        
        with patch('agent.agents.chat_with_reasoning', new=AsyncMock(return_value=mock_response)):
            with patch('agent.agents._add_step'):
                result = await create_design_system("test-build-id", "Modern app", {"prd": "test"})
        
        assert isinstance(result, dict)


class TestQaValidate:
    """Tests for qa_validate function."""

    @pytest.mark.asyncio
    async def test_qa_validate_returns_string(self):
        """Test that qa_validate returns a string."""
        from agent.agents import qa_validate
        
        mock_response = {
            "content": "<html><body>Validated</body></html>",
            "reasoning": None,
        }
        
        with patch('agent.agents.chat_with_reasoning', new=AsyncMock(return_value=mock_response)):
            with patch('agent.agents._add_step'):
                result = await qa_validate("test-build-id", "<html></html>", {"prd": "test"})
        
        assert isinstance(result, str)


class TestPolishPass:
    """Tests for polish_pass function."""

    @pytest.mark.asyncio
    async def test_polish_pass_returns_string(self):
        """Test that polish_pass returns a string."""
        from agent.agents import polish_pass
        
        mock_response = {
            "content": "<html><body>Polished</body></html>",
            "reasoning": None,
        }
        
        with patch('agent.agents.chat_with_reasoning', new=AsyncMock(return_value=mock_response)):
            with patch('agent.agents._add_step'):
                result = await polish_pass("test-build-id", "<html></html>")
        
        assert isinstance(result, str)


class TestVisualValidate:
    """Tests for visual_validate function."""

    @pytest.mark.asyncio
    async def test_visual_validate_returns_string(self):
        """Test that visual_validate returns a string."""
        from agent.agents import visual_validate
        
        mock_response = "<html><body>Validated</body></html>"
        
        with patch('agent.agents.vision_chat', new=AsyncMock(return_value=mock_response)):
            with patch('agent.agents._add_step'):
                result = await visual_validate("test-build-id", "<html></html>")
        
        assert isinstance(result, str)


class TestAgentPrompts:
    """Tests for agent prompts."""

    def test_prd_system_exists(self):
        """Test PRD_SYSTEM prompt exists."""
        from agent.prompts import PRD_SYSTEM
        assert isinstance(PRD_SYSTEM, str)
        assert len(PRD_SYSTEM) > 0

    def test_design_system_prompt_exists(self):
        """Test DESIGN_SYSTEM_PROMPT exists."""
        from agent.prompts import DESIGN_SYSTEM_PROMPT
        assert isinstance(DESIGN_SYSTEM_PROMPT, str)

    def test_qa_system_exists(self):
        """Test QA_SYSTEM prompt exists."""
        from agent.prompts import QA_SYSTEM
        assert isinstance(QA_SYSTEM, str)

    def test_polish_system_exists(self):
        """Test POLISH_SYSTEM prompt exists."""
        from agent.prompts import POLISH_SYSTEM
        assert isinstance(POLISH_SYSTEM, str)
