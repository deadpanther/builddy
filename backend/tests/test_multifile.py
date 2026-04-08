"""Tests for agent/multifile.py."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestMultifileModule:
    """Tests for multifile module."""

    def test_module_imports(self):
        """Test that multifile module can be imported."""
        from agent import multifile
        assert multifile is not None

    def test_classify_complexity_exists(self):
        """Test that classify_complexity function exists."""
        from agent.multifile import classify_complexity
        assert callable(classify_complexity)

    def test_plan_manifest_exists(self):
        """Test that plan_manifest function exists."""
        from agent.multifile import plan_manifest
        assert callable(plan_manifest)

    def test_generate_file_exists(self):
        """Test that generate_file function exists."""
        from agent.multifile import generate_file
        assert callable(generate_file)

    def test_generate_all_files_exists(self):
        """Test that generate_all_files function exists."""
        from agent.multifile import generate_all_files
        assert callable(generate_all_files)

    def test_integration_review_exists(self):
        """Test that integration_review function exists."""
        from agent.multifile import integration_review
        assert callable(integration_review)

    def test_generate_seed_data_exists(self):
        """Test that generate_seed_data function exists."""
        from agent.multifile import generate_seed_data
        assert callable(generate_seed_data)

    def test_generate_deployment_files_exists(self):
        """Test that generate_deployment_files function exists."""
        from agent.multifile import generate_deployment_files
        assert callable(generate_deployment_files)

    def test_analyze_impact_exists(self):
        """Test that analyze_impact function exists."""
        from agent.multifile import analyze_impact
        assert callable(analyze_impact)

    def test_modify_existing_file_exists(self):
        """Test that modify_existing_file function exists."""
        from agent.multifile import modify_existing_file
        assert callable(modify_existing_file)


class TestClassifyComplexity:
    """Tests for classify_complexity function."""

    @pytest.mark.asyncio
    async def test_classify_complexity_returns_dict(self):
        """Test that classify_complexity returns a dict."""
        from agent.multifile import classify_complexity
        
        mock_response = {
            "content": '{"complexity": "simple", "reason": "Single page app"}',
            "reasoning": None,
        }
        
        with patch('agent.multifile.chat_with_reasoning', new=AsyncMock(return_value=mock_response)):
            with patch('agent.multifile._add_step'):
                result = await classify_complexity("test-build-id", "Build a simple timer")
        
        assert isinstance(result, dict)
        assert "complexity" in result


class TestPlanManifest:
    """Tests for plan_manifest function."""

    @pytest.mark.asyncio
    async def test_plan_manifest_returns_dict(self):
        """Test that plan_manifest returns a dict."""
        from agent.multifile import plan_manifest
        
        mock_response = {
            "content": '{"files": [], "tech_stack": {}}',
            "reasoning": None,
        }
        
        with patch('agent.multifile.chat_with_reasoning', new=AsyncMock(return_value=mock_response)):
            with patch('agent.multifile._add_step'):
                result = await plan_manifest("test-build-id", "Build a todo app", {"complexity": "standard"})
        
        assert isinstance(result, dict)


class TestGenerateDeploymentFiles:
    """Tests for generate_deployment_files function."""

    def test_generate_deployment_files_returns_dict(self):
        """Test that generate_deployment_files returns a dict."""
        from agent.multifile import generate_deployment_files
        
        manifest = {
            "app_name": "TestApp",
            "tech_stack": {"frontend": "react", "backend": "node"},
        }
        all_files = {"frontend/index.html": "<html></html>"}
        
        result = generate_deployment_files(manifest, all_files)
        
        assert isinstance(result, dict)
        # Should add Dockerfile and other deployment files
        assert len(result) > len(all_files)


class TestExtractInterface:
    """Tests for _extract_interface function."""

    def test_extract_interface_exists(self):
        """Test that _extract_interface function exists."""
        from agent.multifile import _extract_interface
        assert callable(_extract_interface)

    def test_extract_interface_shortens_content(self):
        """Test that _extract_interface shortens long content."""
        from agent.multifile import _extract_interface
        
        long_content = "line1\n" * 100
        result = _extract_interface(long_content, max_lines=10)
        
        # Should be shorter than original
        assert len(result) < len(long_content)
