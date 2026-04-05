"""GLM API client — supports chat, thinking mode, vision (5V-Turbo), and image gen (CogView-4)."""

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
    model: str | None = None,
    tools: list[dict] | None = None,
) -> str:
    """Send a chat completion request to GLM and return the assistant text."""
    use_model = model or settings.GLM_MODEL
    logger.info("GLM chat → %s (%d messages)", use_model, len(messages))

    for attempt in range(retries + 1):
        try:
            payload: dict = {
                "model": use_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if settings.ENABLE_THINKING:
                payload["thinking"] = {"type": "enabled"}

            if tools:
                payload["tools"] = tools

            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(
                    f"{settings.GLM_BASE_URL}chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.GLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
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

            logger.warning(
                "Empty GLM response (finish=%s, attempt %d/%d). Keys: %s. Usage: %s",
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


async def chat_with_reasoning(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 8192,
    retries: int = 1,
    model: str | None = None,
    tools: list[dict] | None = None,
) -> dict:
    """Chat with thinking mode — returns {"content": str, "reasoning": str}."""
    use_model = model or settings.GLM_MODEL
    logger.info("GLM chat+reasoning → %s (%d messages)", use_model, len(messages))

    for attempt in range(retries + 1):
        try:
            payload: dict = {
                "model": use_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "thinking": {"type": "enabled"},
            }

            if tools:
                payload["tools"] = tools

            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(
                    f"{settings.GLM_BASE_URL}chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.GLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                data = resp.json()

            if "error" in data:
                logger.error("GLM API error: %s", json.dumps(data["error"]))
                if attempt < retries:
                    await asyncio.sleep(2)
                continue

            msg = data["choices"][0]["message"]
            content = msg.get("content") or ""
            reasoning = msg.get("reasoning_content") or ""

            if content.strip():
                logger.info(
                    "GLM response: %d chars content, %d chars reasoning",
                    len(content), len(reasoning),
                )
                return {"content": content, "reasoning": reasoning}

            logger.warning("Empty GLM response (attempt %d/%d)", attempt + 1, retries + 1)

        except Exception as e:
            logger.error("GLM reasoning request failed (attempt %d/%d): %s", attempt + 1, retries + 1, e)

        if attempt < retries:
            await asyncio.sleep(2)

    return {"content": "", "reasoning": ""}


async def vision_chat(
    images_base64: list[str],
    text_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 16384,
    retries: int = 1,
) -> dict:
    """Send image(s) + text to GLM-5V-Turbo. Returns {"content": str, "reasoning": str}."""
    model = settings.GLM_VISION_MODEL
    logger.info("GLM vision → %s (%d images, prompt: %d chars)", model, len(images_base64), len(text_prompt))

    content_parts: list[dict] = []
    for i, img_b64 in enumerate(images_base64):
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"},
        })
    content_parts.append({"type": "text", "text": text_prompt})

    messages = [{"role": "user", "content": content_parts}]

    for attempt in range(retries + 1):
        try:
            payload: dict = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "thinking": {"type": "enabled"},
            }

            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(
                    f"{settings.GLM_BASE_URL}chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.GLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                data = resp.json()

            if "error" in data:
                logger.error("GLM vision API error: %s", json.dumps(data["error"]))
                if attempt < retries:
                    await asyncio.sleep(2)
                continue

            msg = data["choices"][0]["message"]
            content = msg.get("content") or ""
            reasoning = msg.get("reasoning_content") or ""

            if content.strip():
                logger.info("GLM vision response: %d chars", len(content))
                return {"content": content, "reasoning": reasoning}

            logger.warning("Empty vision response (attempt %d/%d)", attempt + 1, retries + 1)

        except Exception as e:
            logger.error("GLM vision failed (attempt %d/%d): %s", attempt + 1, retries + 1, e)

        if attempt < retries:
            await asyncio.sleep(2)

    return {"content": "", "reasoning": ""}


async def generate_image(prompt: str, size: str = "1024x1024") -> str | None:
    """Generate an image with CogView-4. Returns the image URL or None."""
    if not settings.ENABLE_IMAGE_GEN:
        return None

    model = settings.GLM_IMAGE_MODEL
    logger.info("CogView-4 image gen → %s", prompt[:80])

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{settings.GLM_BASE_URL}images/generations",
                headers={
                    "Authorization": f"Bearer {settings.GLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "prompt": prompt,
                    "size": size,
                },
            )
            data = resp.json()

        if "error" in data:
            logger.error("CogView-4 error: %s", json.dumps(data["error"]))
            return None

        url = data["data"][0]["url"]
        logger.info("CogView-4 image generated: %s", url[:80])
        return url

    except Exception as e:
        logger.error("CogView-4 failed: %s", e)
        return None
