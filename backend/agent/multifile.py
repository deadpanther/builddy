"""Multi-file generation and modification: classify, manifest, per-file gen, integration review."""

import asyncio
import json
import logging

from agent.helpers import (
    STEP_TIMEOUT,
    FILE_TIMEOUT,
    _update_build,
    _add_step,
    _add_reasoning,
    _strip_fences,
)
from agent.llm import chat, chat_with_reasoning, chat_streaming
from agent.prompts import (
    CLASSIFY_SYSTEM,
    MANIFEST_SYSTEM,
    FILEGEN_SYSTEM,
    INTEGRATION_SYSTEM,
    DOCKERFILE_TEMPLATE,
    DOCKER_COMPOSE_TEMPLATE,
    PACKAGE_JSON_TEMPLATE,
    README_TEMPLATE,
    IMPACT_SYSTEM,
    MODIFY_FILE_SYSTEM,
    SEED_SYSTEM,
)
from agent.components import COMPONENT_LIBRARY
from config import settings
from services.event_bus import publish as _publish_event

logger = logging.getLogger(__name__)


# ── Multi-File Pipeline Steps ────────────────────────────────────────────────

async def classify_complexity(build_id: str, prompt: str) -> dict:
    """Classify the request into simple/standard/fullstack tier."""
    _add_step(build_id, "Classifying app complexity...")

    result = await chat(
        messages=[
            {"role": "system", "content": CLASSIFY_SYSTEM},
            {"role": "user", "content": f"Classify this app request:\n\n{prompt}"},
        ],
        temperature=0.3,
    )

    try:
        text = result.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        classification = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        classification = {
            "complexity": "simple",
            "reasoning": "Failed to classify, defaulting to simple",
            "app_name": "my-app",
            "app_type": "other",
            "suggested_features": [],
            "needs_backend": False,
            "needs_database": False,
            "needs_auth": False,
        }

    complexity = classification.get("complexity", "simple")
    _update_build(
        build_id,
        complexity=complexity,
        app_name=classification.get("app_name", "my-app"),
        app_description=classification.get("reasoning", ""),
    )
    _add_step(build_id, f"Classified as {complexity}: {classification.get('reasoning', '')}")
    return classification


