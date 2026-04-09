"""Tests for agent/llm.py — streaming, vision, image gen, rate limit retry."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import settings


def _make_response(status_code=200, json_data=None, headers=None):
    """Create a mock httpx Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.headers = headers or {}
    return resp


class _AsyncIter:
    """Helper to make an async iterator from a list — NOT an AsyncMock."""
    def __init__(self, items):
        self._items = items
        self._i = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._i >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._i]
        self._i += 1
        return item


class TestChatBasic:
    @pytest.mark.asyncio
    async def test_chat_returns_text(self):
        mock_resp = _make_response(200, {
            "choices": [{"message": {"content": "Hello world"}, "finish_reason": "stop"}],
            "model": "glm-5",
        })
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agent.llm.httpx.AsyncClient", return_value=mock_client):
            from agent.llm import chat
            result = await chat([{"role": "user", "content": "Hi"}])

        assert result == "Hello world"

    @pytest.mark.asyncio
    async def test_chat_api_error_returns_empty(self):
        mock_resp = _make_response(200, {
            "error": {"message": "Bad request", "code": "invalid"}
        })
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agent.llm.httpx.AsyncClient", return_value=mock_client):
            from agent.llm import chat
            result = await chat([{"role": "user", "content": "Hi"}])

        assert result == ""


class TestChatRateLimitRetry:
    @pytest.mark.asyncio
    async def test_retry_on_429(self):
        rate_resp = _make_response(429, headers={"retry-after": "0"})
        ok_resp = _make_response(200, {
            "choices": [{"message": {"content": "Retried!"}, "finish_reason": "stop"}],
        })
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[rate_resp, ok_resp])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agent.llm.httpx.AsyncClient", return_value=mock_client):
            with patch("agent.llm.asyncio.sleep", new=AsyncMock()):
                from agent.llm import chat
                result = await chat([{"role": "user", "content": "Hi"}], retries=1)

        assert result == "Retried!"

    @pytest.mark.asyncio
    async def test_retry_on_api_rate_limit_error(self):
        """Test retry when rate limit is returned in response body (not HTTP status)."""
        rate_resp = _make_response(200, {
            "error": {"message": "Rate limit exceeded", "code": "1302"}
        })
        ok_resp = _make_response(200, {
            "choices": [{"message": {"content": "Success"}, "finish_reason": "stop"}],
        })
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[rate_resp, ok_resp])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agent.llm.httpx.AsyncClient", return_value=mock_client):
            with patch("agent.llm.asyncio.sleep", new=AsyncMock()):
                from agent.llm import chat
                result = await chat([{"role": "user", "content": "Hi"}], retries=1)

        assert result == "Success"


class TestChatFallback:
    @pytest.mark.asyncio
    async def test_fallback_on_rate_limit(self):
        """Primary model gets rate-limited, fallback model succeeds."""
        rate_resp = _make_response(200, {
            "error": {"message": "rate limit exceeded", "code": "rate_limit"}
        })
        ok_resp = _make_response(200, {
            "choices": [{"message": {"content": "From fallback"}, "finish_reason": "stop"}],
        })
        mock_client = AsyncMock()
        # retries=0: primary gets 1 attempt (rate-limited, falls through to fallback)
        # fallback gets 1 attempt (success)
        mock_client.post = AsyncMock(side_effect=[rate_resp, ok_resp])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agent.llm.httpx.AsyncClient", return_value=mock_client):
            with patch("agent.llm.asyncio.sleep", new=AsyncMock()):
                from agent.llm import chat
                result = await chat(
                    [{"role": "user", "content": "Hi"}],
                    model="primary-model",
                    fallback_model="fallback-model",
                    retries=0,
                )

        assert result == "From fallback"


