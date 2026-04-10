"""Build CRUD endpoints — text builds, screenshot builds, and modifications."""

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select
from sse_starlette.sse import EventSourceResponse

from agent.pipeline import (
    run_modify_fullstack_pipeline,
    run_modify_pipeline,
    run_pipeline,
    run_retry_pipeline,
    run_screenshot_pipeline,
)
from config import settings
from database import get_session
from models import Build
from rate_limiter import limiter
from services.build_tools import collect_chain_ids, diff_builds as compute_file_diffs
from services.cloud_deploy import export_build_files_to_github, export_build_files_to_github_pr
from services.event_bus import subscribe, unsubscribe
from services.post_deploy_hooks import probe_build_url, schedule_post_deploy_hooks

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/builds", tags=["Builds"])

_TEMPLATES_FILE = Path(__file__).resolve().parent.parent / "data" / "build_templates.json"


class BuildCreate(BaseModel):
    tweet_id: str | None = None
    tweet_text: str | None = None
    twitter_username: str | None = None
    prompt: str | None = None
    build_options: dict | None = None  # constraints, acceptance_paths, etc.
    webhook_url: str | None = None
    workspace_id: str | None = None


class ScreenshotBuildCreate(BaseModel):
    image_base64: str | list[str]  # single base64 or list of base64 images
    prompt: str | None = ""  # text instructions (what the app should do)
    build_options: dict | None = None
    webhook_url: str | None = None
    workspace_id: str | None = None


class FigmaHandoffCreate(BaseModel):
    """Design frame as image plus optional design tokens (JSON string)."""

    image_base64: str
    design_tokens: str | None = None  # JSON or CSS variables as text
    prompt: str | None = ""


class RestoreFromRequest(BaseModel):
    source_build_id: str


class QuickModifyRequest(BaseModel):
    instruction: str


class ModifyRequest(BaseModel):
    modification: str


class RemixRequest(BaseModel):
    prompt: str  # what the user wants to change


class CloudDeployRequest(BaseModel):
    provider: str  # "railway" or "render"


class BuildResponse(BaseModel):
    id: str
    tweet_id: str | None = None
    tweet_text: str | None = None
    twitter_username: str | None = None
    app_name: str | None = None
    app_description: str | None = None
    prompt: str | None = None
    status: str
    generated_code: str | None = None
    deploy_url: str | None = None
    parent_build_id: str | None = None
    build_type: str = "text"
    complexity: str | None = "simple"
    thumbnail_url: str | None = None
    reasoning_log: str | None = None
    file_manifest: str | None = None
    generated_files: str | None = None
    zip_url: str | None = None
    tech_stack: str | None = None
    remix_count: int = 0
    deploy_provider: str | None = None
    deploy_external_url: str | None = None
    deploy_status: str | None = None
    steps: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    deployed_at: datetime | None = None
    build_options: str | None = None
    quality_status: str | None = None
    webhook_url: str | None = None
    step_events: str | None = None
    workspace_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


@router.post("", response_model=BuildResponse)
@limiter.limit("10/minute")
async def create_build(request: Request, data: BuildCreate, session: Session = Depends(get_session)):
    """Trigger a new text-to-app build."""
    build = Build(
        tweet_id=data.tweet_id,
        tweet_text=data.tweet_text,
        twitter_username=data.twitter_username,
        prompt=data.prompt or data.tweet_text,
        build_type="text",
        status="pending",
        build_options=json.dumps(data.build_options) if data.build_options else None,
        webhook_url=data.webhook_url,
        workspace_id=data.workspace_id,
    )
    session.add(build)
    session.commit()
    session.refresh(build)

    asyncio.create_task(_run_build_pipeline(build.id))
    return build


