"""Builddy Agent Pipeline — slim orchestrator.

All heavy lifting is delegated to sub-modules:
  agent.helpers   — constants, DB helpers, _strip_fences
  agent.steps     — parse, plan, generate_code, review, thumbnail
  agent.agents    — PRD, design, QA, polish, visual validation
  agent.multifile — classify, manifest, per-file gen, integration review
"""

import asyncio
import json
import logging
from datetime import UTC, datetime

from sqlmodel import Session

from agent.agents import (
    create_design_system,
    polish_pass,
    qa_validate,
    visual_validate,
    write_prd,
)
from agent.autopilot import autopilot_fix_loop
from agent.helpers import _add_step, _strip_fences, _update_build
from agent.llm import chat, chat_with_reasoning, vision_chat
from agent.multifile import (
    analyze_impact,
    classify_complexity,
    generate_all_files,
    generate_deployment_files,
    generate_file,
    generate_seed_data,
    integration_review,
    modify_existing_file,
    plan_manifest,
)
from agent.prompts import CODE_SYSTEM, MODIFY_SYSTEM, QUICK_MODIFY_SYSTEM, SCREENSHOT_SYSTEM
from agent.steps import (
    generate_code,
    generate_thumbnail,
    parse_request,
    plan_app,
    review_code,
)
from agent.test_gen import generate_tests
from config import settings
from database import engine
from models import Build
from services.deployer import create_project_zip, deploy_html, deploy_project, deploy_test_file
from services.post_deploy_hooks import schedule_post_deploy_hooks

logger = logging.getLogger(__name__)


# Re-export _strip_fences so existing `from agent.pipeline import _strip_fences` still works
__all__ = [
    "run_pipeline",
    "run_fullstack_pipeline",
    "run_modify_pipeline",
    "run_screenshot_pipeline",
    "run_retry_pipeline",
    "run_modify_fullstack_pipeline",
    "_strip_fences",
]


# ── Full Pipelines ───────────────────────────────────────────────────────────

