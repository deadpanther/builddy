"""Deployment service — save HTML files to deployed/ directory."""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEPLOYED_DIR = Path(__file__).parent.parent / "deployed"


def ensure_deployed_dir():
    """Make sure the deployed directory exists."""
    DEPLOYED_DIR.mkdir(parents=True, exist_ok=True)


def deploy_html(build_id: str, html_code: str) -> str:
    """Save HTML to deployed/{build_id}/index.html and return the URL path."""
    ensure_deployed_dir()
    app_dir = DEPLOYED_DIR / build_id
    app_dir.mkdir(parents=True, exist_ok=True)

    file_path = app_dir / "index.html"
    file_path.write_text(html_code, encoding="utf-8")

    url = f"/apps/{build_id}/"
    logger.info("Deployed build %s to %s", build_id, url)
    return url


def get_deployed_html(build_id: str) -> str | None:
    """Read deployed HTML for a build."""
    file_path = DEPLOYED_DIR / build_id / "index.html"
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    return None