@router.post("/from-image", response_model=BuildResponse)
@limiter.limit("5/minute")
async def create_build_from_image(request: Request, data: ScreenshotBuildCreate, session: Session = Depends(get_session)):
    """Trigger a screenshot-to-app build using GLM-5V-Turbo."""
    # Normalize to list of base64 strings
    raw_images = data.image_base64 if isinstance(data.image_base64, list) else [data.image_base64]
    images_b64 = []
    for img in raw_images:
        if "," in img and img.startswith("data:"):
            img = img.split(",", 1)[1]
        images_b64.append(img)

    prompt_text = data.prompt or ""
    # Derive app name from prompt
    app_name = prompt_text.split(".")[0].strip()[:60] if prompt_text else "App from Screenshot"
    if not app_name:
        app_name = "App from Screenshot"

    build = Build(
        tweet_text=prompt_text or "Screenshot-to-App build",
        prompt=prompt_text or "Build a fully functional app from the provided screenshot(s)",
        app_name=app_name,
        build_type="screenshot",
        status="pending",
        build_options=json.dumps(data.build_options) if data.build_options else None,
        webhook_url=data.webhook_url,
        workspace_id=data.workspace_id,
    )
    session.add(build)
    session.commit()
    session.refresh(build)

    asyncio.create_task(run_screenshot_pipeline(build.id, images_b64, prompt_text))
    return build


