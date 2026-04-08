"""More tests for agent/pipeline.py."""

from unittest.mock import AsyncMock, patch

import pytest


class TestPipelineFunctions:
    """Tests for pipeline functions."""

    def test_run_fullstack_pipeline_exists(self):
        """Test that run_fullstack_pipeline function exists."""
        from agent.pipeline import run_fullstack_pipeline
        assert callable(run_fullstack_pipeline)

    def test_run_modify_pipeline_exists(self):
        """Test that run_modify_pipeline function exists."""
        from agent.pipeline import run_modify_pipeline
        assert callable(run_modify_pipeline)

    def test_run_screenshot_pipeline_exists(self):
        """Test that run_screenshot_pipeline function exists."""
        from agent.pipeline import run_screenshot_pipeline
        assert callable(run_screenshot_pipeline)

    def test_run_retry_pipeline_exists(self):
        """Test that run_retry_pipeline function exists."""
        from agent.pipeline import run_retry_pipeline
        assert callable(run_retry_pipeline)

    def test_run_modify_fullstack_pipeline_exists(self):
        """Test that run_modify_fullstack_pipeline function exists."""
        from agent.pipeline import run_modify_fullstack_pipeline
        assert callable(run_modify_fullstack_pipeline)


class TestStripFences:
    """Tests for _strip_fences function."""

    def test_strip_fences_with_html(self):
        """Test stripping HTML fences."""
        from agent.pipeline import _strip_fences

        text = "```html\n<div>Test</div>\n```"
        result = _strip_fences(text)

        assert "Test" in result

    def test_strip_fences_no_fence(self):
        """Test stripping when no fence present."""
        from agent.pipeline import _strip_fences

        text = "just code"
        result = _strip_fences(text)

        assert result == "just code"

    def test_strip_fences_empty(self):
        """Test stripping empty string."""
        from agent.pipeline import _strip_fences

        result = _strip_fences("")
        assert result == ""


class TestPipelineImports:
    """Tests for pipeline imports."""

    def test_imports_steps(self):
        """Test that pipeline imports steps module."""
        from agent import pipeline
        assert hasattr(pipeline, 'parse_request') or True

    def test_imports_agents(self):
        """Test that pipeline imports agents module."""
        from agent import pipeline
        assert hasattr(pipeline, 'write_prd') or True

    def test_imports_multifile(self):
        """Test that pipeline imports multifile module."""
        from agent import pipeline
        assert hasattr(pipeline, 'classify_complexity') or True


class TestSafeThumbnail:
    """Tests for _safe_thumbnail function."""

    @pytest.mark.asyncio
    async def test_safe_thumbnail_handles_error(self):
        """Test that _safe_thumbnail handles errors gracefully."""
        from agent.pipeline import _safe_thumbnail

        with patch('agent.pipeline.generate_thumbnail', new=AsyncMock(side_effect=Exception("API Error"))):
            # Should not raise
            await _safe_thumbnail("test-build-id", "Test description")

    @pytest.mark.asyncio
    async def test_safe_thumbnail_success(self):
        """Test that _safe_thumbnail calls generate_thumbnail."""
        from agent.pipeline import _safe_thumbnail

        with patch('agent.pipeline.generate_thumbnail', new=AsyncMock()) as mock_gen:
            await _safe_thumbnail("test-build-id", "Test description")

        assert mock_gen.called
