"""More tests for services/cloud_deploy.py."""

from unittest.mock import patch

import pytest


class TestCloudDeployModule:
    """Tests for cloud_deploy module."""

    def test_module_imports(self):
        """Test that cloud_deploy module can be imported."""
        from services import cloud_deploy
        assert cloud_deploy is not None

    def test_deploy_to_cloud_exists(self):
        """Test that deploy_to_cloud function exists."""
        from services.cloud_deploy import deploy_to_cloud
        assert callable(deploy_to_cloud)

    def test_get_deploy_status_exists(self):
        """Test that get_deploy_status function exists."""
        from services.cloud_deploy import get_deploy_status
        assert callable(get_deploy_status)

    def test_get_manual_deploy_instructions_exists(self):
        """Test that get_manual_deploy_instructions function exists."""
        from services.cloud_deploy import get_manual_deploy_instructions
        assert callable(get_manual_deploy_instructions)


class TestDeployToCloud:
    """Tests for deploy_to_cloud function."""

    @pytest.mark.asyncio
    async def test_deploy_to_cloud_returns_dict(self):
        """Test that deploy_to_cloud returns a dict."""
        from services.cloud_deploy import deploy_to_cloud

        # Mock settings to have no GitHub token (will return manual instructions)
        with patch('services.cloud_deploy.settings') as mock_settings:
            mock_settings.GITHUB_TOKEN = None
            result = await deploy_to_cloud(
                build_id="test-build-id",
                provider="railway",
                project_files={"index.html": "<html></html>"},
                app_name="TestApp"
            )

        assert isinstance(result, dict)
        assert result["status"] == "manual"


class TestGetDeployStatus:
    """Tests for get_deploy_status function."""

    @pytest.mark.asyncio
    async def test_get_deploy_status_returns_dict(self):
        """Test that get_deploy_status returns a dict."""
        from services.cloud_deploy import get_deploy_status

        result = await get_deploy_status(provider="railway", build_id="test-build-id")

        assert isinstance(result, dict)
        assert "status" in result


class TestGetManualDeployInstructions:
    """Tests for get_manual_deploy_instructions function."""

    def test_get_manual_instructions_returns_dict(self):
        """Test that get_manual_instructions returns a dict."""
        from services.cloud_deploy import get_manual_deploy_instructions

        result = get_manual_deploy_instructions("test-build-id", "TestApp")

        assert isinstance(result, dict)
        assert "instructions" in result or "steps" in result or "message" in result


class TestPushToGithub:
    """Tests for _push_to_github function."""

    @pytest.mark.asyncio
    async def test_push_to_github_exists(self):
        """Test that _push_to_github function exists."""
        from services.cloud_deploy import _push_to_github
        assert callable(_push_to_github)


class TestDeployToRailway:
    """Tests for _deploy_to_railway function."""

    @pytest.mark.asyncio
    async def test_deploy_to_railway_exists(self):
        """Test that _deploy_to_railway function exists."""
        from services.cloud_deploy import _deploy_to_railway
        assert callable(_deploy_to_railway)