@router.get("", response_model=list[BuildResponse])
async def list_builds(
    status: str | None = None,
    workspace_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    """List all builds with optional status filter."""
    statement = select(Build).order_by(Build.created_at.desc())
    if status:
        statement = statement.where(Build.status == status)
    if workspace_id:
        statement = statement.where(Build.workspace_id == workspace_id)
    statement = statement.offset(offset).limit(limit)
    builds = session.exec(statement).all()
    return builds


@router.get("/catalog/templates")
async def list_template_catalog():
    """Built-in template slugs for Start-from-template flows."""
    if not _TEMPLATES_FILE.is_file():
        return []
    try:
        return json.loads(_TEMPLATES_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


@router.get("/{build_id}", response_model=BuildResponse)
async def get_build(build_id: str, session: Session = Depends(get_session)):
    """Get build details."""
    build = session.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    return build


@router.get("/{build_id}/steps")
async def get_build_steps(build_id: str, session: Session = Depends(get_session)):
    """Get agent steps for a build."""
    build = session.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    steps = json.loads(build.steps) if build.steps else []
    # Gaps longer than this are "idle" (e.g. user waited before Retry) — not step duration.
    _IDLE_GAP_MS = 5 * 60 * 1000

    timing: list[dict] = []
    try:
        events = json.loads(build.step_events) if build.step_events else []
        from datetime import datetime as dt

        prev: dt | None = None
        for ev in events:
            if not isinstance(ev, dict) or "t" not in ev:
                continue
            try:
                cur = dt.fromisoformat(ev["t"].replace("Z", "+00:00"))
            except ValueError:
                continue
            delta_ms = None
            if prev is not None:
                delta_ms = int((cur - prev).total_seconds() * 1000)
            row: dict = {"message": ev.get("m", ""), "at": ev["t"]}
            if delta_ms is None:
                row["since_previous_ms"] = None
            elif delta_ms > _IDLE_GAP_MS:
                row["since_previous_ms"] = None
                row["idle_before_ms"] = delta_ms
            else:
                row["since_previous_ms"] = delta_ms
            timing.append(row)
            prev = cur
    except (json.JSONDecodeError, TypeError):
        pass
    return {"build_id": build_id, "status": build.status, "steps": steps, "timing": timing}


@router.get("/{build_id}/stream")
async def stream_build(build_id: str, request: Request):
    """SSE endpoint — streams pipeline events in real time."""

    async def event_generator():
        queue = subscribe(build_id)
        try:
            # Send initial heartbeat
            yield {"event": "connected", "data": json.dumps({"build_id": build_id})}

            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    event_type = event.pop("type", "update")
                    yield {"event": event_type, "data": json.dumps(event)}

                    # Stop streaming when build reaches terminal state
                    if event_type == "status" and event.get("status") in ("deployed", "failed"):
                        yield {"event": "done", "data": json.dumps({"status": event.get("status")})}
                        break
                except TimeoutError:
                    # Send keepalive ping
                    yield {"event": "ping", "data": "{}"}
        finally:
            unsubscribe(build_id, queue)

    return EventSourceResponse(event_generator())


@router.post("/{build_id}/deploy", response_model=BuildResponse)
async def deploy_build(build_id: str, session: Session = Depends(get_session)):
    """Manually trigger deploy for a build."""
    build = session.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    if not build.generated_code:
        raise HTTPException(status_code=400, detail="No generated code to deploy")

    from services.deployer import deploy_html
    deploy_url = deploy_html(build_id, build.generated_code)
    build.deploy_url = deploy_url
    build.status = "deployed"
    build.deployed_at = datetime.now(UTC)
    build.updated_at = datetime.now(UTC)
    session.add(build)
    session.commit()
    session.refresh(build)
    return build


@router.post("/{build_id}/modify", response_model=BuildResponse)
async def modify_build(build_id: str, data: ModifyRequest, session: Session = Depends(get_session)):
    """Create a modified version of an existing build. Routes to fullstack or simple pipeline."""
    original = session.get(Build, build_id)
    if not original:
        raise HTTPException(status_code=404, detail="Build not found")

    is_multi_file = original.complexity in ("standard", "fullstack") and original.generated_files
    if not is_multi_file and not original.generated_code:
        raise HTTPException(status_code=400, detail="Original build has no code to modify")

    new_build = Build(
        tweet_text=data.modification,
        app_name=f"{original.app_name or 'App'} (v{_count_versions(session, build_id) + 1})",
        app_description=data.modification,
        prompt=data.modification,
        parent_build_id=build_id,
        build_type=original.build_type,
        complexity=original.complexity,
        status="pending",
    )
    session.add(new_build)
    session.commit()
    session.refresh(new_build)

    if is_multi_file:
        # Multi-file iterative modification pipeline
        existing_files = json.loads(original.generated_files)
        manifest = json.loads(original.file_manifest) if original.file_manifest else {"files": [], "features": []}
        asyncio.create_task(
            run_modify_fullstack_pipeline(new_build.id, data.modification, existing_files, manifest)
        )
    else:
        # Single-file modification pipeline (existing behavior)
        asyncio.create_task(
            run_modify_pipeline(new_build.id, original.generated_code, data.modification)
        )
    return new_build


@router.post("/{build_id}/remix", response_model=BuildResponse)
async def remix_build(build_id: str, data: RemixRequest, session: Session = Depends(get_session)):
    """Create a remixed version of an existing build with a new prompt direction."""
    original = session.get(Build, build_id)
    if not original:
        raise HTTPException(status_code=404, detail="Build not found")
    if original.status != "deployed":
        raise HTTPException(status_code=400, detail="Can only remix deployed builds")

    is_multi_file = original.complexity in ("standard", "fullstack") and original.generated_files
    if not is_multi_file and not original.generated_code:
        raise HTTPException(status_code=400, detail="Original build has no code to remix")

    # Derive app name from the remix prompt (first sentence, capped)
    app_name = data.prompt.split(".")[0].strip()[:60] or "Remixed App"

    new_build = Build(
        tweet_text=data.prompt,
        app_name=app_name,
        app_description=data.prompt,
        prompt=data.prompt,
        parent_build_id=build_id,
        build_type=original.build_type,
        complexity=original.complexity,
        status="pending",
    )
    session.add(new_build)

    # Increment remix_count on the original build
    original.remix_count = original.remix_count + 1
    original.updated_at = datetime.now(UTC)
    session.add(original)

    session.commit()
    session.refresh(new_build)

    if is_multi_file:
        existing_files = json.loads(original.generated_files)
        manifest = json.loads(original.file_manifest) if original.file_manifest else {"files": [], "features": []}
        asyncio.create_task(
            run_modify_fullstack_pipeline(new_build.id, data.prompt, existing_files, manifest)
        )
    else:
        asyncio.create_task(
            run_modify_pipeline(new_build.id, original.generated_code, data.prompt)
        )
    return new_build


def _count_versions(session: Session, build_id: str) -> int:
    """Count how many versions exist in a build chain."""
    count = 1
    current_id = build_id
    while current_id:
        build = session.get(Build, current_id)
        if not build or not build.parent_build_id:
            break
        current_id = build.parent_build_id
        count += 1
    return count


@router.get("/{build_id}/download")
async def download_build(build_id: str, session: Session = Depends(get_session)):
    """Download the project as a zip file."""
    build = session.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    if not build.zip_url:
        raise HTTPException(status_code=404, detail="No zip available for this build")

    from services.deployer import DEPLOYED_DIR
    zip_path = DEPLOYED_DIR / build_id / "project.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Zip file not found on disk")

    filename = f"{(build.app_name or 'project').replace(' ', '-').lower()}.zip"
    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=filename,
    )


