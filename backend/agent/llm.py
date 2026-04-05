"""GLM API client — direct httpx calls matching the working curl approach."""

import asyncio
import json
import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)


async def chat(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 8192,
    retries: int = 1,
    **kwargs,
) -> str:
    """Send a chat completion request to GLM and return the assistant text."""
    logger.info("Sending request to GLM %s (%d messages)", settings.GLM_MODEL, len(messages))

    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(
                    f"{settings.GLM_BASE_URL}chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.GLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.GLM_MODEL,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                data = resp.json()

            if "error" in data:
                logger.error("GLM API error: %s", json.dumps(data["error"]))
                if attempt < retries:
                    await asyncio.sleep(2)
                continue

            text = data["choices"][0]["message"].get("content") or ""
            finish = data["choices"][0].get("finish_reason", "unknown")

            if text.strip():
                logger.info("GLM response: %d chars (finish=%s)", len(text), finish)
                return text

            # Debug: log raw response when empty
            logger.warning(
                "Empty GLM response (finish=%s, attempt %d/%d). Raw keys: %s. Usage: %s",
                finish, attempt + 1, retries + 1,
                list(data["choices"][0]["message"].keys()),
                json.dumps(data.get("usage", {})),
            )

        except Exception as e:
            logger.error("GLM request failed (attempt %d/%d): %s", attempt + 1, retries + 1, e)

        if attempt < retries:
            await asyncio.sleep(2)

    logger.warning("GLM returned empty after %d attempts", retries + 1)
    return ""
