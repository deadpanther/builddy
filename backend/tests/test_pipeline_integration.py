"""Integration tests for autopilot and test generation in the pipeline."""

from unittest.mock import AsyncMock, patch

import pytest


class TestAutopilotIntegration:
    """Tests for autopilot integration in pipeline."""

    def test_autopilot_module_imports(self):
        """Test that autopilot module can be imported."""
        from agent import autopilot
        assert autopilot is not None

    def test_autopilot_fix_loop_exists(self):
        """Test that autopilot_fix_loop function exists."""
        from agent.autopilot import autopilot_fix_loop
        assert callable(autopilot_fix_loop)

    @pytest.mark.asyncio
    async def test_autopilot_fix_loop_returns_tuple(self):
        """Test that autopilot_fix_loop returns a tuple of (code, iterations)."""
        from agent.autopilot import autopilot_fix_loop

        mock_validate_result = {
            "has_errors": False,
            "console_errors": [],
            "screenshot_base64": "base64data",
        }

        with patch('services.visual_validator.validate_html', new=AsyncMock(return_value=mock_validate_result)):
            code, iterations = await autopilot_fix_loop("<html><body>Test</body></html>")

        assert isinstance(code, str)
        assert isinstance(iterations, int)
        assert iterations >= 0

    @pytest.mark.asyncio
    async def test_autopilot_fix_loop_calls_callback(self):
        """Test that autopilot_fix_loop calls the callback on each iteration."""
        from agent.autopilot import autopilot_fix_loop

        mock_validate_result = {
            "has_errors": False,
            "console_errors": [],
            "screenshot_base64": "base64data",
        }

        callback_calls = []

        def on_iteration(iteration, errors, screenshot):
            callback_calls.append((iteration, errors, screenshot))

        with patch('services.visual_validator.validate_html', new=AsyncMock(return_value=mock_validate_result)):
            await autopilot_fix_loop("<html><body>Test</body></html>", on_iteration=on_iteration)

        # Should have at least one call
        assert len(callback_calls) >= 1


class TestTestGenIntegration:
    """Tests for test generation integration in pipeline."""

    def test_test_gen_module_imports(self):
        """Test that test_gen module can be imported."""
        from agent import test_gen
        assert test_gen is not None

    def test_generate_tests_exists(self):
        """Test that generate_tests function exists."""
        from agent.test_gen import generate_tests
        assert callable(generate_tests)

    @pytest.mark.asyncio
    async def test_generate_tests_returns_dict(self):
        """Test that generate_tests returns a dict of file paths to content."""
        from agent.test_gen import generate_tests

        mock_response = {
            "content": "```html\n<html><body>Test Suite</body></html>\n```",
            "reasoning": None,
        }

        with patch('agent.test_gen.chat_with_reasoning', new=AsyncMock(return_value=mock_response)):
            result = await generate_tests("<html><body>App</body></html>", app_name="TestApp")

        assert isinstance(result, dict)
        assert len(result) > 0
        # Should have at least one test file
        for path, content in result.items():
            assert isinstance(path, str)
            assert isinstance(content, str)


class TestPipelineAutopilotWiring:
    """Tests for autopilot wiring in the main pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_imports_autopilot(self):
        """Test that pipeline imports autopilot module."""
        from agent.pipeline import autopilot_fix_loop
        assert callable(autopilot_fix_loop)

    @pytest.mark.asyncio
    async def test_pipeline_imports_test_gen(self):
        """Test that pipeline imports test_gen module."""
        from agent.pipeline import generate_tests
        assert callable(generate_tests)


class TestDeployerTestFiles:
    """Tests for deploying test files."""

    def test_deploy_test_file_exists(self):
        """Test that deploy_test_file function exists."""
        from services.deployer import deploy_test_file
        assert callable(deploy_test_file)

    def test_deploy_test_file_returns_url(self, tmp_path):
        """Test that deploy_test_file deploys and returns URL."""

        from services.deployer import DEPLOYED_DIR, deploy_test_file

        # Create a temp deployed dir for testing
        original_dir = DEPLOYED_DIR

        try:
            # Use tmp_path as deployed dir
            import services.deployer
            services.deployer.DEPLOYED_DIR = tmp_path

            url = deploy_test_file("test-build-id", "tests.html", "<html><body>Tests</body></html>")

            assert url == "/apps/test-build-id/tests.html"
            assert (tmp_path / "test-build-id" / "tests.html").exists()
        finally:
            services.deployer.DEPLOYED_DIR = original_dir
