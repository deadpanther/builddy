"""Cloud deployment service -- deploy Builddy projects to Railway and Render."""

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import httpx

from config import settings

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


async def export_build_files_to_github(
    build_id: str,
    project_files: dict[str, str],
    app_name: str,
) -> str:
    """Push files to a new GitHub repository; returns the repo HTTPS URL."""
    return await _push_to_github(build_id, project_files, app_name)


async def deploy_to_cloud(
    build_id: str,
    provider: str,
    project_files: dict[str, str],
    app_name: str,
) -> dict:
    """Deploy project files to a cloud provider.

    If GitHub + Railway/Render tokens are configured, creates a GitHub repo
    and triggers deployment.  Otherwise returns manual instructions.
    """
    if not settings.GITHUB_TOKEN:
        instructions = get_manual_deploy_instructions(build_id, app_name)
        return {
            "status": "manual",
            "url": None,
            "instructions": instructions,
        }

    try:
        repo_url = await _push_to_github(build_id, project_files, app_name)
    except Exception as exc:
        logger.exception("Failed to push to GitHub for build %s: %s", build_id, exc)
        return {
            "status": "manual",
            "url": None,
            "instructions": get_manual_deploy_instructions(build_id, app_name),
            "error": f"GitHub push failed: {exc}",
        }

    if provider == "railway" and settings.RAILWAY_API_TOKEN:
        result = await _deploy_to_railway(repo_url, app_name)
        return {**result, "repo_url": repo_url}

    # For Render or when provider token is missing, return repo URL + instructions
    return {
        "status": "ready",
        "url": repo_url,
        "repo_url": repo_url,
        "instructions": _cloud_instructions_with_repo(provider, repo_url, app_name),
    }


async def get_deploy_status(provider: str, build_id: str) -> dict:
    """Check deploy status with the provider.

    Currently returns the stored status since full polling requires
    provider-specific project IDs stored separately.
    """
    if provider == "railway" and settings.RAILWAY_API_TOKEN:
        # Railway GraphQL status check would go here with a project_id lookup
        return {"status": "deploying", "url": None}

    return {"status": "ready", "url": None}


def get_manual_deploy_instructions(build_id: str, app_name: str) -> dict:
    """Return instructions for manual deployment when API tokens are not configured."""
    safe_name = app_name.replace(" ", "-").lower()[:40]
    return {
        "message": "API tokens not configured. Deploy manually using one of these options:",
        "download_first": "Download the project zip, then use one of the commands below.",
        "options": [
            {
                "provider": "railway",
                "name": "Railway",
                "steps": [
                    "Install Railway CLI: npm install -g @railway/cli",
                    "Login: railway login",
                    f"Initialize: railway init --name {safe_name}",
                    "Deploy: railway up",
                ],
                "one_liner": f"npm i -g @railway/cli && railway login && railway init --name {safe_name} && railway up",
                "docs_url": "https://docs.railway.app/quick-start",
            },
            {
                "provider": "render",
                "name": "Render",
                "steps": [
                    "Push the project to a GitHub repo",
                    "Go to https://dashboard.render.com/new/static",
                    "Connect the GitHub repo",
                    "Set build command (if needed) and publish directory",
                    "Click 'Create Static Site'",
                ],
                "one_liner": None,
                "docs_url": "https://docs.render.com/static-sites",
            },
            {
                "provider": "fly",
                "name": "Fly.io",
                "steps": [
                    "Install Fly CLI: curl -L https://fly.io/install.sh | sh",
                    "Login: fly auth login",
                    f"Launch: fly launch --name {safe_name}",
                    "Deploy: fly deploy",
                ],
                "one_liner": f"curl -L https://fly.io/install.sh | sh && fly auth login && fly launch --name {safe_name} && fly deploy",
                "docs_url": "https://fly.io/docs/getting-started/",
            },
        ],
    }


# ── Internal helpers ────────────────────────────────────────────────────────


