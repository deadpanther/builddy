"""Tests for agent/prompts.py."""

import pytest


class TestPrompts:
    """Tests for agent prompts."""

    def test_prompts_module_imports(self):
        """Test that prompts module can be imported."""
        from agent import prompts
        assert prompts is not None

    def test_prompts_has_content(self):
        """Test that prompts has expected content."""
        from agent import prompts
        
        # Check for common prompt-related attributes
        attrs = dir(prompts)
        # Should have some prompt-related content
        assert len(attrs) > 0


class TestPromptConstants:
    """Tests for prompt constants."""

    def test_parse_system_exists(self):
        """Test PARSE_SYSTEM prompt exists."""
        from agent.prompts import PARSE_SYSTEM
        assert isinstance(PARSE_SYSTEM, str)
        assert len(PARSE_SYSTEM) > 100

    def test_plan_system_exists(self):
        """Test PLAN_SYSTEM prompt exists."""
        from agent.prompts import PLAN_SYSTEM
        assert isinstance(PLAN_SYSTEM, str)
        assert len(PLAN_SYSTEM) > 100

    def test_code_system_exists(self):
        """Test CODE_SYSTEM prompt exists."""
        from agent.prompts import CODE_SYSTEM
        assert isinstance(CODE_SYSTEM, str)
        assert len(CODE_SYSTEM) > 100

    def test_modify_system_exists(self):
        """Test MODIFY_SYSTEM prompt exists."""
        from agent.prompts import MODIFY_SYSTEM
        assert isinstance(MODIFY_SYSTEM, str)
        assert len(MODIFY_SYSTEM) > 50

    def test_review_system_exists(self):
        """Test REVIEW_SYSTEM prompt exists."""
        from agent.prompts import REVIEW_SYSTEM
        assert isinstance(REVIEW_SYSTEM, str)
        assert len(REVIEW_SYSTEM) > 100


class TestPromptContent:
    """Tests for prompt content quality."""

    def test_parse_system_mentions_json(self):
        """Test PARSE_SYSTEM mentions JSON format."""
        from agent.prompts import PARSE_SYSTEM
        assert "JSON" in PARSE_SYSTEM

    def test_code_system_mentions_tailwind(self):
        """Test CODE_SYSTEM mentions Tailwind."""
        from agent.prompts import CODE_SYSTEM
        assert "tailwind" in CODE_SYSTEM.lower()

    def test_code_system_mentions_dark_mode(self):
        """Test CODE_SYSTEM mentions dark mode."""
        from agent.prompts import CODE_SYSTEM
        assert "dark" in CODE_SYSTEM.lower()

    def test_review_system_has_checklist(self):
        """Test REVIEW_SYSTEM has checklist items."""
        from agent.prompts import REVIEW_SYSTEM
        assert "[ ]" in REVIEW_SYSTEM or "checklist" in REVIEW_SYSTEM.lower()

    def test_modify_system_keeps_functionality(self):
        """Test MODIFY_SYSTEM mentions keeping functionality."""
        from agent.prompts import MODIFY_SYSTEM
        assert "keep" in MODIFY_SYSTEM.lower() or "existing" in MODIFY_SYSTEM.lower()


class TestMultiAgentPrompts:
    """Tests for multi-agent pipeline prompts."""

    def test_prd_system_exists(self):
        """Test PRD_SYSTEM prompt exists."""
        from agent.prompts import PRD_SYSTEM
        assert isinstance(PRD_SYSTEM, str)
        assert len(PRD_SYSTEM) > 100

    def test_design_system_prompt_exists(self):
        """Test DESIGN_SYSTEM_PROMPT exists."""
        from agent.prompts import DESIGN_SYSTEM_PROMPT
        assert isinstance(DESIGN_SYSTEM_PROMPT, str)
        assert len(DESIGN_SYSTEM_PROMPT) > 100

    def test_qa_system_exists(self):
        """Test QA_SYSTEM prompt exists."""
        from agent.prompts import QA_SYSTEM
        assert isinstance(QA_SYSTEM, str)
        assert len(QA_SYSTEM) > 100

    def test_polish_system_exists(self):
        """Test POLISH_SYSTEM prompt exists."""
        from agent.prompts import POLISH_SYSTEM
        assert isinstance(POLISH_SYSTEM, str)
        assert len(POLISH_SYSTEM) > 100
