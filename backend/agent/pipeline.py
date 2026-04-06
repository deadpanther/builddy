"""Builddy Agent Pipeline — powered by GLM 5.1 with thinking mode, vision, and image generation."""

import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlmodel import Session
from agent.llm import chat, chat_with_reasoning, vision_chat, generate_image
from agent.prompts import (
    PARSE_SYSTEM, PLAN_SYSTEM, CODE_SYSTEM, REVIEW_SYSTEM,
    MODIFY_SYSTEM, SCREENSHOT_SYSTEM, IMAGE_PROMPT_TEMPLATE,
    CLASSIFY_SYSTEM, MANIFEST_SYSTEM, FILEGEN_SYSTEM, INTEGRATION_SYSTEM,
    DOCKERFILE_TEMPLATE, DOCKER_COMPOSE_TEMPLATE, PACKAGE_JSON_TEMPLATE,
    README_TEMPLATE, IMPACT_SYSTEM, MODIFY_FILE_SYSTEM, SEED_SYSTEM,
)
from services.deployer import deploy_html, deploy_project, create_project_zip
from database import engine
from models import Build
from config import settings

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _update_build(build_id: str, **kwargs):
    with Session(engine) as session:
        build = session.get(Build, build_id)
        if build:
            for k, v in kwargs.items():
                setattr(build, k, v)
            build.updated_at = datetime.now(timezone.utc)
            session.add(build)
            session.commit()


def _add_step(build_id: str, step: str):
    with Session(engine) as session:
        build = session.get(Build, build_id)
        if build:
            existing = json.loads(build.steps) if build.steps else []
            existing.append(step)
            build.steps = json.dumps(existing)
            build.updated_at = datetime.now(timezone.utc)
            session.add(build)
            session.commit()


def _add_reasoning(build_id: str, stage: str, reasoning: str):
    """Append reasoning from thinking mode to the build's reasoning log."""
    if not reasoning:
        return
    with Session(engine) as session:
        build = session.get(Build, build_id)
        if build:
            existing = json.loads(build.reasoning_log) if build.reasoning_log else []
            existing.append({"stage": stage, "reasoning": reasoning[:2000]})
            build.reasoning_log = json.dumps(existing)
            session.add(build)
            session.commit()


def _strip_fences(text: str) -> str:
    """Extract code from markdown fences, ignoring any preamble text before them."""
    text = text.strip()

    # Find the opening fence (may have preamble text before it)
    html_fence = text.find("```html")
    generic_fence = text.find("```")

    if html_fence != -1:
        # Extract content after ```html\n ... up to closing ```
        start = html_fence + 7  # len("```html")
        # Skip the newline after ```html if present
        if start < len(text) and text[start] == "\n":
            start += 1
        closing = text.rfind("```", start)
        if closing != -1:
            return text[start:closing].strip()
        return text[start:].strip()

    if generic_fence != -1:
        start = generic_fence + 3
        if start < len(text) and text[start] == "\n":
            start += 1
        closing = text.rfind("```", start)
        if closing != -1:
            return text[start:closing].strip()
        return text[start:].strip()

    return text


# ── Pipeline Steps ───────────────────────────────────────────────────────────

async def parse_request(build_id: str, tweet_text: str) -> dict:
    """Step 1: Parse the request into a structured app request."""
    _update_build(build_id, status="planning")
    _add_step(build_id, "Parsing request with GLM 5.1...")

    result = await chat(
        messages=[
            {"role": "system", "content": PARSE_SYSTEM},
            {"role": "user", "content": f"Parse this request:\n\n{tweet_text}"},
        ],
        temperature=0.3,
    )

    try:
        text = result.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        parsed = {
            "prompt": tweet_text.replace("@builddy", "").strip(),
            "app_type": "other",
            "app_name": "my-app",
        }

    _update_build(
        build_id,
        prompt=parsed.get("prompt", tweet_text),
        app_name=parsed.get("app_name", "my-app"),
        app_description=parsed.get("prompt", ""),
    )
    _add_step(build_id, f"Parsed: {parsed.get('app_name', 'app')} ({parsed.get('app_type', 'other')})")
    return parsed