async def plan_manifest(build_id: str, prompt: str, classification: dict) -> dict:
    """Plan the full file manifest for a multi-file project."""
    _update_build(build_id, status="planning")
    _add_step(build_id, "Planning project file manifest with GLM 5.1 thinking mode...")

    user_content = (
        f"Plan the file manifest for this app:\n\n"
        f"Request: {prompt}\n\n"
        f"Classification: {json.dumps(classification, indent=2)}"
    )

    try:
        result = await chat_with_reasoning(
            messages=[
                {"role": "system", "content": MANIFEST_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.5,
        )
        manifest_text = result["content"]
        reasoning = result["reasoning"]

        if reasoning:
            _add_reasoning(build_id, "manifest_planning", reasoning)
            _add_step(build_id, f"[thinking] GLM planned the project architecture ({len(reasoning)} chars)")
    except Exception as e:
        logger.warning("Manifest planning with reasoning failed, falling back: %s", e)
        manifest_text = await chat(
            messages=[
                {"role": "system", "content": MANIFEST_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.5,
            thinking=False,
        )

    try:
        text = manifest_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        manifest = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        raise ValueError("GLM returned invalid manifest JSON — cannot proceed")

    # Sort files by generation order
    manifest["files"] = sorted(manifest.get("files", []), key=lambda f: f.get("order", 99))

    _update_build(
        build_id,
        file_manifest=json.dumps(manifest),
        tech_stack=json.dumps(manifest.get("tech_stack", {})),
    )
    file_count = len(manifest.get("files", []))
    _add_step(build_id, f"Manifest planned: {file_count} files to generate")
    return manifest


async def generate_file(
    build_id: str,
    manifest: dict,
    file_entry: dict,
    generated_so_far: dict[str, str],
    file_index: int,
    total_files: int,
) -> str:
    """Generate a single file using the manifest and previously generated files as context."""
    file_path = file_entry["path"]
    _add_step(build_id, f"Generating file {file_index + 1}/{total_files}: {file_path}")

    # Build context from previously generated files — only include DEPENDENCIES
    # to avoid sending 200K+ of irrelevant context that slows generation
    deps = set(file_entry.get("dependencies", []))
    context_parts = []
    for prev_path, prev_content in generated_so_far.items():
        if prev_path in deps:
            # Full content for direct dependencies
            context_parts.append(f"--- FILE: {prev_path} ---\n{prev_content}\n--- END FILE ---")
        elif prev_path.endswith((".js", ".html")) and len(prev_content) < 2000:
            # Small files get included in full
            context_parts.append(f"--- FILE: {prev_path} ---\n{prev_content}\n--- END FILE ---")
        else:
            # Large non-dependency files: include first 80 lines only (API routes, schema, exports)
            lines = prev_content.split("\n")
            summary = "\n".join(lines[:80])
            if len(lines) > 80:
                summary += f"\n... ({len(lines) - 80} more lines)"
            context_parts.append(f"--- FILE: {prev_path} (summary) ---\n{summary}\n--- END FILE ---")
    context_str = "\n\n".join(context_parts) if context_parts else "(No files generated yet)"

    # Inject a slim component reference for the FIRST HTML file only (index.html)
    # Other HTML files get just the CSS animations + dark mode snippet
    component_ref = ""
    if file_path == "frontend/index.html":
        component_ref = f"\n\n{COMPONENT_LIBRARY}\n\nUse the component patterns above as building blocks for the UI."
    elif file_path.startswith("frontend/") and file_path.endswith(".html"):
        component_ref = (
            "\n\nINCLUDE THESE IN YOUR HTML:\n"
            "- <script src='https://cdn.tailwindcss.com'></script>\n"
            "- Dark mode: use dark: prefix, add toggle calling toggleDark()\n"
            "- CSS animations: @keyframes fade-in, scale-in, slide-up (see app's index.html for reference)\n"
            "- Match the SAME header/nav/styling as index.html for consistency\n"
        )

    # Slim manifest: only include file list overview + tech stack, not full details
    slim_manifest = {
        "app_name": manifest.get("app_name"),
        "description": manifest.get("description"),
        "tech_stack": manifest.get("tech_stack"),
        "features": manifest.get("features"),
        "files": [{"path": f["path"], "purpose": f["purpose"]} for f in manifest.get("files", [])],
    }

    user_content = (
        f"Generate the file: {file_path}\n\n"
        f"PURPOSE: {file_entry.get('purpose', 'See manifest')}\n\n"
        f"PROJECT OVERVIEW:\n{json.dumps(slim_manifest, indent=2)}\n\n"
        f"REFERENCE FILES:\n{context_str}"
        f"{component_ref}"
    )

    # Only enable web search for the MAIN frontend page (index.html), not every file
    tools = None
    is_main_page = file_path == "frontend/index.html"
    if is_main_page and settings.ENABLE_WEB_SEARCH:
        tools = [
            {
                "type": "web_search",
                "web_search": {
                    "enable": "True",
                    "search_engine": "search-prime",
                    "search_result": "True",
                    "count": "2",
                    "search_recency_filter": "noLimit",
                },
            }
        ]
        _add_step(build_id, f"[skill:web-search] Researching UI patterns for {file_path}...")

    # Stream file generation so the frontend sees code appear in real time
    # Publish chunks every ~500 chars to avoid flooding the event bus
    _last_publish_len = 0

    async def _on_chunk(accumulated: str):
        nonlocal _last_publish_len
        if len(accumulated) - _last_publish_len >= 300:
            _publish_event(build_id, "file_chunk", {
                "file_path": file_path,
                "content": accumulated,
                "done": False,
            })
            _last_publish_len = len(accumulated)

    # Publish that we're starting this file
    _publish_event(build_id, "file_streaming_start", {"file_path": file_path})

    code = ""
    try:
        raw = await asyncio.wait_for(
            chat_streaming(
                messages=[
                    {"role": "system", "content": FILEGEN_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
                on_chunk=_on_chunk,
                temperature=0.5,
                max_tokens=8192,
                model=settings.GLM_FAST_MODEL,
            ),
            timeout=FILE_TIMEOUT,
        )
        code = raw.strip()
    except asyncio.TimeoutError:
        _add_step(build_id, f"Streaming timed out for {file_path} — trying fallback...")

    # Strip markdown fences if present
    if code.startswith("```"):
        first_newline = code.index("\n") if "\n" in code else 3
        code = code[first_newline + 1:]
    if code.endswith("```"):
        code = code[:-3].strip()

    if not code:
        # Fallback: non-streaming with fallback model
        _add_step(build_id, f"Retrying {file_path} (non-streaming fallback)...")
        try:
            fallback_result = await asyncio.wait_for(
                chat(
                    messages=[
                        {"role": "system", "content": FILEGEN_SYSTEM},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.5,
                    max_tokens=8192,
                    thinking=False,
                    retries=2,
                    model=settings.GLM_FALLBACK_MODEL,
                ),
                timeout=FILE_TIMEOUT,
            )
            code = _strip_fences(fallback_result)
        except asyncio.TimeoutError:
            _add_step(build_id, f"Fallback also timed out for {file_path}")
            code = ""

    # Publish final content
    if code:
        _publish_event(build_id, "file_chunk", {
            "file_path": file_path,
            "content": code,
            "done": True,
        })

    if not code:
        raise ValueError(f"GLM returned empty content for {file_path}")

    _add_step(build_id, f"Generated {file_path} ({len(code)} chars)")
    return code


async def generate_all_files(build_id: str, manifest: dict, existing_files: dict[str, str] | None = None) -> dict[str, str]:
    """Generate all files in the manifest sequentially (backend-first order).

    If *existing_files* is provided (e.g. from a retry), already-generated files
    are skipped and used as context for the remaining ones.
    """
    _update_build(build_id, status="coding")
    files = manifest.get("files", [])
    total = len(files)
    generated: dict[str, str] = dict(existing_files) if existing_files else {}

    skipped = sum(1 for f in files if f["path"] in generated)
    if skipped:
        _add_step(build_id, f"Resuming generation: {skipped}/{total} files already done")
    else:
        _add_step(build_id, f"Generating {total} files sequentially (backend first)...")

    for i, file_entry in enumerate(files):
        file_path = file_entry["path"]
        if file_path in generated:
            continue  # already generated (retry case)
        content = await generate_file(build_id, manifest, file_entry, generated, i, total)
        generated[file_path] = content
        # Save after each file so retry can resume from here
        _update_build(build_id, generated_files=json.dumps(generated))
        # Notify SSE clients that a new file is ready
        _publish_event(build_id, "file_generated", {
            "file_path": file_path,
            "file_count": len(generated),
            "total_files": total,
            "chars": len(content),
        })
        # Small delay between files to avoid rate limit bursting
        if i < total - 1:
            await asyncio.sleep(1)

    _add_step(build_id, f"All {total} files generated ({sum(len(v) for v in generated.values())} total chars)")
    return generated


def _extract_interface(content: str, max_lines: int = 50) -> str:
    """Extract the 'interface' of a file — imports, exports, routes, schema.

    For backend files: first 50 lines (schema + route definitions).
    For frontend files: first 30 lines (imports + structure) + any fetch() lines.
    """
    lines = content.split("\n")
    head = lines[:max_lines]

    # Also grab lines with API routes, fetch calls, table definitions
    important = []
    for i, line in enumerate(lines[max_lines:], start=max_lines):
        stripped = line.strip()
        if any(kw in stripped for kw in [
            "app.get(", "app.post(", "app.put(", "app.delete(",
            "router.", "fetch(", "CREATE TABLE", "export ", "import ",
            "module.exports",
        ]):
            important.append(line)
        if len(important) > 30:
            break

    result = "\n".join(head)
    if important:
        result += "\n\n// ... key definitions ...\n" + "\n".join(important)
    if len(lines) > max_lines:
        result += f"\n\n// ... ({len(lines) - max_lines} more lines)"
    return result


async def integration_review(build_id: str, manifest: dict, all_files: dict[str, str]) -> dict[str, str]:
    """Review files for cross-file consistency using INTERFACES only (fast).

    Only sends the first ~50 lines of each file + key definitions like routes,
    fetch calls, and table schemas. Fixes are applied per-file.
    """
    _update_build(build_id, status="reviewing")
    _add_step(build_id, "Running quick integration review (interfaces only)...")

    # Build slim context — interfaces only, not full file content
    interface_sections = []
    for path, content in all_files.items():
        # Skip deployment files — they don't have integration issues
        if path in ("Dockerfile", "docker-compose.yml", "package.json", "README.md", ".env.example", ".gitignore"):
            continue
        interface = _extract_interface(content)
        interface_sections.append(f"--- FILE: {path} ---\n{interface}\n--- END FILE ---")

    interfaces_str = "\n\n".join(interface_sections)
    total_chars = len(interfaces_str)
    _add_step(build_id, f"Reviewing {len(interface_sections)} file interfaces ({total_chars} chars context)")

    # Slim manifest
    slim_manifest = {
        "app_name": manifest.get("app_name"),
        "tech_stack": manifest.get("tech_stack"),
        "features": manifest.get("features"),
        "files": [{"path": f["path"], "purpose": f["purpose"]} for f in manifest.get("files", [])],
    }

    user_content = (
        f"PROJECT:\n{json.dumps(slim_manifest, indent=2)}\n\n"
        f"FILE INTERFACES (first ~50 lines + key definitions of each file):\n{interfaces_str}\n\n"
        f"Check for API route mismatches, import/export mismatches, and DB schema mismatches. "
        f"Only flag REAL bugs. For each fix, output the COMPLETE corrected file."
    )

    try:
        result = await asyncio.wait_for(
            chat_with_reasoning(
                messages=[
                    {"role": "system", "content": INTEGRATION_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.2,
                max_tokens=8192,
                model=settings.GLM_FAST_MODEL,
                fallback_model=settings.GLM_FALLBACK_MODEL,
            ),
            timeout=STEP_TIMEOUT,
        )

        review_text = result["content"].strip()
        reasoning = result["reasoning"]

        if reasoning:
            _add_reasoning(build_id, "integration_review", reasoning)
            _add_step(build_id, f"[thinking] Reviewed cross-file integration ({len(reasoning)} chars)")

        if review_text.startswith("```"):
            review_text = review_text.split("\n", 1)[1].rsplit("```", 1)[0]
        review = json.loads(review_text)

        issues_found = review.get("issues_found", 0)
        fixes = review.get("fixes", [])

        if issues_found > 0 and fixes:
            _add_step(build_id, f"Found {issues_found} integration issue(s) — applying fixes...")
            for fix in fixes:
                file_path = fix.get("file", "")
                fixed_content = fix.get("fixed_content", "")
                issue_desc = fix.get("issue", "unknown issue")
                if file_path and fixed_content and file_path in all_files:
                    all_files[file_path] = fixed_content
                    _add_step(build_id, f"Fixed: {issue_desc} in {file_path}")
                    _publish_event(build_id, "file_generated", {
                        "file_path": file_path,
                        "file_count": len(all_files),
                        "total_files": len(all_files),
                        "chars": len(fixed_content),
                    })
            _update_build(build_id, generated_files=json.dumps(all_files))
        else:
            _add_step(build_id, "Integration review passed — no issues found")

    except asyncio.TimeoutError:
        logger.warning("Integration review timed out (non-fatal)")
        _add_step(build_id, "Integration review timed out — skipping (app still works)")
    except Exception as e:
        logger.warning("Integration review failed (non-fatal): %s", e)
        _add_step(build_id, f"Integration review skipped: {str(e)[:100]}")

    return all_files


async def generate_seed_data(
    build_id: str,
    manifest: dict,
    all_files: dict[str, str],
) -> str | None:
    """Generate an init-data.js script that seeds the database with realistic sample data."""
    # Extract the db.js content from generated files
    db_content = all_files.get("backend/db.js", "")
    if not db_content:
        logger.warning("No backend/db.js found — skipping seed data generation")
        return None

    user_content = (
        f"PROJECT MANIFEST:\n{json.dumps(manifest, indent=2)}\n\n"
        f"DATABASE SCHEMA FILE (backend/db.js):\n{db_content}"
    )

    try:
        result = await chat_with_reasoning(
            messages=[
                {"role": "system", "content": SEED_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.6,
            max_tokens=16384,
            retries=2,
        )

        seed_script = result["content"].strip()
        reasoning = result["reasoning"]

        if reasoning:
            _add_reasoning(build_id, "seed_data", reasoning)

        # Strip markdown fences if present
        if seed_script.startswith("```"):
            first_newline = seed_script.index("\n") if "\n" in seed_script else 3
            seed_script = seed_script[first_newline + 1:]
        if seed_script.endswith("```"):
            seed_script = seed_script[:-3].strip()

        if not seed_script:
            logger.warning("Seed data generation returned empty content")
            return None

        return seed_script

    except Exception as e:
        logger.warning("Seed data generation failed (non-fatal): %s", e)
        return None


def generate_deployment_files(manifest: dict, all_files: dict[str, str]) -> dict[str, str]:
    """Generate Dockerfile, docker-compose.yml, package.json, and README from templates."""
    app_name = manifest.get("app_name", "my-app").lower().replace(" ", "-")
    description = manifest.get("description", "A web application built with Builddy")
    features = manifest.get("features", [])
    features_list = "\n".join(f"- {f}" for f in features) if features else "- Full-stack web application"
    port = "3000"

    deployment_files = {
        "Dockerfile": DOCKERFILE_TEMPLATE.format(port=port).strip(),
        "docker-compose.yml": DOCKER_COMPOSE_TEMPLATE.format(port=port).strip(),
        "package.json": PACKAGE_JSON_TEMPLATE.format(
            app_name=app_name,
            description=description,
        ).strip(),
        "README.md": README_TEMPLATE.format(
            app_name=manifest.get("app_name", "My App"),
            description=description,
            port=port,
            features_list=features_list,
        ).strip(),
        ".env.example": f"PORT={port}\nNODE_ENV=development\n",
    }

    # Add .gitignore
    deployment_files[".gitignore"] = "node_modules/\ndata/*.db\n.env\n"

    return {**all_files, **deployment_files}


async def analyze_impact(build_id: str, modification: str, manifest: dict, existing_files: dict[str, str]) -> dict:
    """Analyze which files need to be created/modified/unchanged for a modification."""
    _add_step(build_id, "Analyzing modification impact...")

    # Build file listing for context
    file_sections = []
    for path, content in existing_files.items():
        file_sections.append(f"--- FILE: {path} ---\n{content}\n--- END FILE ---")
    all_files_str = "\n\n".join(file_sections)

    user_content = (
        f"MODIFICATION REQUEST: {modification}\n\n"
        f"PROJECT MANIFEST:\n{json.dumps(manifest, indent=2)}\n\n"
        f"ALL EXISTING FILES:\n{all_files_str}"
    )

    try:
        result = await chat_with_reasoning(
            messages=[
                {"role": "system", "content": IMPACT_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=8192,
        )
        impact_text = result["content"].strip()
        reasoning = result["reasoning"]

        if reasoning:
            _add_reasoning(build_id, "impact_analysis", reasoning)
            _add_step(build_id, f"[thinking] GLM analyzed modification impact ({len(reasoning)} chars)")
    except Exception as e:
        logger.warning("Impact analysis with reasoning failed, falling back: %s", e)
        impact_text = await chat(
            messages=[
                {"role": "system", "content": IMPACT_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=8192,
            thinking=False,
        )

    try:
        text = impact_text.strip() if isinstance(impact_text, str) else impact_text
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        impact = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        raise ValueError("GLM returned invalid impact analysis JSON")

    create_count = len(impact.get("files_to_create", []))
    modify_count = len(impact.get("files_to_modify", []))
    unchanged_count = len(impact.get("files_unchanged", []))
    _add_step(
        build_id,
        f"Impact: {create_count} new, {modify_count} modified, {unchanged_count} unchanged"
    )
    return impact


async def modify_existing_file(
    build_id: str,
    modification: str,
    file_path: str,
    change_spec: dict,
    original_content: str,
    manifest: dict,
    context_files: dict[str, str],
    file_index: int,
    total_files: int,
) -> str:
    """Modify a single existing file based on the impact analysis."""
    _add_step(build_id, f"Modifying file {file_index + 1}/{total_files}: {file_path}")

    # Build context from newly created/modified files
    context_parts = []
    for ctx_path, ctx_content in context_files.items():
        context_parts.append(f"--- FILE: {ctx_path} ---\n{ctx_content}\n--- END FILE ---")
    context_str = "\n\n".join(context_parts) if context_parts else "(No other files changed yet)"

    user_content = (
        f"USER'S MODIFICATION REQUEST: {modification}\n\n"
        f"CHANGES NEEDED FOR THIS FILE: {change_spec.get('changes', '')}\n"
        f"REASON: {change_spec.get('reason', '')}\n\n"
        f"ORIGINAL FILE ({file_path}):\n{original_content}\n\n"
        f"PROJECT MANIFEST:\n{json.dumps(manifest, indent=2)}\n\n"
        f"OTHER RECENTLY CHANGED FILES:\n{context_str}"
    )

    result = await chat_with_reasoning(
        messages=[
            {"role": "system", "content": MODIFY_FILE_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        temperature=0.4,
        max_tokens=16384,
        retries=2,
    )

    code = result["content"].strip()
    reasoning = result["reasoning"]

    # Strip markdown fences if present
    if code.startswith("```"):
        first_newline = code.index("\n") if "\n" in code else 3
        code = code[first_newline + 1:]
    if code.endswith("```"):
        code = code[:-3].strip()

    if reasoning:
        _add_reasoning(build_id, f"modifying_{file_path}", reasoning)

    if not code:
        _add_step(build_id, f"Modification returned empty for {file_path} — keeping original")
        return original_content

    _add_step(build_id, f"Modified {file_path} ({len(code)} chars)")
    return code
