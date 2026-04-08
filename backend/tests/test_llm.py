"""Tests for agent/llm.py - LLM integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestLLMModule:
    """Tests for LLM module."""

    def test_module_imports(self):
        """Test that llm module can be imported."""
        from agent import llm
        assert llm is not None

    def test_chat_function_exists(self):
        """Test that chat function exists."""
        from agent.llm import chat
        assert callable(chat)

    def test_chat_with_reasoning_exists(self):
        """Test that chat_with_reasoning function exists."""
        from agent.llm import chat_with_reasoning
        assert callable(chat_with_reasoning)


class TestLLMFunctions:
    """Tests for LLM functions."""

    @pytest.mark.asyncio
    async def test_chat_returns_string(self):
        """Test that chat returns a string."""
        from agent.llm import chat

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await chat(messages=[{"role": "user", "content": "Hello"}])

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_chat_with_empty_messages(self):
        """Test chat with empty messages."""
        from agent.llm import chat

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": ""}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await chat(messages=[])

        assert result == ""


class TestGenerateImage:
    """Tests for image generation."""

    def test_generate_image_exists(self):
        """Test that generate_image function exists."""
        from agent.llm import generate_image
        assert callable(generate_image)


class TestLLMSettings:
    """Tests for LLM settings usage."""

    def test_settings_import(self):
        """Test that settings is imported."""
        from agent.llm import settings
        assert settings is not None

    def test_api_key_from_settings(self):
        """Test that API key comes from settings."""
        from agent.llm import settings
        assert hasattr(settings, 'GLM_API_KEY')