@router.post("/{build_id}/cloud-deploy", response_model=BuildResponse)
@limiter.limit("3/minute")
async def cloud_deploy_build(
    request: Request,
    build_id: str,
    data: CloudDeployRequest,
    session: Session = Depends(get_session),
):
    """Deploy a build to a cloud provider (Railway or Render)."""
    build = session.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    if build.status != "deployed":
        raise HTTPException(status_code=400, detail="Build must be deployed locally before cloud deploy")
    if not build.generated_code and not build.generated_files:
        raise HTTPException(status_code=400, detail="No generated code available to deploy")

    provider = data.provider.lower()
    if provider not in ("railway", "render"):
        raise HTTPException(status_code=400, detail="Provider must be 'railway' or 'render'")

    # Collect project files
    project_files: dict[str, str] = {}
    if build.generated_files:
        project_files = json.loads(build.generated_files)
    elif build.generated_code:
        project_files = {"index.html": build.generated_code}

    app_name = (build.app_name or "builddy-app").replace(" ", "-").lower()[:40]

    from services.cloud_deploy import deploy_to_cloud
    result = await deploy_to_cloud(build_id, provider, project_files, app_name)

    build.deploy_provider = provider
    build.deploy_status = result.get("status", "pending")
    if result.get("url"):
        build.deploy_external_url = result["url"]
    build.updated_at = datetime.now(UTC)
    session.add(build)
    session.commit()
    session.refresh(build)
    return build


@router.get("/{build_id}/deploy-status")
async def get_cloud_deploy_status(build_id: str, session: Session = Depends(get_session)):
    """Check current cloud deploy status for a build."""
    build = session.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    if not build.deploy_provider:
        return {"status": "none", "provider": None, "url": None, "instructions": None}

    from services.cloud_deploy import get_deploy_status, get_manual_deploy_instructions

    if build.deploy_status == "manual":
        instructions = get_manual_deploy_instructions(build_id, build.app_name or "builddy-app")
        return {
            "status": "manual",
            "provider": build.deploy_provider,
            "url": build.deploy_external_url,
            "instructions": instructions,
        }

    status_info = await get_deploy_status(build.deploy_provider, build_id)
    # Update status if changed
    if status_info.get("status") and status_info["status"] != build.deploy_status:
        build.deploy_status = status_info["status"]
        if status_info.get("url"):
            build.deploy_external_url = status_info["url"]
        build.updated_at = datetime.now(UTC)
        session.add(build)
        session.commit()

    return {
        "status": build.deploy_status,
        "provider": build.deploy_provider,
        "url": build.deploy_external_url,
        "instructions": status_info.get("instructions"),
    }