class TestChatWithReasoning:
    @pytest.mark.asyncio
    async def test_reasoning_response(self):
        mock_resp = _make_response(200, {
            "choices": [{"message": {"content": "The answer", "reasoning_content": "I thought about it"}}],
        })
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agent.llm.httpx.AsyncClient", return_value=mock_client):
            from agent.llm import chat_with_reasoning
            result = await chat_with_reasoning([{"role": "user", "content": "Think"}])

        assert result["content"] == "The answer"
        assert result["reasoning"] == "I thought about it"

    @pytest.mark.asyncio
    async def test_reasoning_error(self):
        mock_resp = _make_response(200, {"error": {"message": "Failed"}})
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agent.llm.httpx.AsyncClient", return_value=mock_client):
            from agent.llm import chat_with_reasoning
            result = await chat_with_reasoning([{"role": "user", "content": "Think"}])

        assert result["content"] == ""
        assert result["reasoning"] == ""


class TestVisionChat:
    @pytest.mark.asyncio
    async def test_vision_success(self):
        mock_resp = _make_response(200, {
            "choices": [{"message": {"content": "I see a button", "reasoning_content": "Looking at image"}}],
        })
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agent.llm.httpx.AsyncClient", return_value=mock_client):
            from agent.llm import vision_chat
            result = await vision_chat(["base64imgdata"], "What do you see?")

        assert result["content"] == "I see a button"

    @pytest.mark.asyncio
    async def test_vision_error(self):
        mock_resp = _make_response(200, {"error": {"message": "Vision failed"}})
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agent.llm.httpx.AsyncClient", return_value=mock_client):
            from agent.llm import vision_chat
            result = await vision_chat(["data"], "Describe")

        assert result["content"] == ""


class TestGenerateImage:
    @pytest.mark.asyncio
    async def test_generate_image_disabled(self):
        with patch.object(settings, "ENABLE_IMAGE_GEN", False):
            from agent.llm import generate_image
            result = await generate_image("A sunset")
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_image_success(self):
        mock_resp = _make_response(200, {
            "data": [{"url": "https://cdn.example.com/img.png"}],
        })
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agent.llm.httpx.AsyncClient", return_value=mock_client):
            with patch.object(settings, "ENABLE_IMAGE_GEN", True):
                from agent.llm import generate_image
                result = await generate_image("A sunset")

        assert result == "https://cdn.example.com/img.png"

    @pytest.mark.asyncio
    async def test_generate_image_error(self):
        mock_resp = _make_response(200, {"error": {"message": "NSFW content"}})
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agent.llm.httpx.AsyncClient", return_value=mock_client):
            with patch.object(settings, "ENABLE_IMAGE_GEN", True):
                from agent.llm import generate_image
                result = await generate_image("Bad prompt")

        assert result is None

    @pytest.mark.asyncio
    async def test_generate_image_exception(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Network error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agent.llm.httpx.AsyncClient", return_value=mock_client):
            with patch.object(settings, "ENABLE_IMAGE_GEN", True):
                from agent.llm import generate_image
                result = await generate_image("A sunset")

        assert result is None


class TestChatStreaming:
    @pytest.mark.asyncio
    async def test_streaming_success(self):
        lines = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            'data: {"choices":[{"delta":{"content":" World"}}]}',
            'data: [DONE]',
        ]

        mock_response = MagicMock()
        mock_response.aiter_lines = MagicMock(return_value=_AsyncIter(lines))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        chunks_received = []

        async def on_chunk(text):
            chunks_received.append(text)

        with patch("agent.llm.httpx.AsyncClient", return_value=mock_client):
            from agent.llm import chat_streaming
            result = await chat_streaming(
                [{"role": "user", "content": "Hi"}],
                on_chunk=on_chunk,
            )

        assert result == "Hello World"
        assert len(chunks_received) == 2

    @pytest.mark.asyncio
    async def test_streaming_exception_returns_empty(self):
        mock_client = AsyncMock()
        mock_client.stream = MagicMock(side_effect=Exception("Connection lost"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agent.llm.httpx.AsyncClient", return_value=mock_client):
            from agent.llm import chat_streaming
            result = await chat_streaming(
                [{"role": "user", "content": "Hi"}],
                on_chunk=AsyncMock(),
            )

        assert result == ""
