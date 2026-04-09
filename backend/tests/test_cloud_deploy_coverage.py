"""Tests for services/cloud_deploy.py — cloud deployment functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDeployToCloud:
    @pytest.mark.asyncio
    async def test_deploy_no_github_token_returns_manual(self):
        """When GITHUB_TOKEN is missing, returns manual instructions."""
        with patch("services.cloud_deploy.settings") as mock_settings:
            mock_settings.GITHUB_TOKEN = None
            from services.cloud_deploy import deploy_to_cloud
            result = await deploy_to_cloud("build-123", "railway", {"index.html": "<h1>Hi</h1>"}, "my-app")

        assert result["status"] == "manual"
        assert "instructions" in result

    @pytest.mark.asyncio
    async def test_deploy_github_push_fails_returns_manual(self):
        """When GitHub push fails, falls back to manual instructions."""
        with (
            patch("services.cloud_deploy.settings") as mock_settings,
            patch("services.cloud_deploy._push_to_github", new=AsyncMock(side_effect=Exception("Push failed"))),
        ):
            mock_settings.GITHUB_TOKEN = "ghp_test123"
            from services.cloud_deploy import deploy_to_cloud
            result = await deploy_to_cloud("build-123", "railway", {"index.html": "<h1>Hi</h1>"}, "my-app")

        assert result["status"] == "manual"
        assert "GitHub push failed" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_deploy_railway_success(self):
        """Full deploy to Railway via GitHub repo + Railway API."""
        with (
            patch("services.cloud_deploy.settings") as mock_settings,
            patch("services.cloud_deploy._push_to_github", new=AsyncMock(return_value="https://github.com/user/repo")),
            patch("services.cloud_deploy._deploy_to_railway", new=AsyncMock(return_value={
                "status": "deployed",
                "url": "https://myapp.up.railway.app",
            })),
        ):
            mock_settings.GITHUB_TOKEN = "ghp_test123"
            mock_settings.RAILWAY_API_TOKEN = "railway-test-token"
            from services.cloud_deploy import deploy_to_cloud
            result = await deploy_to_cloud("build-123", "railway", {"index.html": "<h1>Hi</h1>"}, "my-app")

        assert result["status"] == "deployed"
        assert "url" in result
        assert result["repo_url"] == "https://github.com/user/repo"

    @pytest.mark.asyncio
    async def test_deploy_render_returns_ready(self):
        """Render without Render API token returns repo URL + instructions."""
        with (
            patch("services.cloud_deploy.settings") as mock_settings,
            patch("services.cloud_deploy._push_to_github", new=AsyncMock(return_value="https://github.com/user/repo")),
            patch("services.cloud_deploy._cloud_instructions_with_repo", return_value={"steps": ["Deploy to Render"]}),
        ):
            mock_settings.GITHUB_TOKEN = "ghp_test123"
            mock_settings.RAILWAY_API_TOKEN = None
            from services.cloud_deploy import deploy_to_cloud
            result = await deploy_to_cloud("build-123", "render", {"index.html": "<h1>Hi</h1>"}, "my-app")

        assert result["status"] == "ready"
        assert result["repo_url"] == "https://github.com/user/repo"


class TestGetDeployStatus:
    @pytest.mark.asyncio
    async def test_get_railway_status_deploying(self):
        with patch("services.cloud_deploy.settings") as mock_settings:
            mock_settings.RAILWAY_API_TOKEN = "test-token"
            from services.cloud_deploy import get_deploy_status
            result = await get_deploy_status("railway", "build-123")

        assert result["status"] == "deploying"

    @pytest.mark.asyncio
    async def test_get_status_no_provider_token(self):
        with patch("services.cloud_deploy.settings") as mock_settings:
            mock_settings.RAILWAY_API_TOKEN = None
            from services.cloud_deploy import get_deploy_status
            result = await get_deploy_status("railway", "build-123")

        assert result["status"] == "ready"

    @pytest.mark.asyncio
    async def test_get_status_unknown_provider(self):
        from services.cloud_deploy import get_deploy_status
        result = await get_deploy_status("unknown", "build-123")
        assert result["status"] == "ready"


class TestManualDeployInstructions:
    def test_manual_instructions_contains_options(self):
        with patch("services.cloud_deploy.settings") as mock_settings:
            mock_settings.GITHUB_TOKEN = None
            from services.cloud_deploy import get_manual_deploy_instructions
            result = get_manual_deploy_instructions("build-123", "my-app")

        assert isinstance(result, dict)
        assert "message" in result
