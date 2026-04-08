"""GLM API client — supports chat, thinking mode, vision (5V-Turbo), image gen (CogView-4),
   with automatic rate-limit retry, model fallback, and tiered model selection."""

import asyncio
import json
import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)

# Rate-limit backoff settings
RATE_LIMIT_CODES = {429, 503, 529}
RATE_LIMIT_INITIAL_WAIT = 3      # seconds
RATE_LIMIT_MAX_WAIT = 30         # seconds


async def _request_with_fallback(
    payload: dict,
    fallback_model: str | None = None,
    retries: int = 1,
) -> dict:
    """Make a GLM API request with rate-limit retry and optional model fallback.

    Returns the raw response JSON dict.
    Raises on unrecoverable errors after exhausting retries.
    """
    primary_model = payload["model"]
    models_to_try = [primary_model]
    if fallback_model and fallback_model != primary_model:
        models_to_try.append(fallback_model)

    for model in models_to_try:
        payload_copy = {**payload, "model": model}
        wait = RATE_LIMIT_INITIAL_WAIT

        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient(timeout=300) as client:
                    resp = await client.post(
                        f"{settings.GLM_BASE_URL}chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.GLM_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json=payload_copy,
                    )

                # Check for rate limit via HTTP status
                if resp.status_code in RATE_LIMIT_CODES:
                    retry_after = resp.headers.get("retry-after")
                    wait_time = int(retry_after) if retry_after else wait
                    logger.warning(
                        "Rate limited (HTTP %d) on %s — waiting %ds (attempt %d/%d)",
                        resp.status_code, model, wait_time, attempt + 1, retries + 1,
                    )
                    await asyncio.sleep(wait_time)
                    wait = min(wait * 2, RATE_LIMIT_MAX_WAIT)
                    continue

                data = resp.json()

                # Check for rate limit via error response body
                if "error" in data:
                    err_code = data["error"].get("code", "")
                    err_msg = str(data["error"].get("message", ""))
                    if "rate" in err_msg.lower() or "concurrency" in err_msg.lower() or err_code == "1302":
                        logger.warning(
                            "Rate limited (API error) on %s — waiting %ds (attempt %d/%d): %s",
                            model, wait, attempt + 1, retries + 1, err_msg[:100],
                        )
                        await asyncio.sleep(wait)
                        wait = min(wait * 2, RATE_LIMIT_MAX_WAIT)
                        continue

                    # Non-rate-limit API error
                    logger.error("GLM API error on %s: %s", model, json.dumps(data["error"])[:200])
                    if attempt < retries:
                        await asyncio.sleep(2)
                        continue
                    break  # try fallback model

                return data

            except httpx.TimeoutException:
                logger.warning("GLM timeout on %s (attempt %d/%d)", model, attempt + 1, retries + 1)
                if attempt < retries:
                    await asyncio.sleep(wait)
                    wait = min(wait * 2, RATE_LIMIT_MAX_WAIT)
                    continue
                break  # try fallback model

            except Exception as e:
                logger.error("GLM request failed on %s (attempt %d/%d): %s", model, attempt + 1, retries + 1, e)
                if attempt < retries:
                    await asyncio.sleep(2)
                    continue
                break  # try fallback model

        if model != models_to_try[-1]:
            logger.info("Falling back from %s to %s", model, models_to_try[-1])

    return {"error": {"message": "All models exhausted after retries"}}