@router.get("/{build_id}/files")
async def get_build_files(build_id: str, session: Session = Depends(get_session)):
    """Get all generated files for a build."""
    build = session.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    if build.generated_files:
        files = json.loads(build.generated_files)
        return {
            "build_id": build_id,
            "complexity": build.complexity,
            "file_count": len(files),
            "files": files,
        }

    # Fallback: single-file builds return generated_code as index.html
    if build.generated_code:
        return {
            "build_id": build_id,
            "complexity": "simple",
            "file_count": 1,
            "files": {"index.html": build.generated_code},
        }

    raise HTTPException(status_code=404, detail="No files available for this build")


@router.put("/{build_id}/files")
async def update_build_file(build_id: str, payload: dict, session: Session = Depends(get_session)):
    """Update a single file in a deployed build and redeploy.

    Body: { "file_path": "index.html", "content": "..." }
    """
    build = session.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    if build.status != "deployed":
        raise HTTPException(status_code=400, detail="Can only edit deployed builds")

    file_path = payload.get("file_path", "")
    content = payload.get("content", "")
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")

    # Prevent path traversal attacks
    if ".." in file_path or file_path.startswith("/") or file_path.startswith("\\"):
        raise HTTPException(status_code=400, detail="Invalid file path")

    from services.deployer import deploy_html, deploy_project

    # Update generated_files or generated_code in DB
    if build.generated_files:
        files = json.loads(build.generated_files)
        files[file_path] = content
        build.generated_files = json.dumps(files)
        # Redeploy all files
        deploy_project(build_id, files)
    else:
        # Simple single-file build
        build.generated_code = content
        deploy_html(build_id, content)

    build.updated_at = datetime.now(UTC)
    session.add(build)
    session.commit()
    session.refresh(build)

    return {"status": "updated", "file_path": file_path, "build_id": build_id}


@router.get("/{build_id}/chain")
async def get_build_chain(build_id: str, session: Session = Depends(get_session)):
    """Get the full version chain for a build (from original to current)."""
    build = session.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    # Walk UP to find the root
    root_id = build_id
    visited = {root_id}
    current = build
    while current.parent_build_id:
        if current.parent_build_id in visited:
            break  # prevent cycles
        root_id = current.parent_build_id
        visited.add(root_id)
        current = session.get(Build, root_id)
        if not current:
            break

    # Walk DOWN from root collecting all descendants
    chain = []
    queue = [root_id]
    visited_down = set()
    while queue:
        cid = queue.pop(0)
        if cid in visited_down:
            continue
        visited_down.add(cid)
        b = session.get(Build, cid)
        if not b:
            continue
        chain.append({
            "id": b.id,
            "app_name": b.app_name,
            "prompt": b.prompt,
            "status": b.status,
            "complexity": b.complexity,
            "created_at": str(b.created_at),
            "parent_build_id": b.parent_build_id,
        })
        # Find children
        children = session.exec(
            select(Build).where(Build.parent_build_id == cid)
        ).all()
        for child in children:
            queue.append(child.id)

    # Sort by created_at ascending (oldest first)
    chain.sort(key=lambda x: x["created_at"])
    return chain


@router.get("/{build_id}/diff/{other_id}")
async def build_file_diff(build_id: str, other_id: str, session: Session = Depends(get_session)):
    """Unified diff of generated files between two builds (same chain not required)."""
    ba = session.get(Build, build_id)
    bb = session.get(Build, other_id)
    if not ba or not bb:
        raise HTTPException(status_code=404, detail="Build not found")
    return {
        "build_a": build_id,
        "build_b": other_id,
        "files": compute_file_diffs(ba, bb),
    }