async def plan_app(build_id: str, prompt: str) -> str:
    """Step 2: Plan the app architecture (with optional web search)."""
    _add_step(build_id, "Planning architecture with GLM 5.1 thinking mode...")

    # Build tools list — include web search if enabled
    tools = None
    if settings.ENABLE_WEB_SEARCH:
        tools = [
            {
                "type": "web_search",
                "web_search": {
                    "enable": "True",
                    "search_engine": "search-prime",
                    "search_result": "True",
                    "count": "3",
                    "search_recency_filter": "noLimit",
                },
            }
        ]

    try:
        result = await chat_with_reasoning(
            messages=[
                {"role": "system", "content": PLAN_SYSTEM},
                {"role": "user", "content": f"Plan this app:\n\n{prompt}"},
            ],
            temperature=0.5,
            tools=tools,
        )

        plan = result["content"]
        reasoning = result["reasoning"]

        if reasoning:
            _add_reasoning(build_id, "planning", reasoning)
            _add_step(build_id, f"[thinking] GLM reasoned through the architecture ({len(reasoning)} chars)")

        if tools:
            _add_step(build_id, "[research] GLM searched the web for relevant patterns")

    except Exception as e:
        logger.warning("Planning with reasoning/search failed, falling back: %s", e)
        plan = await chat(
            messages=[
                {"role": "system", "content": PLAN_SYSTEM},
                {"role": "user", "content": f"Plan this app:\n\n{prompt}"},
            ],
            temperature=0.5,
            thinking=False,
        )

    _add_step(build_id, f"Plan created ({len(plan)} chars)")
    return plan


async def generate_code(build_id: str, prompt: str, plan: str) -> str:
    """Step 3: Generate the complete HTML/CSS/JS code with thinking mode."""
    _update_build(build_id, status="coding")
    _add_step(build_id, "Generating code with GLM 5.1...")

    result = await chat_with_reasoning(
        messages=[
            {"role": "user", "content": f"Generate a complete single-file HTML app (with inline CSS and JS, no external dependencies) for: {prompt}\n\nWrap your code in ```html fences."},
        ],
        temperature=0.7,
        max_tokens=16384,
        retries=2,
    )

    code = _strip_fences(result["content"])
    reasoning = result["reasoning"]

    if reasoning:
        _add_reasoning(build_id, "coding", reasoning)
        _add_step(build_id, f"[thinking] GLM reasoned through implementation ({len(reasoning)} chars)")

    if not code:
        # Fallback: try with thinking explicitly disabled
        _add_step(build_id, "Retrying code generation (thinking disabled)...")
        code_text = await chat(
            messages=[
                {"role": "user", "content": f"Generate a complete single-file HTML app (with inline CSS and JS, no external dependencies) for: {prompt}\n\nWrap your code in ```html fences."},
            ],
            temperature=0.7,
            max_tokens=16384,
            retries=2,
            thinking=False,
        )
        code = _strip_fences(code_text)

    if not code:
        raise ValueError("GLM returned empty code after retries — cannot proceed")

    _update_build(build_id, generated_code=code)
    _add_step(build_id, f"Code generated ({len(code)} chars)")
    return code


async def review_code(build_id: str, code: str) -> str:
    """Step 4: Self-review and fix any issues."""
    _update_build(build_id, status="reviewing")
    _add_step(build_id, "Reviewing code with GLM 5.1...")

    result = await chat_with_reasoning(
        messages=[
            {"role": "system", "content": REVIEW_SYSTEM},
            {"role": "user", "content": f"Review and fix this code:\n\n{code}"},
        ],
        temperature=0.2,
        max_tokens=16384,
    )

    reviewed = _strip_fences(result["content"])
    reasoning = result["reasoning"]

    if reasoning:
        _add_reasoning(build_id, "reviewing", reasoning)
        _add_step(build_id, f"[thinking] GLM reviewed code quality ({len(reasoning)} chars)")

    if not reviewed:
        _add_step(build_id, "Review returned empty — keeping original code")
        return code

    _update_build(build_id, generated_code=reviewed)
    _add_step(build_id, "Code review complete — issues fixed")
    return reviewed


