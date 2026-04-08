"""Deployment service — save HTML files to deployed/ directory."""

import io
import logging
import zipfile
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


def deploy_project(build_id: str, files: dict[str, str]) -> str:
    """Write all project files to deployed/{build_id}/ and return the URL path.

    If the file tree contains ``frontend/index.html``, a copy is placed at the
    app root so the static-file mount serves it directly.
    """
    ensure_deployed_dir()
    app_dir = DEPLOYED_DIR / build_id
    app_dir.mkdir(parents=True, exist_ok=True)

    for relative_path, content in files.items():
        dest = app_dir / relative_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

    # Copy ALL frontend files to root so static serving matches Express behavior.
    # Express serves `express.static('frontend')` which maps frontend/login.html → /login.html.
    # We mirror this AND rewrite /api/ paths to include the app prefix.
    app_base = f"/apps/{build_id}"
    frontend_dir = app_dir / "frontend"
    if frontend_dir.is_dir():
        for file_path in frontend_dir.rglob("*"):
            if not file_path.is_file():
                continue
            relative = file_path.relative_to(frontend_dir)
            root_dest = app_dir / relative
            root_dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                content = file_path.read_text(encoding="utf-8")
                # Rewrite absolute /api/ calls to include the app base path
                # so fetch('/api/auth/login') becomes fetch('/apps/{id}/api/auth/login')
                content = content.replace("'/api/", f"'{app_base}/api/")
                content = content.replace('"/api/', f'"{app_base}/api/')
                content = content.replace("('/api/", f"('{app_base}/api/")
                content = content.replace('("/api/', f'("{app_base}/api/')
                # Also rewrite href/src references to other pages
                content = content.replace("href='/", f"href='{app_base}/")
                content = content.replace('href="/', f'href="{app_base}/')
                content = content.replace("href='/apps/", "href='/apps/")  # don't double-rewrite
                content = content.replace('href="/apps/', 'href="/apps/')  # don't double-rewrite
                root_dest.write_text(content, encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                # Binary file — copy as-is
                root_dest.write_bytes(file_path.read_bytes())

    url = f"/apps/{build_id}/"
    logger.info("Deployed project %s (%d files) to %s", build_id, len(files), url)
    return url


def create_project_zip(build_id: str, files: dict[str, str]) -> str:
    """Create a zip archive of all project files and return the URL path.

    Files inside the archive are stored under a root folder named after the
    first 8 characters of *build_id* (e.g. ``a1b2c3d4/backend/server.js``).
    """
    ensure_deployed_dir()
    app_dir = DEPLOYED_DIR / build_id
    app_dir.mkdir(parents=True, exist_ok=True)

    zip_path = app_dir / "project.zip"
    prefix = build_id[:8]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for relative_path, content in files.items():
            arcname = f"{prefix}/{relative_path}"
            zf.writestr(arcname, content)
    zip_path.write_bytes(buf.getvalue())

    url = f"/apps/{build_id}/project.zip"
    logger.info("Created project zip for %s at %s", build_id, url)
    return url


def get_project_files(build_id: str) -> dict[str, str] | None:
    """Read all deployed files for a build, returning {relative_path: content}.

    Excludes the generated zip archive and ``__pycache__`` directories.
    Returns ``None`` if the build directory does not exist.
    """
    app_dir = DEPLOYED_DIR / build_id
    if not app_dir.is_dir():
        return None

    result: dict[str, str] = {}
    for file_path in app_dir.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.name == "project.zip":
            continue
        if "__pycache__" in file_path.parts:
            continue
        relative = file_path.relative_to(app_dir).as_posix()
        try:
            result[relative] = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            # Skip binary or unreadable files
            logger.debug("Skipping non-text file %s", relative)
    return result