async def _safe_thumbnail(build_id: str, description: str):
    """Generate thumbnail without crashing the pipeline if it fails."""
    try:
        await generate_thumbnail(build_id, description)
    except Exception as e:
        logger.warning("Thumbnail generation failed for %s: %s", build_id, e)


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

    # Step 6: Generate test suite (non-blocking)
    app_name = manifest.get("app_name", "App")
    main_html = all_files.get("frontend/index.html", "")

    if settings.ENABLE_AUTO_TEST_GEN:
        async def _generate_and_deploy_fullstack_tests():
            try:
                tests = await generate_tests(
                    main_html,
                    app_name=app_name,
                    complexity=classification.get("complexity", "standard"),
                    manifest=manifest,
                    all_files=all_files,
                )
                for test_path, test_content in tests.items():
                    test_url = deploy_test_file(build_id, test_path, test_content)
                    _add_step(build_id, f"Test file deployed at {test_url}")
            except Exception as e:
                logger.warning("Test generation failed for fullstack build %s: %s", build_id, e)

        asyncio.create_task(_generate_and_deploy_fullstack_tests())
    else:
        logger.info("Test generation skipped for fullstack build %s (disabled)", build_id)

    # Step 7: Create downloadable zip
    _add_step(build_id, "Creating downloadable project zip...")
    zip_url = create_project_zip(build_id, all_files)

    # Also store the main index.html as generated_code for backward compat
    _update_build(
        build_id,
        status="deployed",
        deploy_url=deploy_url,
        zip_url=zip_url,
        generated_code=main_html,
        deployed_at=datetime.now(UTC),
    )
    _add_step(build_id, f"Deployed at {deploy_url}")
    _add_step(build_id, f"Download zip: {zip_url}")
    schedule_post_deploy_hooks(build_id, deploy_url)

    return deploy_url


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
            deployed_at=datetime.now(UTC),
        )
        _add_step(build_id, f"Deployed at {deploy_url}")
        _add_step(build_id, f"Download zip: {zip_url}")
        schedule_post_deploy_hooks(build_id, deploy_url)

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
    """Retry a simple (single-file) build from point of failure.

    Key principle: SKIP steps that already succeeded. Use fast model on retry.
    """
    from agent.helpers import _strip_fences as strip_fences

    with Session(engine) as session:
        build = session.get(Build, build_id)
        existing_code = build.generated_code if build else None

    if failed_at == "deploying" and existing_code:
        # Code ready, just deploy
        _add_step(build_id, "Resuming from deploy (code ready)")
        code = existing_code
    elif failed_at == "reviewing" and existing_code:
        # Code exists, just review
        _add_step(build_id, "Resuming from review (code already generated)")
        code = await review_code(build_id, existing_code)
    elif failed_at in ("coding", "planning", "pending") or not existing_code:
        # Need to generate code — use fast model directly (GLM-5.1 already failed)
        _add_step(build_id, "Retrying code generation with fast model (skipping redundant steps)...")
        _update_build(build_id, status="coding")

        code_text = await chat(
            messages=[
                {"role": "system", "content": CODE_SYSTEM},
                {"role": "user", "content": (
                    f"Build this app: {prompt}\n\n"
                    f"Generate the COMPLETE single-file HTML app using Tailwind CSS CDN. "
                    f"Include dark mode toggle, animations, empty states, toast notifications. "
                    f"Wrap your code in ```html fences."
                )},
            ],
            temperature=0.7,
            max_tokens=8192,
            retries=3,
            thinking=False,
            model=settings.GLM_FAST_MODEL,
        )
        code = strip_fences(code_text)

        if not code:
            # Try fallback model
            _add_step(build_id, "Fast model empty — trying fallback model...")
            code_text = await chat(
                messages=[
                    {"role": "system", "content": CODE_SYSTEM},
                    {"role": "user", "content": f"Build a complete single-file HTML app for: {prompt}\n\nWrap in ```html fences."},
                ],
                temperature=0.7,
                max_tokens=8192,
                retries=2,
                thinking=False,
                model=settings.GLM_FALLBACK_MODEL,
            )
            code = strip_fences(code_text)

        if not code:
            # Last resort: try the primary model (glm-5.1) — may have separate quota
            _add_step(build_id, "Fallback also empty — trying primary model (glm-5.1)...")
            await asyncio.sleep(10)  # Wait before hitting primary
            code_text = await chat(
                messages=[
                    {"role": "system", "content": CODE_SYSTEM},
                    {"role": "user", "content": f"Build a complete single-file HTML app for: {prompt}\n\nWrap in ```html fences."},
                ],
                temperature=0.7,
                max_tokens=8192,
                retries=2,
                thinking=False,
                model=settings.GLM_MODEL,
            )
            code = strip_fences(code_text)

        if not code:
            _add_step(
                build_id,
                "All models rate-limited. Wait a few minutes and retry, "
                "or set GLM_MAX_CONCURRENT_REQUESTS=1 to reduce load.",
            )
            raise ValueError("All models returned empty code — cannot proceed")

        _update_build(build_id, generated_code=code)
        _add_step(build_id, f"Code generated ({len(code)} chars)")
    else:
        # Unknown — use existing code or fail
        code = existing_code or ""
        if not code:
            raise ValueError("No code available and unknown retry state")

    # Deploy
    _update_build(build_id, status="deploying")
    _add_step(build_id, "Deploying app...")
    deploy_url = deploy_html(build_id, code)
    _update_build(
        build_id,
        status="deployed",
        deploy_url=deploy_url,
        deployed_at=datetime.now(UTC),
        tech_stack=json.dumps({
            "frontend": "HTML + Tailwind CSS + JavaScript",
            "backend": "None (client-only)",
            "database": "localStorage",
            "deployment": "Static HTML",
        }),
    )
    _add_step(build_id, f"Deployed at {deploy_url}")
    schedule_post_deploy_hooks(build_id, deploy_url)


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
        deployed_at=datetime.now(UTC),
    )
    _add_step(build_id, f"Deployed at {deploy_url}")
    _add_step(build_id, f"Download zip: {zip_url}")
    schedule_post_deploy_hooks(build_id, deploy_url)


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

            # PM Agent: Write PRD
            prd = await write_prd(build_id, prompt)

            # Design Agent: Create design system
            design = await create_design_system(build_id, prompt, prd)

            # Enrich prompt with PRD + design context for downstream agents
            enriched_prompt = (
                f"{prompt}\n\n"
                f"PRD: {json.dumps(prd, indent=2)[:3000]}\n\n"
                f"Design System: {json.dumps(design, indent=2)[:2000]}"
            )

            deploy_url = await run_fullstack_pipeline(build_id, enriched_prompt, classification)

            # Generate thumbnail (non-blocking)
            asyncio.create_task(_safe_thumbnail(build_id, prompt))
            logger.info("Build %s completed (fullstack): %s", build_id, deploy_url)
        else:
            # ── Simple single-file pipeline with multi-agent quality ──
            logger.info("Build %s using enhanced simple pipeline", build_id)

            # PM Agent: Write PRD with acceptance criteria
            prd = await write_prd(build_id, prompt)

            # Design Agent: Create visual design system
            design = await create_design_system(build_id, prompt, prd)

            # Plan (with web search + thinking + PRD + design context)
            plan_prompt = (
                f"{prompt}\n\n"
                f"PRD: {json.dumps(prd, indent=2)[:3000]}\n\n"
                f"Design System: {json.dumps(design, indent=2)[:2000]}"
            )
            plan = await plan_app(build_id, plan_prompt)

            # Generate code with live streaming
            code = await generate_code(build_id, plan_prompt, plan)

            # Store as generated_files so the Files tab works for simple apps too
            _update_build(build_id, generated_code=code, generated_files=json.dumps({"index.html": code}))

            # QA Agent: Validate against PRD acceptance criteria
            code = await qa_validate(build_id, code, prd)

            # Polish Agent: Animations, empty states, dark mode, micro-interactions
            code = await polish_pass(build_id, code)

            # Visual Feedback Loop: Browser screenshot → GLM-5V fix
            code = await visual_validate(build_id, code)

            # Autopilot: Run in headless browser, detect errors, auto-fix
            app_name = parsed.get("app_name", "App")

            if settings.ENABLE_AUTOPILOT:
                _add_step(build_id, "Running autopilot error detection...")

                def _on_autopilot_iteration(iteration: int, errors_found: int, screenshot_available: bool):
                    if errors_found > 0:
                        _add_step(build_id, f"Autopilot iteration {iteration}: {errors_found} error(s) found, fixing...")
                    else:
                        _add_step(build_id, f"Autopilot iteration {iteration}: No errors detected")

                fixed_code, iterations = await autopilot_fix_loop(code, on_iteration=_on_autopilot_iteration)
                if iterations > 0:
                    code = fixed_code
                    _add_step(build_id, f"Autopilot completed after {iterations} iteration(s)")
            else:
                _add_step(build_id, "Autopilot skipped (disabled)")

            # Deploy
            _update_build(build_id, status="deploying")
            _add_step(build_id, "Deploying app...")
            deploy_url = deploy_html(build_id, code)

            # Generate test suite (non-blocking for simple apps)
            if settings.ENABLE_AUTO_TEST_GEN:
                async def _generate_and_deploy_tests():
                    try:
                        tests = await generate_tests(code, app_name=app_name)
                        for test_path, test_content in tests.items():
                            test_url = deploy_test_file(build_id, test_path, test_content)
                            _add_step(build_id, f"Test suite deployed at {test_url}")
                    except Exception as e:
                        logger.warning("Test generation failed for build %s: %s", build_id, e)

                asyncio.create_task(_generate_and_deploy_tests())
            else:
                logger.info("Test generation skipped for build %s (disabled)", build_id)

            _update_build(
                build_id,
                status="deployed",
                deploy_url=deploy_url,
                deployed_at=datetime.now(UTC),
                tech_stack=json.dumps({
                    "frontend": "HTML + Tailwind CSS + JavaScript",
                    "backend": "None (client-only)",
                    "database": "localStorage",
                    "deployment": "Static HTML",
                }),
            )
            _add_step(build_id, f"Deployed at {deploy_url}")
            schedule_post_deploy_hooks(build_id, deploy_url)

            # Generate thumbnail (non-blocking)
            asyncio.create_task(_safe_thumbnail(build_id, prompt))
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
            from agent.helpers import _add_reasoning
            _add_reasoning(build_id, "vision", reasoning)
            _add_step(build_id, f"[thinking] GLM-5V analyzed the design ({len(reasoning)} chars)")

        if not code:
            raise ValueError("GLM-5V-Turbo returned empty code — cannot proceed")

        _update_build(build_id, status="coding", generated_code=code)
        _add_step(build_id, f"Screenshot converted to code ({len(code)} chars)")

        # Step 2: Review
        code = await review_code(build_id, code)

        app_name_desc = text_prompt or "Screenshot App"

        # Autopilot (parity with text/simple pipeline)
        if settings.ENABLE_AUTOPILOT:
            _add_step(build_id, "Running autopilot error detection...")

            def _on_autopilot_iteration(iteration: int, errors_found: int, screenshot_available: bool):
                if errors_found > 0:
                    _add_step(build_id, f"Autopilot iteration {iteration}: {errors_found} error(s) found, fixing...")
                else:
                    _add_step(build_id, f"Autopilot iteration {iteration}: No errors detected")

            fixed_code, iterations = await autopilot_fix_loop(code, on_iteration=_on_autopilot_iteration)
            if iterations > 0:
                code = fixed_code
                _add_step(build_id, f"Autopilot completed after {iterations} iteration(s)")
        else:
            _add_step(build_id, "Autopilot skipped (disabled)")

        # Step 3: Deploy
        _update_build(build_id, status="deploying")
        _add_step(build_id, "Deploying app...")
        deploy_url = deploy_html(build_id, code)

        # Generate test suite (non-blocking)

        if settings.ENABLE_AUTO_TEST_GEN:
            async def _generate_screenshot_tests():
                try:
                    tests = await generate_tests(code, app_name=app_name_desc)
                    for test_path, test_content in tests.items():
                        test_url = deploy_test_file(build_id, test_path, test_content)
                        _add_step(build_id, f"Test suite deployed at {test_url}")
                except Exception as e:
                    logger.warning("Test generation failed for screenshot build %s: %s", build_id, e)

            asyncio.create_task(_generate_screenshot_tests())
        else:
            logger.info("Test generation skipped for screenshot build %s (disabled)", build_id)

        _update_build(
            build_id,
            status="deployed",
            deploy_url=deploy_url,
            deployed_at=datetime.now(UTC),
        )
        _add_step(build_id, f"Deployed at {deploy_url}")
        schedule_post_deploy_hooks(build_id, deploy_url)

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