@router.post("/{anchor_id}/restore", response_model=BuildResponse)
@limiter.limit("5/minute")
async def restore_build_snapshot(
    request: Request,
    anchor_id: str,
    data: RestoreFromRequest,
    session: Session = Depends(get_session),
):
    """Create a new build that copies files from an older chain member; parent links to *anchor_id*."""
    anchor = session.get(Build, anchor_id)
    source = session.get(Build, data.source_build_id)
    if not anchor or not source:
        raise HTTPException(status_code=404, detail="Build not found")
    chain = collect_chain_ids(session, anchor_id)
    if data.source_build_id not in chain:
        raise HTTPException(status_code=400, detail="Source build must be in the same version chain")

    new_build = Build(
        tweet_text=f"Restored from {source.id[:8]}",
        prompt=f"Restored snapshot from build {source.id[:8]}",
        app_name=source.app_name or anchor.app_name or "Restored app",
        app_description=source.app_description,
        parent_build_id=anchor_id,
        build_type=source.build_type or "text",
        complexity=source.complexity or "simple",
        status="deploying",
        generated_code=source.generated_code,
        generated_files=source.generated_files,
        file_manifest=source.file_manifest,
        tech_stack=source.tech_stack,
        thumbnail_url=source.thumbnail_url,
    )
    session.add(new_build)
    session.commit()
    session.refresh(new_build)

    asyncio.create_task(_deploy_restored_build(new_build.id))
    return new_build


@router.post("/{build_id}/quick-modify", response_model=BuildResponse)
@limiter.limit("10/minute")
async def quick_modify_build(
    request: Request,
    build_id: str,
    data: QuickModifyRequest,
    session: Session = Depends(get_session),
):
    """Fast modification path for simple single-file HTML builds only."""
    original = session.get(Build, build_id)
    if not original:
        raise HTTPException(status_code=404, detail="Build not found")
    if original.complexity in ("standard", "fullstack") and original.generated_files:
        raise HTTPException(
            status_code=400,
            detail="Quick modify supports simple HTML builds only; use /modify for fullstack",
        )
    if not original.generated_code:
        raise HTTPException(status_code=400, detail="No generated HTML to modify")

    new_build = Build(
        tweet_text=data.instruction,
        app_name=f"{original.app_name or 'App'} (quick)",
        app_description=data.instruction,
        prompt=data.instruction,
        parent_build_id=build_id,
        build_type=original.build_type,
        complexity="simple",
        status="pending",
    )
    session.add(new_build)
    session.commit()
    session.refresh(new_build)

    asyncio.create_task(
        run_modify_pipeline(new_build.id, original.generated_code, data.instruction, quick=True)
    )
    return new_build


@router.get("/{build_id}/probe")
async def probe_deployed_build(build_id: str, session: Session = Depends(get_session)):
    """HTTP probe of deploy or cloud URL (post-deploy ops MVP)."""
    build = session.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    return await probe_build_url(build)


@router.post("/{build_id}/github-sync")
@limiter.limit("3/minute")
async def github_sync_build(request: Request, build_id: str, session: Session = Depends(get_session)):
    """Export current build files to a new GitHub repository (requires GITHUB_TOKEN)."""
    if not settings.GITHUB_TOKEN:
        raise HTTPException(status_code=400, detail="GITHUB_TOKEN not configured")
    build = session.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    project_files: dict[str, str] = {}
    if build.generated_files:
        project_files = json.loads(build.generated_files)
    elif build.generated_code:
        project_files = {"index.html": build.generated_code}
    else:
        raise HTTPException(status_code=400, detail="No files to export")

    app_name = (build.app_name or "builddy-app").replace(" ", "-").lower()[:40]
    repo_url = await export_build_files_to_github(build_id, project_files, app_name)
    return {"repo_url": repo_url, "pull_requests_url": f"{repo_url}/compare"}


