"""AI Test Generator Agent — generates runnable test suites for built apps."""

import asyncio
import json
import logging

from agent.llm import chat, chat_with_reasoning
from agent.prompts import TEST_GEN_SYSTEM
from config import settings

logger = logging.getLogger(__name__)


async def generate_tests(
    code: str,
    app_name: str = "App",
    complexity: str = "simple",
    manifest: dict | None = None,
    all_files: dict[str, str] | None = None,
) -> dict[str, str]:
    """Generate a test suite for the given app code.

    Returns a dict of file_path -> test_content.
    For simple apps: {"tests.html": "..."}
    For fullstack apps: {"tests/app.test.js": "..."}
    """
    if complexity in ("standard", "fullstack") and all_files:
        return await _generate_fullstack_tests(app_name, manifest or {}, all_files)
    return await _generate_simple_tests(code, app_name)


async def _generate_simple_tests(code: str, app_name: str) -> dict[str, str]:
    """Generate an in-browser test suite for a single-file HTML app."""
    user_content = (
        f"Generate a comprehensive test suite for this single-file HTML app called '{app_name}'.\n\n"
        f"APP SOURCE CODE:\n```html\n{code}\n```\n\n"
        f"Generate a tests.html file with an inline test runner. "
        f"Test ALL interactive elements, data persistence, edge cases, and UI states."
    )

    try:
        result = await asyncio.wait_for(
            chat_with_reasoning(
                messages=[
                    {"role": "system", "content": TEST_GEN_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.4,
                max_tokens=8192,
            ),
            timeout=120,
        )
        test_code = _extract_code(result["content"])
    except (TimeoutError, Exception) as e:
        logger.warning("Test generation with reasoning failed: %s, trying fast model", e)
        try:
            raw = await asyncio.wait_for(
                chat(
                    messages=[
                        {"role": "system", "content": TEST_GEN_SYSTEM},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.4,
                    max_tokens=8192,
                    thinking=False,
                    model=settings.GLM_FAST_MODEL,
                ),
                timeout=120,
            )
            test_code = _extract_code(raw)
        except Exception as e2:
            logger.warning("Test generation fallback also failed: %s", e2)
            return {}

    if not test_code:
        return {}

    return {"tests.html": test_code}


async def _generate_fullstack_tests(
    app_name: str, manifest: dict, all_files: dict[str, str]
) -> dict[str, str]:
    """Generate API tests for a fullstack app using Node.js built-in test runner."""
    # Build context from key files only (backend routes + db schema)
    context_parts = []
    for path, content in all_files.items():
        if any(path.startswith(p) for p in ("backend/", "server.", "api.")):
            context_parts.append(f"--- FILE: {path} ---\n{content[:3000]}\n--- END FILE ---")
        elif path in ("package.json", "init-data.js"):
            context_parts.append(f"--- FILE: {path} ---\n{content[:2000]}\n--- END FILE ---")

    if not context_parts:
        # No backend files — fall back to testing the main HTML
        main_html = all_files.get("frontend/index.html", "")
        if main_html:
            return await _generate_simple_tests(main_html, app_name)
        return {}

    context_str = "\n\n".join(context_parts)
    slim_manifest = {
        "app_name": manifest.get("app_name", app_name),
        "features": manifest.get("features", []),
        "tech_stack": manifest.get("tech_stack", {}),
        "files": [{"path": f["path"], "purpose": f["purpose"]} for f in manifest.get("files", [])],
    }

    user_content = (
        f"Generate a comprehensive API test suite for this fullstack app '{app_name}'.\n\n"
        f"PROJECT MANIFEST:\n{json.dumps(slim_manifest, indent=2)}\n\n"
        f"BACKEND FILES:\n{context_str}\n\n"
        f"Generate tests/app.test.js using Node.js built-in test runner (node:test + node:assert). "
        f"Test ALL API endpoints, validation, CRUD operations, and edge cases."
    )

    try:
        result = await asyncio.wait_for(
            chat_with_reasoning(
                messages=[
                    {"role": "system", "content": TEST_GEN_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.4,
                max_tokens=8192,
            ),
            timeout=120,
        )
        test_code = _extract_code(result["content"], lang="javascript")
    except (TimeoutError, Exception) as e:
        logger.warning("Fullstack test generation failed: %s, trying fast model", e)
        try:
            raw = await asyncio.wait_for(
                chat(
                    messages=[
                        {"role": "system", "content": TEST_GEN_SYSTEM},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.4,
                    max_tokens=8192,
                    thinking=False,
                    model=settings.GLM_FAST_MODEL,
                ),
                timeout=120,
            )
            test_code = _extract_code(raw, lang="javascript")
        except Exception as e2:
            logger.warning("Fullstack test generation fallback also failed: %s", e2)
            return {}

    if not test_code:
        return {}

    return {"tests/app.test.js": test_code}


def _extract_code(text: str, lang: str = "html") -> str:
    """Extract code from markdown fences."""
    text = text.strip()

    # Try language-specific fence first
    fence = f"```{lang}"
    if fence in text:
        start = text.find(fence) + len(fence)
        if start < len(text) and text[start] == "\n":
            start += 1
        closing = text.rfind("```", start)
        if closing != -1:
            return text[start:closing].strip()
        return text[start:].strip()

    # Try generic fence
    if "```" in text:
        start = text.find("```") + 3
        # Skip language tag on same line
        newline = text.find("\n", start)
        if newline != -1 and newline - start < 20:
            start = newline + 1
        closing = text.rfind("```", start)
        if closing != -1:
            return text[start:closing].strip()
        return text[start:].strip()

    return text
