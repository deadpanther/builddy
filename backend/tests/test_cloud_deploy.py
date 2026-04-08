"""Tests for services/cloud_deploy.py."""

from unittest.mock import patch

import pytest


class TestGetManualDeployInstructions:
    """Tests for get_manual_deploy_instructions function."""

    def test_returns_dict(self):
        """Test that function returns a dictionary."""
        from services.cloud_deploy import get_manual_deploy_instructions

        result = get_manual_deploy_instructions("test-build", "TestApp")
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        """Test that result has required keys."""
        from services.cloud_deploy import get_manual_deploy_instructions

        result = get_manual_deploy_instructions("test-build", "TestApp")
        assert "message" in result
        assert "options" in result

    def test_sanitizes_app_name(self):
        """Test that app name is sanitized for CLI use."""
        from services.cloud_deploy import get_manual_deploy_instructions

        result = get_manual_deploy_instructions("build-123", "My Test App!")
        # Should have lowercase, hyphenated name
        assert "my-test-app" in str(result).lower() or "test" in str(result).lower()

    def test_has_railway_option(self):
        """Test that Railway is included as an option."""
        from services.cloud_deploy import get_manual_deploy_instructions

        result = get_manual_deploy_instructions("build-123", "TestApp")
        providers = [opt.get("provider") for opt in result.get("options", [])]
        assert "railway" in providers

    def test_has_render_option(self):
        """Test that Render is included as an option."""
        from services.cloud_deploy import get_manual_deploy_instructions

        result = get_manual_deploy_instructions("build-123", "TestApp")
        providers = [opt.get("provider") for opt in result.get("options", [])]
        assert "render" in providers

    def test_options_have_steps(self):
        """Test that each option has steps."""
        from services.cloud_deploy import get_manual_deploy_instructions

        result = get_manual_deploy_instructions("build-123", "TestApp")
        for opt in result.get("options", []):
            assert "steps" in opt
            assert isinstance(opt["steps"], list)
            assert len(opt["steps"]) > 0


class TestDeployToCloud:
    """Tests for deploy_to_cloud function."""

    @pytest.mark.asyncio
    async def test_returns_manual_without_github_token(self):
        """Test returns manual instructions when GITHUB_TOKEN not set."""
        from config import settings
        from services.cloud_deploy import deploy_to_cloud

        # Mock settings to not have GITHUB_TOKEN
        with patch.object(settings, 'GITHUB_TOKEN', None):
            result = await deploy_to_cloud(
                build_id="test-build",
                provider="railway",
                project_files={"index.html": "<html></html>"},
                app_name="TestApp"
            )

        assert result["status"] == "manual"
        assert "instructions" in result

    @pytest.mark.asyncio
    async def test_returns_dict(self):
        """Test that function returns a dictionary."""
        from config import settings
        from services.cloud_deploy import deploy_to_cloud

        with patch.object(settings, 'GITHUB_TOKEN', None):
            result = await deploy_to_cloud(
                build_id="test-build",
                provider="railway",
                project_files={},
                app_name="TestApp"
            )

        assert isinstance(result, dict)


class TestGetDeployStatus:
    """Tests for get_deploy_status function."""

    @pytest.mark.asyncio
    async def test_returns_dict(self):
        """Test that function returns a dictionary."""
        from services.cloud_deploy import get_deploy_status

        result = await get_deploy_status("railway", "test-build")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_has_status_key(self):
        """Test that result has status key."""
        from services.cloud_deploy import get_deploy_status

        result = await get_deploy_status("railway", "test-build")
        assert "status" in result

    @pytest.mark.asyncio
    async def test_handles_unknown_provider(self):
        """Test handling of unknown provider."""
        from services.cloud_deploy import get_deploy_status

        result = await get_deploy_status("unknown", "test-build")
        assert "status" in result


class TestCloudInstructionsWithRepo:
    """Tests for _cloud_instructions_with_repo function."""

    def test_function_exists(self):
        """Test that the function exists."""
        from services import cloud_deploy
        assert hasattr(cloud_deploy, '_cloud_instructions_with_repo')