async def run_modify_pipeline(build_id: str, original_code: str, modification: str, *, quick: bool = False):
    """Run a modification pipeline — takes existing code and applies changes."""
    try:
        _update_build(build_id, status="coding")
        _add_step(build_id, f"Modifying: {modification[:100]}...")

        await asyncio.sleep(1)

        system = QUICK_MODIFY_SYSTEM if quick else MODIFY_SYSTEM
        code_ctx = original_code if len(original_code) < 120_000 else original_code[-120_000:]
        max_tok = 8192 if quick else 16384

        result = await chat_with_reasoning(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"Requested change: {modification}\n\nCurrent code:\n```html\n{code_ctx}\n```"},
            ],
            temperature=0.5,
            max_tokens=max_tok,
            retries=2,
        )

        modified = _strip_fences(result["content"])
        reasoning = result["reasoning"]

        if reasoning:
            from agent.helpers import _add_reasoning
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
            deployed_at=datetime.now(UTC),
        )
        _add_step(build_id, f"Deployed at {deploy_url}")
        schedule_post_deploy_hooks(build_id, deploy_url)
        logger.info("Modification %s completed: %s", build_id, deploy_url)

    except Exception as e:
        with Session(engine) as session:
            build = session.get(Build, build_id)
            failed_at = build.status if build else "unknown"
        logger.exception("Modify %s failed at [%s]: %s", build_id, failed_at, str(e))
        _update_build(build_id, status="failed", error=f"[{failed_at}] {str(e)}")
        _add_step(build_id, f"Modification failed: {str(e)}")