async def chat(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 8192,
    retries: int = 2,
    model: str | None = None,
    tools: list[dict] | None = None,
    thinking: bool | None = None,
    fallback_model: str | None = None,
) -> str:
    """Send a chat completion request to GLM and return the assistant text.

    *thinking* controls the thinking/reasoning mode.  ``None`` (default) follows
    the global ``ENABLE_THINKING`` setting; ``True``/``False`` override it.
    *fallback_model* is tried if the primary model is rate-limited.
    """
    use_model = model or settings.GLM_MODEL
    use_fallback = fallback_model or settings.GLM_FALLBACK_MODEL
    logger.info("GLM chat → %s (%d messages)", use_model, len(messages))

    enable_thinking = thinking if thinking is not None else settings.ENABLE_THINKING

    payload: dict = {
        "model": use_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if enable_thinking:
        payload["thinking"] = {"type": "enabled"}

    if tools:
        payload["tools"] = tools

    data = await _request_with_fallback(payload, fallback_model=use_fallback, retries=retries)

    if "error" in data:
        logger.warning("GLM chat failed: %s", json.dumps(data["error"])[:200])
        return ""

    text = data["choices"][0]["message"].get("content") or ""
    finish = data["choices"][0].get("finish_reason", "unknown")

    if text.strip():
        actual_model = data.get("model", use_model)
        logger.info("GLM response (%s): %d chars (finish=%s)", actual_model, len(text), finish)
        return text

    logger.warning("Empty GLM response (finish=%s)", finish)
    return ""


async def chat_with_reasoning(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 8192,
    retries: int = 2,
    model: str | None = None,
    tools: list[dict] | None = None,
    fallback_model: str | None = None,
) -> dict:
    """Chat with thinking mode — returns {"content": str, "reasoning": str}.

    *fallback_model* is tried if the primary model is rate-limited.
    """
    use_model = model or settings.GLM_MODEL
    use_fallback = fallback_model or settings.GLM_FALLBACK_MODEL
    logger.info("GLM chat+reasoning → %s (%d messages)", use_model, len(messages))

    payload: dict = {
        "model": use_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "thinking": {"type": "enabled"},
    }

    if tools:
        payload["tools"] = tools

    data = await _request_with_fallback(payload, fallback_model=use_fallback, retries=retries)

    if "error" in data:
        logger.warning("GLM reasoning failed: %s", json.dumps(data["error"])[:200])
        return {"content": "", "reasoning": ""}

    msg = data["choices"][0]["message"]
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or ""

    if content.strip():
        actual_model = data.get("model", use_model)
        logger.info(
            "GLM response (%s): %d chars content, %d chars reasoning",
            actual_model, len(content), len(reasoning),
        )
        return {"content": content, "reasoning": reasoning}

    logger.warning("Empty GLM reasoning response")
    return {"content": "", "reasoning": ""}


async def vision_chat(
    images_base64: list[str],
    text_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 16384,
    retries: int = 2,
) -> dict:
    """Send image(s) + text to GLM-5V-Turbo. Returns {"content": str, "reasoning": str}."""
    model = settings.GLM_VISION_MODEL
    logger.info("GLM vision → %s (%d images, prompt: %d chars)", model, len(images_base64), len(text_prompt))

    content_parts: list[dict] = []
    for img_b64 in images_base64:
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"},
        })
    content_parts.append({"type": "text", "text": text_prompt})

    messages = [{"role": "user", "content": content_parts}]

    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "thinking": {"type": "enabled"},
    }

    data = await _request_with_fallback(payload, retries=retries)

    if "error" in data:
        logger.warning("GLM vision failed: %s", json.dumps(data["error"])[:200])
        return {"content": "", "reasoning": ""}

    msg = data["choices"][0]["message"]
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or ""

    if content.strip():
        logger.info("GLM vision response: %d chars", len(content))
        return {"content": content, "reasoning": reasoning}

    logger.warning("Empty vision response")
    return {"content": "", "reasoning": ""}


async def chat_streaming(
    messages: list[dict],
    on_chunk: callable,
    temperature: float = 0.7,
    max_tokens: int = 8192,
    model: str | None = None,
) -> str:
    """Stream a chat response, calling on_chunk(accumulated_text) for each token.

    Returns the full accumulated text. No thinking mode (streaming + thinking
    don't combine well on most APIs).
    """
    use_model = model or settings.GLM_FAST_MODEL
    logger.info("GLM streaming → %s (%d messages)", use_model, len(messages))

    payload = {
        "model": use_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    accumulated = ""
    try:
        async with httpx.AsyncClient(timeout=300) as client, client.stream(
            "POST",
            f"{settings.GLM_BASE_URL}chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        ) as response:
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        accumulated += content
                        await on_chunk(accumulated)
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue

        logger.info("GLM streaming complete: %d chars", len(accumulated))
        return accumulated

    except Exception as e:
        logger.error("GLM streaming failed: %s", e)
        if accumulated:
            return accumulated
        return ""


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
