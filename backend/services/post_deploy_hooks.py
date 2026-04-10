"""Acceptance URL checks, outbound webhooks, and deploy probes after builds."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime
from urllib.parse import urljoin

import httpx
from sqlmodel import Session

from config import settings
from database import engine
from models import Build

logger = logging.getLogger(__name__)


def _absolute_url(base: str, path: str) -> str:
    base = base.rstrip("/") + "/"
    if path.startswith("http"):
        return path
    return urljoin(base, path.lstrip("/"))


async def run_acceptance_checks(build_id: str, deploy_url_path: str) -> None:
    """HTTP GET paths from build_options.acceptance_paths; set quality_status."""
    with Session(engine) as session:
        build = session.get(Build, build_id)
        if not build or not build.build_options:
            return
        try:
            opts = json.loads(build.build_options)
        except json.JSONDecodeError:
            return
        paths = opts.get("acceptance_paths") or []
        if not paths or not isinstance(paths, list):
            return

    host = getattr(settings, "PUBLIC_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
    if deploy_url_path.startswith("http"):
        base = deploy_url_path
    else:
        path = deploy_url_path if deploy_url_path.startswith("/") else f"/{deploy_url_path}"
        base = host + path

    failed: list[str] = []
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for p in paths:
            if not isinstance(p, str):
                continue
            url = _absolute_url(base, p)
            try:
                r = await client.get(url)
                if r.status_code != 200:
                    failed.append(f"{p} -> {r.status_code}")
            except Exception as e:
                failed.append(f"{p} -> {e!s}")

    status = "ok" if not failed else "failed"
    with Session(engine) as session:
        b = session.get(Build, build_id)
        if b:
            b.quality_status = status
            b.updated_at = datetime.now(UTC)
            note = "Acceptance checks passed" if not failed else "Acceptance failed: " + "; ".join(failed)
            session.add(b)
            session.commit()
            from agent.helpers import _add_step

            _add_step(build_id, note)


async def emit_build_webhook(build_id: str, event: str, extra: dict | None = None) -> None:
    with Session(engine) as session:
        build = session.get(Build, build_id)
        if not build:
            return
        url = build.webhook_url
        if not url and not getattr(settings, "DEFAULT_WEBHOOK_URL", ""):
            return
        target = url or getattr(settings, "DEFAULT_WEBHOOK_URL", "")
        payload = {
            "event": event,
            "build_id": build_id,
            "status": build.status,
            "deploy_url": build.deploy_url,
            "app_name": build.app_name,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if extra:
            payload.update(extra)
        body = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"}
        secret = getattr(settings, "WEBHOOK_SIGNING_SECRET", "") or ""
        if secret:
            sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
            headers["X-Builddy-Signature"] = f"sha256={sig}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(target, content=body, headers=headers)
    except Exception as e:
        logger.warning("Webhook delivery failed for %s: %s", build_id, e)


async def run_pipeline_quality_smoke(build_id: str, deploy_url_path: str) -> None:
    """Lightweight checks when ENABLE_PIPELINE_QUALITY_CHECKS is on (reachable page + <title>)."""
    if not getattr(settings, "ENABLE_PIPELINE_QUALITY_CHECKS", False):
        return
    host = getattr(settings, "PUBLIC_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
    if deploy_url_path.startswith("http"):
        base = deploy_url_path.rstrip("/") + "/"
    else:
        path = deploy_url_path if deploy_url_path.startswith("/") else f"/{deploy_url_path}"
        base = host + path
        if not base.endswith("/"):
            base = base + "/"
    from agent.helpers import _add_step

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            r = await client.get(base)
            html = (r.text or "")[:80000]
            lower = html.lower()
            has_title = "<title>" in lower and "</title>" in lower
            if r.status_code >= 400:
                _add_step(
                    build_id,
                    f"Quality smoke: HTTP {r.status_code} for {base[:80]}…",
                )
            elif not has_title:
                _add_step(build_id, f"Quality smoke: page OK but missing <title> ({base[:60]}…)")
            else:
                _add_step(build_id, "Quality smoke: page reachable with <title> present")
    except Exception as e:
        _add_step(build_id, f"Quality smoke failed: {e!s}")


async def run_post_deploy_hooks(build_id: str, deploy_url_path: str) -> None:
    await run_pipeline_quality_smoke(build_id, deploy_url_path)
    await run_acceptance_checks(build_id, deploy_url_path)
    await emit_build_webhook(build_id, "deployed", {"deploy_path": deploy_url_path})


def schedule_post_deploy_hooks(build_id: str, deploy_url_path: str) -> None:
    asyncio.create_task(run_post_deploy_hooks(build_id, deploy_url_path))


async def probe_build_url(build: Build) -> dict:
    """GET deploy or cloud URL; return status code or error."""
    url = build.deploy_external_url
    if not url and build.deploy_url:
        url = f"http://127.0.0.1:8000{build.deploy_url}" if build.deploy_url.startswith("/") else build.deploy_url
    if not url:
        return {"ok": False, "error": "no_url"}
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            r = await client.get(url)
            return {"ok": r.status_code < 400, "status_code": r.status_code, "url": url}
    except Exception as e:
        return {"ok": False, "error": str(e), "url": url}