async def generate_thumbnail(build_id: str, app_description: str):
    """Generate an app thumbnail using CogView-4."""
    if not settings.ENABLE_IMAGE_GEN:
        return

    _add_step(build_id, "Generating app thumbnail with CogView-4...")

    prompt = IMAGE_PROMPT_TEMPLATE.format(description=app_description[:200])
    url = await generate_image(prompt, size="1024x1024")

    if url:
        _update_build(build_id, thumbnail_url=url)
        _add_step(build_id, f"[image] Thumbnail generated with CogView-4")
    else:
        _add_step(build_id, "Thumbnail generation skipped")


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

    # Build context from previously generated files
    context_parts = []
    for prev_path, prev_content in generated_so_far.items():
        context_parts.append(f"--- FILE: {prev_path} ---\n{prev_content}\n--- END FILE ---")
    context_str = "\n\n".join(context_parts) if context_parts else "(No files generated yet)"

    user_content = (
        f"Generate the file: {file_path}\n\n"
        f"PURPOSE: {file_entry.get('purpose', 'See manifest')}\n\n"
        f"FULL PROJECT MANIFEST:\n{json.dumps(manifest, indent=2)}\n\n"
        f"PREVIOUSLY GENERATED FILES:\n{context_str}"
    )

    result = await chat_with_reasoning(
        messages=[
            {"role": "system", "content": FILEGEN_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        temperature=0.5,
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
        _add_reasoning(build_id, f"generating_{file_path}", reasoning)

    if not code:
        # Fallback with thinking explicitly disabled
        _add_step(build_id, f"Retrying {file_path} (thinking disabled)...")
        code = await chat(
            messages=[
                {"role": "system", "content": FILEGEN_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.5,
            max_tokens=16384,
            thinking=False,
            retries=1,
        )
        code = _strip_fences(code)

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

    _add_step(build_id, f"All {total} files generated ({sum(len(v) for v in generated.values())} total chars)")
    return generated


async def integration_review(build_id: str, manifest: dict, all_files: dict[str, str]) -> dict[str, str]:
    """Review all files together for cross-file consistency issues."""
    _update_build(build_id, status="reviewing")
    _add_step(build_id, "Running integration review across all files...")

    # Build full file listing for context
    file_sections = []
    for path, content in all_files.items():
        file_sections.append(f"--- FILE: {path} ---\n{content}\n--- END FILE ---")
    all_files_str = "\n\n".join(file_sections)

    user_content = (
        f"PROJECT MANIFEST:\n{json.dumps(manifest, indent=2)}\n\n"
        f"ALL GENERATED FILES:\n{all_files_str}"
    )

    try:
        result = await chat_with_reasoning(
            messages=[
                {"role": "system", "content": INTEGRATION_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=16384,
        )

        review_text = result["content"].strip()
        reasoning = result["reasoning"]

        if reasoning:
            _add_reasoning(build_id, "integration_review", reasoning)
            _add_step(build_id, f"[thinking] GLM reviewed cross-file integration ({len(reasoning)} chars)")

        # Parse the review result
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
            # Update DB with fixed files
            _update_build(build_id, generated_files=json.dumps(all_files))
        else:
            _add_step(build_id, "Integration review passed — no issues found")

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


# ── Full Pipelines ───────────────────────────────────────────────────────────

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


async def run_modify_fullstack_pipeline(
    build_id: str,
    modification: str,
    existing_files: dict[str, str],
    manifest: dict,
):
    """Run the iterative modification pipeline for multi-file projects."""
    try:
        _update_build(build_id, status="planning")

        # Step 1: Impact analysis
        impact = await analyze_impact(build_id, modification, manifest, existing_files)

        _update_build(build_id, status="coding")

        # Start with a copy of all existing files
        updated_files = dict(existing_files)
        context_files: dict[str, str] = {}

        files_to_create = impact.get("files_to_create", [])
        files_to_modify = impact.get("files_to_modify", [])
        total_changes = len(files_to_create) + len(files_to_modify)

        if total_changes == 0:
            _add_step(build_id, "No file changes needed — redeploying as-is")
        else:
            _add_step(build_id, f"Applying {total_changes} file changes...")

            # Step 2a: Generate new files
            for i, file_spec in enumerate(files_to_create):
                file_path = file_spec["path"]
                _add_step(build_id, f"Creating new file {i + 1}/{len(files_to_create)}: {file_path}")

                # Use FILEGEN_SYSTEM for new files (same as initial generation)
                file_entry = {
                    "path": file_path,
                    "purpose": file_spec.get("purpose", ""),
                    "dependencies": file_spec.get("depends_on", []),
                }
                # Provide both existing unchanged files and already-modified files as context
                gen_context = {**updated_files, **context_files}
                code = await generate_file(
                    build_id, manifest, file_entry, gen_context, i, len(files_to_create)
                )
                updated_files[file_path] = code
                context_files[file_path] = code

            # Step 2b: Modify existing files
            for i, change_spec in enumerate(files_to_modify):
                file_path = change_spec["path"]
                original = existing_files.get(file_path, "")
                if not original:
                    _add_step(build_id, f"Warning: {file_path} not found in existing files, skipping")
                    continue

                modified = await modify_existing_file(
                    build_id, modification, file_path, change_spec,
                    original, manifest, context_files,
                    i, len(files_to_modify),
                )
                updated_files[file_path] = modified
                context_files[file_path] = modified

        # Step 3: Integration review (only if changes were made)
        if total_changes > 0:
            updated_files = await integration_review(build_id, manifest, updated_files)

        # Step 3.5: Regenerate seed data if database schema changed
        manifest_updates = impact.get("manifest_updates", {})
        db_modified = any(
            spec.get("path") == "backend/db.js" for spec in files_to_modify
        )
        new_tables = manifest_updates.get("new_tables", [])
        if db_modified or new_tables:
            _add_step(build_id, "Database schema changed — regenerating seed data...")
            seed_script = await generate_seed_data(build_id, manifest, updated_files)
            if seed_script:
                updated_files["init-data.js"] = seed_script
                _add_step(build_id, f"Seed data script regenerated ({len(seed_script)} chars)")

        # Step 4: Regenerate deployment files with updated manifest
        _add_step(build_id, "Updating deployment files...")
        new_features = manifest_updates.get("new_features", [])
        if new_features:
            existing_features = manifest.get("features", [])
            manifest = {**manifest, "features": existing_features + new_features}

        updated_files = generate_deployment_files(manifest, updated_files)

        # Step 5: Deploy
        _update_build(build_id, status="deploying", generated_files=json.dumps(updated_files))
        _add_step(build_id, "Deploying modified project...")
        deploy_url = deploy_project(build_id, updated_files)

        # Step 6: Create zip
        _add_step(build_id, "Creating downloadable project zip...")
        zip_url = create_project_zip(build_id, updated_files)

        main_html = updated_files.get("frontend/index.html", "")
        _update_build(
            build_id,
            status="deployed",
            deploy_url=deploy_url,
            zip_url=zip_url,
            generated_code=main_html,
            generated_files=json.dumps(updated_files),
            file_manifest=json.dumps(manifest),
            deployed_at=datetime.now(timezone.utc),
        )
        _add_step(build_id, f"Deployed at {deploy_url}")
        _add_step(build_id, f"Download zip: {zip_url}")

        # Thumbnail
        asyncio.create_task(_safe_thumbnail(build_id, modification))

        logger.info("Fullstack modification %s completed: %s", build_id, deploy_url)

    except Exception as e:
        with Session(engine) as session:
            build = session.get(Build, build_id)
            failed_at = build.status if build else "unknown"
        logger.exception("Fullstack modify %s failed at [%s]: %s", build_id, failed_at, str(e))
        _update_build(build_id, status="failed", error=f"[{failed_at}] {str(e)}")
        _add_step(build_id, f"Modification failed: {str(e)}")


async def run_fullstack_pipeline(build_id: str, prompt: str, classification: dict):
    """Run the full multi-file generation pipeline for standard/fullstack apps."""
    # Step 1: Plan manifest
    manifest = await plan_manifest(build_id, prompt, classification)

    # Step 2: Generate all files
    all_files = await generate_all_files(build_id, manifest)

    # Step 3: Integration review
    all_files = await integration_review(build_id, manifest, all_files)

    # Step 3.5: Generate seed data
    _add_step(build_id, "Generating realistic sample data...")
    seed_script = await generate_seed_data(build_id, manifest, all_files)
    if seed_script:
        all_files["init-data.js"] = seed_script
        _add_step(build_id, f"Seed data script generated ({len(seed_script)} chars)")

    # Step 4: Add deployment files (Dockerfile, package.json, etc.)
    _add_step(build_id, "Generating deployment files (Dockerfile, package.json, README)...")
    all_files = generate_deployment_files(manifest, all_files)
    _update_build(build_id, generated_files=json.dumps(all_files))
    _add_step(build_id, f"Project complete: {len(all_files)} total files")

    # Step 5: Deploy project files
    _update_build(build_id, status="deploying")
    _add_step(build_id, "Deploying project...")
    deploy_url = deploy_project(build_id, all_files)

    # Step 6: Create downloadable zip
    _add_step(build_id, "Creating downloadable project zip...")
    zip_url = create_project_zip(build_id, all_files)

    # Also store the main index.html as generated_code for backward compat
    main_html = all_files.get("frontend/index.html", "")
    _update_build(
        build_id,
        status="deployed",
        deploy_url=deploy_url,
        zip_url=zip_url,
        generated_code=main_html,
        deployed_at=datetime.now(timezone.utc),
    )
    _add_step(build_id, f"Deployed at {deploy_url}")
    _add_step(build_id, f"Download zip: {zip_url}")

    return deploy_url

async def run_retry_pipeline(build_id: str, failed_at: str = "unknown"):
    """Retry a failed build from the point of failure, reusing saved intermediate state.

    The caller (retry endpoint) must pass *failed_at* because the error field
    is cleared before this coroutine runs.
    """
    try:
        with Session(engine) as session:
            build = session.get(Build, build_id)
            if not build:
                logger.error("Build %s not found for retry", build_id)
                return

            prompt = build.prompt or build.tweet_text or ""
            complexity = build.complexity or "simple"

        _add_step(build_id, f"Retrying build from '{failed_at}' stage...")

        if complexity in ("standard", "fullstack"):
            await _retry_fullstack(build_id, prompt, failed_at)
        else:
            await _retry_simple(build_id, prompt, failed_at)

        # Generate thumbnail (non-blocking)
        asyncio.create_task(_safe_thumbnail(build_id, prompt))
        logger.info("Retry of build %s completed", build_id)

    except Exception as e:
        with Session(engine) as session:
            build = session.get(Build, build_id)
            current_status = build.status if build else "unknown"
        logger.exception("Retry of build %s failed at [%s]: %s", build_id, current_status, str(e))
        _update_build(build_id, status="failed", error=f"[{current_status}] {str(e)}")
        _add_step(build_id, f"Retry failed at {current_status}: {str(e)}")


async def _retry_simple(build_id: str, prompt: str, failed_at: str):
    """Retry a simple (single-file) build from point of failure."""
    with Session(engine) as session:
        build = session.get(Build, build_id)
        existing_code = build.generated_code if build else None

    if failed_at in ("pending", "planning"):
        # Need to redo everything from planning
        plan = await plan_app(build_id, prompt)
        code = await generate_code(build_id, prompt, plan)
        code = await review_code(build_id, code)
    elif failed_at == "coding":
        # Planning done, redo coding
        plan = ""  # plan was already used, re-plan briefly
        plan = await plan_app(build_id, prompt)
        code = await generate_code(build_id, prompt, plan)
        code = await review_code(build_id, code)
    elif failed_at == "reviewing":
        # Code exists, just redo review
        if existing_code:
            _add_step(build_id, "Resuming from review stage (code already generated)")
            code = await review_code(build_id, existing_code)
        else:
            plan = await plan_app(build_id, prompt)
            code = await generate_code(build_id, prompt, plan)
            code = await review_code(build_id, code)
    elif failed_at == "deploying":
        # Code exists and was reviewed, just deploy
        if existing_code:
            _add_step(build_id, "Resuming from deploy stage (code ready)")
            code = existing_code
        else:
            plan = await plan_app(build_id, prompt)
            code = await generate_code(build_id, prompt, plan)
            code = await review_code(build_id, code)
    else:
        # Unknown stage, restart from scratch
        plan = await plan_app(build_id, prompt)
        code = await generate_code(build_id, prompt, plan)
        code = await review_code(build_id, code)

    # Deploy
    _update_build(build_id, status="deploying")
    _add_step(build_id, "Deploying app...")
    deploy_url = deploy_html(build_id, code)
    _update_build(
        build_id,
        status="deployed",
        deploy_url=deploy_url,
        deployed_at=datetime.now(timezone.utc),
    )
    _add_step(build_id, f"Deployed at {deploy_url}")


async def _retry_fullstack(build_id: str, prompt: str, failed_at: str):
    """Retry a fullstack build from point of failure, reusing saved state."""
    with Session(engine) as session:
        build = session.get(Build, build_id)
        if not build:
            raise ValueError("Build not found")
        saved_manifest = json.loads(build.file_manifest) if build.file_manifest else None
        saved_files = json.loads(build.generated_files) if build.generated_files else None
        saved_complexity = build.complexity or "standard"

    # Determine what we can skip based on saved state
    has_manifest = saved_manifest is not None and len(saved_manifest.get("files", [])) > 0
    has_files = saved_files is not None and len(saved_files) > 0

    # Step 1: Plan manifest (skip if already saved)
    if has_manifest:
        manifest = saved_manifest
        _add_step(build_id, f"Reusing saved manifest ({len(manifest.get('files', []))} files)")
    else:
        classification = {
            "complexity": saved_complexity,
            "app_name": build.app_name or "app",
            "needs_backend": True,
            "needs_database": True,
            "needs_auth": saved_complexity == "fullstack",
        }
        manifest = await plan_manifest(build_id, prompt, classification)

    # Step 2: Generate files (skip already-generated ones)
    if failed_at in ("coding",) or (has_files and failed_at in ("reviewing", "deploying")):
        # Some or all files exist — pass them in to skip re-generation
        manifest_paths = {f["path"] for f in manifest.get("files", [])}
        if has_files and all(p in saved_files for p in manifest_paths):
            all_files = saved_files
            _add_step(build_id, f"Reusing all {len(all_files)} generated files")
        else:
            all_files = await generate_all_files(build_id, manifest, saved_files)
    else:
        all_files = await generate_all_files(build_id, manifest, saved_files)

    # Step 3: Integration review (always re-run unless we're past it)
    if failed_at not in ("deploying",):
        all_files = await integration_review(build_id, manifest, all_files)
    else:
        _add_step(build_id, "Skipping integration review (already passed)")

    # Step 3.5: Generate seed data (if not already present)
    if "init-data.js" not in all_files:
        _add_step(build_id, "Generating realistic sample data...")
        seed_script = await generate_seed_data(build_id, manifest, all_files)
        if seed_script:
            all_files["init-data.js"] = seed_script
            _add_step(build_id, f"Seed data script generated ({len(seed_script)} chars)")

    # Step 4: Deployment files
    _add_step(build_id, "Generating deployment files (Dockerfile, package.json, README)...")
    all_files = generate_deployment_files(manifest, all_files)
    _update_build(build_id, generated_files=json.dumps(all_files))
    _add_step(build_id, f"Project complete: {len(all_files)} total files")

    # Step 5: Deploy
    _update_build(build_id, status="deploying")
    _add_step(build_id, "Deploying project...")
    deploy_url = deploy_project(build_id, all_files)

    # Step 6: Zip
    _add_step(build_id, "Creating downloadable project zip...")
    zip_url = create_project_zip(build_id, all_files)

    main_html = all_files.get("frontend/index.html", "")
    _update_build(
        build_id,
        status="deployed",
        deploy_url=deploy_url,
        zip_url=zip_url,
        generated_code=main_html,
        deployed_at=datetime.now(timezone.utc),
    )
    _add_step(build_id, f"Deployed at {deploy_url}")
    _add_step(build_id, f"Download zip: {zip_url}")


async def run_pipeline(build_id: str):
    """Run the full text-to-app agent pipeline. Routes to simple or fullstack pipeline based on complexity."""
    try:
        with Session(engine) as session:
            build = session.get(Build, build_id)
            if not build:
                logger.error("Build %s not found", build_id)
                return
            tweet_text = build.tweet_text or build.prompt or "Build a simple hello world app"

        # Step 1: Parse
        parsed = await parse_request(build_id, tweet_text)
        prompt = parsed.get("prompt", tweet_text)

        # Step 2: Classify complexity
        classification = await classify_complexity(build_id, prompt)
        complexity = classification.get("complexity", "simple")

        if complexity in ("standard", "fullstack"):
            # ── Multi-file pipeline ──
            logger.info("Build %s using %s pipeline", build_id, complexity)
            deploy_url = await run_fullstack_pipeline(build_id, prompt, classification)

            # Generate thumbnail (non-blocking)
            app_desc = prompt
            asyncio.create_task(_safe_thumbnail(build_id, app_desc))
            logger.info("Build %s completed (fullstack): %s", build_id, deploy_url)
        else:
            # ── Simple single-file pipeline (existing behavior) ──
            logger.info("Build %s using simple pipeline", build_id)

            # Plan (with web search + thinking)
            plan = await plan_app(build_id, prompt)

            # Generate code (with thinking)
            code = await generate_code(build_id, prompt, plan)

            # Review (with thinking)
            code = await review_code(build_id, code)

            # Deploy
            _update_build(build_id, status="deploying")
            _add_step(build_id, "Deploying app...")
            deploy_url = deploy_html(build_id, code)

            _update_build(
                build_id,
                status="deployed",
                deploy_url=deploy_url,
                deployed_at=datetime.now(timezone.utc),
            )
            _add_step(build_id, f"Deployed at {deploy_url}")

            # Generate thumbnail (non-blocking)
            app_desc = prompt
            asyncio.create_task(_safe_thumbnail(build_id, app_desc))
            logger.info("Build %s completed (simple): %s", build_id, deploy_url)

    except Exception as e:
        with Session(engine) as session:
            build = session.get(Build, build_id)
            failed_at = build.status if build else "unknown"
        logger.exception("Build %s failed at [%s]: %s", build_id, failed_at, str(e))
        _update_build(build_id, status="failed", error=f"[{failed_at}] {str(e)}")
        _add_step(build_id, f"Build failed at {failed_at}: {str(e)}")


async def run_screenshot_pipeline(build_id: str, images_base64: list[str], text_prompt: str = ""):
    """Run the screenshot-to-app pipeline using GLM-5V-Turbo."""
    try:
        _update_build(build_id, status="planning", build_type="screenshot")
        img_count = len(images_base64)
        _add_step(build_id, f"Analyzing {img_count} screenshot(s) with GLM-5V-Turbo...")

        # Step 1: Vision model converts screenshot(s) to code
        full_prompt = SCREENSHOT_SYSTEM
        if text_prompt:
            full_prompt += f"\n\nIMPORTANT — the user described this app as: {text_prompt}"
            full_prompt += "\nUse this description as the app's title, purpose, and guide for all functionality."
        if img_count > 1:
            full_prompt += f"\n\nThe user uploaded {img_count} screenshots showing different screens/states of the app. Implement ALL screens and wire navigation between them."
        full_prompt += "\n\nConvert the screenshot(s) into a COMPLETE, FULLY INTERACTIVE, working single-file HTML application. Every button, link, input, toggle, and interactive element MUST work. Wrap your code in ```html fences."

        result = await vision_chat(
            images_base64=images_base64,
            text_prompt=full_prompt,
            temperature=0.5,
            max_tokens=16384,
            retries=2,
        )

        code = _strip_fences(result["content"])
        reasoning = result["reasoning"]

        if reasoning:
            _add_reasoning(build_id, "vision", reasoning)
            _add_step(build_id, f"[thinking] GLM-5V analyzed the design ({len(reasoning)} chars)")

        if not code:
            raise ValueError("GLM-5V-Turbo returned empty code — cannot proceed")

        _update_build(build_id, status="coding", generated_code=code)
        _add_step(build_id, f"Screenshot converted to code ({len(code)} chars)")

        # Step 2: Review
        code = await review_code(build_id, code)

        # Step 3: Deploy
        _update_build(build_id, status="deploying")
        _add_step(build_id, "Deploying app...")
        deploy_url = deploy_html(build_id, code)

        _update_build(
            build_id,
            status="deployed",
            deploy_url=deploy_url,
            deployed_at=datetime.now(timezone.utc),
        )
        _add_step(build_id, f"Deployed at {deploy_url}")

        # Thumbnail
        desc = text_prompt or "web application from screenshot"
        asyncio.create_task(_safe_thumbnail(build_id, desc))

        logger.info("Screenshot build %s completed: %s", build_id, deploy_url)

    except Exception as e:
        with Session(engine) as session:
            build = session.get(Build, build_id)
            failed_at = build.status if build else "unknown"
        logger.exception("Screenshot build %s failed at [%s]: %s", build_id, failed_at, str(e))
        _update_build(build_id, status="failed", error=f"[{failed_at}] {str(e)}")
        _add_step(build_id, f"Build failed at {failed_at}: {str(e)}")


async def run_modify_pipeline(build_id: str, original_code: str, modification: str):
    """Run a modification pipeline — takes existing code and applies changes."""
    try:
        _update_build(build_id, status="coding")
        _add_step(build_id, f"Modifying: {modification[:100]}...")

        await asyncio.sleep(1)

        result = await chat_with_reasoning(
            messages=[
                {"role": "system", "content": MODIFY_SYSTEM},
                {"role": "user", "content": f"Requested change: {modification}\n\nCurrent code:\n```html\n{original_code}\n```"},
            ],
            temperature=0.5,
            max_tokens=16384,
            retries=2,
        )

        modified = _strip_fences(result["content"])
        reasoning = result["reasoning"]

        if reasoning:
            _add_reasoning(build_id, "modify", reasoning)
            _add_step(build_id, f"[thinking] GLM reasoned through the modification ({len(reasoning)} chars)")

        if not modified:
            # Fallback: simpler prompt with thinking disabled
            _add_step(build_id, "Retrying modification (thinking disabled)...")
            await asyncio.sleep(3)
            modified_text = await chat(
                messages=[
                    {"role": "user", "content": f"Take this HTML app and apply this change: {modification}\n\nOutput the complete modified HTML in ```html fences.\n\nOriginal:\n```html\n{original_code}\n```"},
                ],
                temperature=0.7,
                max_tokens=16384,
                thinking=False,
                retries=1,
            )
            modified = _strip_fences(modified_text)

        if not modified:
            raise ValueError("GLM returned empty modification — cannot proceed")

        _update_build(build_id, generated_code=modified, status="reviewing")
        _add_step(build_id, f"Code modified ({len(modified)} chars)")

        # Deploy directly (skip review for modifications to keep it fast)
        _update_build(build_id, status="deploying")
        _add_step(build_id, "Deploying modified app...")
        deploy_url = deploy_html(build_id, modified)

        _update_build(
            build_id,
            status="deployed",
            deploy_url=deploy_url,
            deployed_at=datetime.now(timezone.utc),
        )
        _add_step(build_id, f"Deployed at {deploy_url}")
        logger.info("Modification %s completed: %s", build_id, deploy_url)

    except Exception as e:
        with Session(engine) as session:
            build = session.get(Build, build_id)
            failed_at = build.status if build else "unknown"
        logger.exception("Modify %s failed at [%s]: %s", build_id, failed_at, str(e))
        _update_build(build_id, status="failed", error=f"[{failed_at}] {str(e)}")
        _add_step(build_id, f"Modification failed: {str(e)}")


async def _safe_thumbnail(build_id: str, description: str):
    """Generate thumbnail without crashing the pipeline if it fails."""
    try:
        await generate_thumbnail(build_id, description)
    except Exception as e:
        logger.warning("Thumbnail generation failed for %s: %s", build_id, e)
