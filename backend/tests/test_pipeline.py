"""Tests for agent/pipeline.py."""



class TestPipelineModule:
    """Tests for pipeline module."""

    def test_module_imports(self):
        """Test that pipeline module can be imported."""
        from agent import pipeline
        assert pipeline is not None

    def test_run_pipeline_exists(self):
        """Test that run_pipeline function exists."""
        from agent.pipeline import run_pipeline
        assert callable(run_pipeline)

    def test_run_modify_pipeline_exists(self):
        """Test that run_modify_pipeline function exists."""
        from agent.pipeline import run_modify_pipeline
        assert callable(run_modify_pipeline)

    def test_run_retry_pipeline_exists(self):
        """Test that run_retry_pipeline function exists."""
        from agent.pipeline import run_retry_pipeline
        assert callable(run_retry_pipeline)


class TestPipelineConstants:
    """Tests for pipeline constants."""

    def test_module_has_functions(self):
        """Test that module has expected functions."""
        from agent import pipeline

        functions = [f for f in dir(pipeline) if not f.startswith('_')]
        assert len(functions) > 0


class TestPipelineImports:
    """Tests for pipeline imports."""

    def test_imports_helpers(self):
        """Test that pipeline imports helpers."""
        from agent.pipeline import _add_step, _update_build
        assert callable(_update_build)
        assert callable(_add_step)

    def test_imports_steps(self):
        """Test that pipeline imports steps."""
        from agent import pipeline
        # Check that step functions are available
        assert hasattr(pipeline, 'run_pipeline')