@router.post("/{build_id}/github-pr")
@limiter.limit("3/minute")
async def github_pr_export(request: Request, build_id: str, session: Session = Depends(get_session)):
    """Push files on a side branch and open a PR against the repo default branch."""
    if not settings.GITHUB_TOKEN:
        raise HTTPException(status_code=400, detail="GITHUB_TOKEN not configured")
    build = session.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    project_files: dict[str, str] = {}
    if build.generated_files:
        project_files = json.loads(build.generated_files)
    elif build.generated_code:
        project_files = {"index.html": build.generated_code}
    else:
        raise HTTPException(status_code=400, detail="No files to export")

    app_name = (build.app_name or "builddy-app").replace(" ", "-").lower()[:40]
    try:
        result = await export_build_files_to_github_pr(build_id, project_files, app_name)
    except Exception as e:
        logger.exception("GitHub PR export failed for %s", build_id)
        raise HTTPException(status_code=500, detail=str(e)) from e
    return result


@router.post("/from-template/{slug}", response_model=BuildResponse)
@limiter.limit("10/minute")
async def create_build_from_template(
    request: Request,
    slug: str,
    session: Session = Depends(get_session),
):
    """Start a new text build from a built-in template slug."""
    if not _TEMPLATES_FILE.is_file():
        raise HTTPException(status_code=500, detail="Templates file missing")
    try:
        templates = json.loads(_TEMPLATES_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid templates JSON: {e}") from e
    entry = next((t for t in templates if t.get("slug") == slug), None)
    if not entry or not entry.get("prompt"):
        raise HTTPException(status_code=404, detail="Unknown template slug")

    build = Build(
        tweet_text=entry.get("name", slug),
        prompt=entry["prompt"],
        app_name=entry.get("name", slug)[:60],
        app_description=entry.get("description", ""),
        build_type="text",
        status="pending",
    )
    session.add(build)
    session.commit()
    session.refresh(build)
    asyncio.create_task(_run_build_pipeline(build.id))
    return build


@router.post("/from-figma", response_model=BuildResponse)
@limiter.limit("5/minute")
async def create_build_from_figma(request: Request, data: FigmaHandoffCreate, session: Session = Depends(get_session)):
    """Figma / design handoff MVP: frame image + optional design tokens, same pipeline as screenshot."""
    img = data.image_base64
    if "," in img and img.startswith("data:"):
        img = img.split(",", 1)[1]

    prompt_text = data.prompt or ""
    if data.design_tokens:
        prompt_text = (
            f"{prompt_text}\n\nDesign tokens / theme (apply consistently):\n{data.design_tokens[:12000]}"
        ).strip()

    app_name = (prompt_text.split(".")[0].strip()[:60] if prompt_text else "") or "Figma handoff"
    build = Build(
        tweet_text=prompt_text or "Figma handoff build",
        prompt=prompt_text or "Implement the UI from the design frame; match spacing, typography, and colors.",
        app_name=app_name,
        build_type="screenshot",
        status="pending",
    )
    session.add(build)
    session.commit()
    session.refresh(build)

    asyncio.create_task(run_screenshot_pipeline(build.id, [img], prompt_text))
    return build


@router.post("/{build_id}/retry", response_model=BuildResponse)
@limiter.limit("5/minute")
async def retry_build(request: Request, build_id: str, session: Session = Depends(get_session)):
    """Retry a failed or stuck build from the point of failure."""
    build = session.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    # Allow retry on failed OR stuck builds (coding/planning/reviewing that hung)
    terminal_ok = {"deployed"}
    if build.status in terminal_ok:
        raise HTTPException(status_code=400, detail="Build already deployed")

    # Parse failed_at stage from error or current status
    failed_at = build.status  # default: resume from current stuck stage
    if build.error:
        match = build.error.split("]")[0].replace("[", "").strip()
        if match:
            failed_at = match

    # Reset status to pending so the UI shows it's retrying
    build.status = "pending"
    build.error = None
    build.updated_at = datetime.now(UTC)
    session.add(build)
    session.commit()
    session.refresh(build)

    asyncio.create_task(run_retry_pipeline(build_id, failed_at=failed_at))
    return build


@router.delete("/{build_id}")
async def delete_build(build_id: str, session: Session = Depends(get_session)):
    """Delete a build and its deployed files."""
    build = session.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    # Delete deployed files from disk
    import shutil

    from services.deployer import DEPLOYED_DIR
    app_dir = DEPLOYED_DIR / build_id
    if app_dir.exists():
        shutil.rmtree(app_dir, ignore_errors=True)

    # Stop Express process if running
    try:
        from services.process_manager import process_manager
        await process_manager.stop_app(build_id)
    except Exception:
        pass

    # Delete from DB
    session.delete(build)
    session.commit()

    return {"status": "deleted", "build_id": build_id}


@router.post("/{build_id}/generate-tests")
async def generate_tests_for_build(build_id: str, session: Session = Depends(get_session)):
    """Generate a test suite for a deployed build using the AI Test Generator agent."""
    build = session.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    if build.status != "deployed":
        raise HTTPException(status_code=400, detail="Build must be deployed first")
    if not build.generated_code and not build.generated_files:
        raise HTTPException(status_code=400, detail="No generated code to test")

    from agent.test_gen import generate_tests

    all_files = json.loads(build.generated_files) if build.generated_files else None
    manifest = json.loads(build.file_manifest) if build.file_manifest else None

    test_files = await generate_tests(
        code=build.generated_code or "",
        app_name=build.app_name or "App",
        complexity=build.complexity or "simple",
        manifest=manifest,
        all_files=all_files,
    )

    if not test_files:
        raise HTTPException(status_code=500, detail="Test generation failed")

    # Merge test files into the build's generated files
    if build.generated_files:
        files = json.loads(build.generated_files)
        files.update(test_files)
        build.generated_files = json.dumps(files)
    else:
        build.generated_files = json.dumps(test_files)

    build.updated_at = datetime.now(UTC)
    session.add(build)
    session.commit()

    # Redeploy with test files included
    from services.deployer import deploy_project

    if build.complexity in ("standard", "fullstack"):
        files = json.loads(build.generated_files)
        deploy_project(build_id, files)
    elif "tests.html" in test_files:
        # For simple apps, also deploy the test file alongside index.html
        from services.deployer import DEPLOYED_DIR
        test_path = DEPLOYED_DIR / build_id / "tests.html"
        test_path.write_text(test_files["tests.html"], encoding="utf-8")

    return {
        "status": "generated",
        "test_files": list(test_files.keys()),
        "test_count": len(test_files),
    }


async def _deploy_restored_build(build_id: str):
    """Write restored snapshot to disk and mark build deployed."""
    from database import engine as db_engine
    from services.deployer import deploy_html, deploy_project

    def _work() -> str | None:
        with Session(db_engine) as session:
            b = session.get(Build, build_id)
            if not b:
                return None
            try:
                if b.generated_files:
                    files = json.loads(b.generated_files)
                    url = deploy_project(build_id, files)
                elif b.generated_code:
                    url = deploy_html(build_id, b.generated_code)
                else:
                    b.status = "failed"
                    b.error = "Restore failed: no code or files to deploy"
                    b.updated_at = datetime.now(UTC)
                    session.add(b)
                    session.commit()
                    return None
                b.deploy_url = url
                b.status = "deployed"
                b.deployed_at = datetime.now(UTC)
                b.updated_at = datetime.now(UTC)
                session.add(b)
                session.commit()
                return url
            except Exception as e:
                logger.exception("Restore deploy failed for %s", build_id)
                b.status = "failed"
                b.error = f"Restore deploy failed: {e}"
                b.updated_at = datetime.now(UTC)
                session.add(b)
                session.commit()
                return None

    url = await asyncio.to_thread(_work)
    if url:
        schedule_post_deploy_hooks(build_id, url)


async def _run_build_pipeline(build_id: str):
    """Run the agent pipeline in background."""
    try:
        await run_pipeline(build_id)
    except Exception as e:
        logger.exception("Pipeline failed for build %s: %s", build_id, e)