async def _push_to_github(
    build_id: str,
    project_files: dict[str, str],
    app_name: str,
) -> str:
    """Create a GitHub repo and push project files. Returns the repo URL."""
    safe_name = f"{app_name}-{build_id[:8]}"
    headers = {
        "Authorization": f"token {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Determine if we create under an org or the authenticated user
    org = settings.GITHUB_ORG
    if org:
        create_url = f"{GITHUB_API}/orgs/{org}/repos"
    else:
        create_url = f"{GITHUB_API}/user/repos"

    async with httpx.AsyncClient(timeout=30) as client:
        # Create the repo
        resp = await client.post(
            create_url,
            headers=headers,
            json={
                "name": safe_name,
                "description": f"Builddy app: {app_name}",
                "private": False,
                "auto_init": False,
            },
        )

        if resp.status_code == 422:
            # Repo may already exist -- try to use it
            logger.info("Repo %s may already exist, continuing", safe_name)
        elif resp.status_code >= 400:
            raise RuntimeError(
                f"GitHub repo creation failed ({resp.status_code}): {resp.text}"
            )

        if org:
            repo_url = f"https://github.com/{org}/{safe_name}"
            clone_url = f"https://x-access-token:{settings.GITHUB_TOKEN}@github.com/{org}/{safe_name}.git"
        else:
            # Fetch authenticated user name
            user_resp = await client.get(
                f"{GITHUB_API}/user", headers=headers
            )
            username = user_resp.json().get("login", "builddy")
            repo_url = f"https://github.com/{username}/{safe_name}"
            clone_url = f"https://x-access-token:{settings.GITHUB_TOKEN}@github.com/{username}/{safe_name}.git"

    # Write files to a temp dir, init git, push
    await _git_push_files(clone_url, project_files, app_name)

    return repo_url


async def _git_push_files(
    clone_url: str,
    project_files: dict[str, str],
    app_name: str,
) -> None:
    """Write project files to a temp directory and push to the remote."""
    tmp_dir = tempfile.mkdtemp(prefix="builddy-deploy-")
    try:
        # Write all project files
        for filepath, content in project_files.items():
            full_path = Path(tmp_dir) / filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

        # Git init + commit + push
        cmds = [
            ["git", "init"],
            ["git", "checkout", "-b", "main"],
            ["git", "add", "."],
            ["git", "commit", "-m", f"Initial deploy: {app_name}"],
            ["git", "remote", "add", "origin", clone_url],
            ["git", "push", "-u", "origin", "main", "--force"],
        ]

        loop = asyncio.get_event_loop()
        for cmd in cmds:
            await loop.run_in_executor(
                None,
                lambda c=cmd: subprocess.run(
                    c,
                    cwd=tmp_dir,
                    capture_output=True,
                    text=True,
                    check=True,
                    env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                ),
            )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def _deploy_to_railway(repo_url: str, app_name: str) -> dict:
    """Create a Railway project from a GitHub repo via their GraphQL API."""
    headers = {
        "Authorization": f"Bearer {settings.RAILWAY_API_TOKEN}",
        "Content-Type": "application/json",
    }

    # Create a project
    create_mutation = """
    mutation($name: String!, $repo: String!) {
        projectCreate(input: {
            name: $name
            plugins: []
            defaultEnvironmentName: "production"
        }) {
            id
            name
        }
    }
    """

    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: Create project
        resp = await client.post(
            "https://backboard.railway.app/graphql/v2",
            headers=headers,
            json={
                "query": create_mutation,
                "variables": {"name": app_name, "repo": repo_url},
            },
        )

        if resp.status_code >= 400:
            logger.warning("Railway project creation failed: %s", resp.text)
            return {
                "status": "ready",
                "url": repo_url,
                "instructions": _cloud_instructions_with_repo("railway", repo_url, app_name),
            }

        data = resp.json()
        project_data = data.get("data", {}).get("projectCreate", {})
        project_id = project_data.get("id", "")

        return {
            "status": "deploying",
            "url": f"https://{app_name}.up.railway.app",
            "project_id": project_id,
        }


def _cloud_instructions_with_repo(
    provider: str, repo_url: str, app_name: str
) -> dict:
    """Return deploy instructions when a GitHub repo is available."""
    safe_name = app_name.replace(" ", "-").lower()[:40]

    if provider == "railway":
        return {
            "message": "GitHub repo created. Connect it to Railway to deploy.",
            "repo_url": repo_url,
            "steps": [
                f"Go to https://railway.app/new/github and connect {repo_url}",
                "Railway will auto-detect and deploy your project",
                "Your app will be live at a .up.railway.app URL",
            ],
            "docs_url": "https://docs.railway.app/quick-start",
        }

    if provider == "render":
        return {
            "message": "GitHub repo created. Connect it to Render to deploy.",
            "repo_url": repo_url,
            "steps": [
                "Go to https://dashboard.render.com/new/static",
                f"Connect the repo: {repo_url}",
                "Set publish directory to '.' (or 'frontend' if full-stack)",
                "Click 'Create Static Site'",
            ],
            "docs_url": "https://docs.render.com/static-sites",
        }

    return {
        "message": f"GitHub repo created at {repo_url}. Deploy manually.",
        "repo_url": repo_url,
    }


async def export_build_files_to_github_pr(
    build_id: str,
    project_files: dict[str, str],
    app_name: str,
) -> dict[str, str]:
    """Create repo with README, push files on a feature branch, open a PR to the default branch."""
    safe_name = f"{app_name}-{build_id[:8]}"
    headers = {
        "Authorization": f"token {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    org = settings.GITHUB_ORG
    if org:
        create_url = f"{GITHUB_API}/orgs/{org}/repos"
        owner = org
    else:
        create_url = f"{GITHUB_API}/user/repos"
        owner = ""

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            create_url,
            headers=headers,
            json={
                "name": safe_name,
                "description": f"Builddy app: {app_name}",
                "private": False,
                "auto_init": True,
            },
        )
        if resp.status_code >= 400 and resp.status_code != 422:
            raise RuntimeError(f"GitHub repo creation failed ({resp.status_code}): {resp.text}")

        if not org:
            user_resp = await client.get(f"{GITHUB_API}/user", headers=headers)
            owner = user_resp.json().get("login", "builddy")

        repo_url = f"https://github.com/{owner}/{safe_name}"
        clone_url = f"https://x-access-token:{settings.GITHUB_TOKEN}@github.com/{owner}/{safe_name}.git"

        info = await client.get(f"{GITHUB_API}/repos/{owner}/{safe_name}", headers=headers)
        if info.status_code >= 400:
            raise RuntimeError(f"Could not read repo metadata: {info.text}")
        default_branch = info.json().get("default_branch") or "main"

    branch_name = f"builddy-export-{build_id[:8]}"
    await _git_clone_push_branch(clone_url, project_files, app_name, branch_name)

    async with httpx.AsyncClient(timeout=30) as client:
        pr_resp = await client.post(
            f"{GITHUB_API}/repos/{owner}/{safe_name}/pulls",
            headers=headers,
            json={
                "title": f"Builddy export: {app_name}",
                "head": branch_name,
                "base": default_branch,
                "body": f"Automated export from build `{build_id}`.",
            },
        )
        if pr_resp.status_code >= 400:
            raise RuntimeError(f"GitHub PR creation failed ({pr_resp.status_code}): {pr_resp.text}")
        pr_data = pr_resp.json()

    return {
        "repo_url": repo_url,
        "pr_url": pr_data.get("html_url", ""),
        "pr_number": str(pr_data.get("number", "")),
    }


async def _git_clone_push_branch(
    clone_url: str,
    project_files: dict[str, str],
    app_name: str,
    branch_name: str,
) -> None:
    tmp_dir = tempfile.mkdtemp(prefix="builddy-pr-")
    try:
        loop = asyncio.get_event_loop()

        def _run(cmd: list[str]) -> None:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            )

        await loop.run_in_executor(
            None,
            lambda: _run(["git", "clone", "--depth", "1", clone_url, tmp_dir]),
        )

        for filepath, content in project_files.items():
            full_path = Path(tmp_dir) / filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

        cmds = [
            ["git", "-C", tmp_dir, "checkout", "-b", branch_name],
            ["git", "-C", tmp_dir, "add", "-A"],
            ["git", "-C", tmp_dir, "commit", "-m", f"Export app files: {app_name}"],
            ["git", "-C", tmp_dir, "push", "-u", "origin", branch_name],
        ]
        for cmd in cmds:
            await loop.run_in_executor(None, lambda c=cmd: _run(c))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
