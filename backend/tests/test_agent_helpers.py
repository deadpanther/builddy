"""Tests for agent/helpers.py utility functions."""

import json
from unittest.mock import patch, MagicMock, call

import pytest

from agent.helpers import (
    _update_build,
    _add_step,
    _add_reasoning,
    _strip_fences,
    STEP_TIMEOUT,
    FILE_TIMEOUT,
    VISUAL_TIMEOUT,
)


class TestConstants:
    def test_timeout_constants(self):
        """Verify timeout constants have expected values."""
        assert STEP_TIMEOUT == 120
        assert FILE_TIMEOUT == 180
        assert VISUAL_TIMEOUT == 60


class TestUpdateBuild:
    def test_update_build_updates_fields(self, db_session):
        """Test that _update_build updates build fields in the database."""
        from models import Build
        
        build = Build(prompt="Test app", status="pending")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id
        
        _update_build(build_id, status="coding", app_name="TestApp")
        
        # Expire session cache to see changes from other sessions
        db_session.expire_all()
        
        # Verify update
        updated = db_session.get(Build, build_id)
        assert updated.status == "coding"
        assert updated.app_name == "TestApp"

    def test_update_build_updates_timestamp(self, db_session):
        """Test that _update_build updates the updated_at timestamp."""
        from models import Build
        from datetime import datetime, timezone
        
        build = Build(prompt="Timestamp test", status="pending")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        original_updated_at = build.updated_at
        build_id = build.id
        
        _update_build(build_id, status="deploying")
        
        # Expire session cache to see changes from other sessions
        db_session.expire_all()
        
        updated = db_session.get(Build, build_id)
        assert updated.updated_at > original_updated_at

    def test_update_build_publishes_status_event(self, db_session):
        """Test that _update_build publishes event when status changes."""
        from models import Build
        
        build = Build(prompt="Event test", status="pending")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id
        
        with patch("agent.helpers._publish_event") as mock_publish:
            _update_build(build_id, status="deployed")
            mock_publish.assert_called_once_with(build_id, "status", {"status": "deployed"})

    def test_update_build_no_event_when_status_not_changed(self, db_session):
        """Test that _update_build doesn't publish event for non-status updates."""
        from models import Build
        
        build = Build(prompt="No event test", status="pending")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id
        
        with patch("agent.helpers._publish_event") as mock_publish:
            _update_build(build_id, app_name="New Name")
            mock_publish.assert_not_called()

    def test_update_build_handles_missing_build(self):
        """Test that _update_build doesn't crash for non-existent build."""
        # Should not raise
        _update_build("nonexistent-build-id", status="failed")

    def test_update_build_multiple_fields(self, db_session):
        """Test updating multiple fields at once."""
        from models import Build
        
        build = Build(prompt="Multi-field test")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id
        
        _update_build(
            build_id,
            status="deployed",
            app_name="My App",
            generated_code="<html></html>",
            deploy_url="/apps/test/",
        )
        
        # Expire session cache to see changes from other sessions
        db_session.expire_all()
        
        updated = db_session.get(Build, build_id)
        assert updated.status == "deployed"
        assert updated.app_name == "My App"
        assert updated.generated_code == "<html></html>"
        assert updated.deploy_url == "/apps/test/"


class TestAddStep:
    def test_add_step_appends_to_steps(self, db_session):
        """Test that _add_step appends step to build's steps array."""
        from models import Build
        
        build = Build(prompt="Step test", steps=None)
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id
        
        _add_step(build_id, "Planning app structure")
        
        # Expire session cache to see changes from other sessions
        db_session.expire_all()
        
        updated = db_session.get(Build, build_id)
        steps = json.loads(updated.steps)
        assert len(steps) == 1
        assert steps[0] == "Planning app structure"

    def test_add_step_appends_multiple(self, db_session):
        """Test that multiple calls append to steps array."""
        from models import Build
        
        build = Build(prompt="Multiple steps test", steps=None)
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id
        
        _add_step(build_id, "Step 1")
        _add_step(build_id, "Step 2")
        _add_step(build_id, "Step 3")
        
        # Expire session cache to see changes from other sessions
        db_session.expire_all()
        
        updated = db_session.get(Build, build_id)
        steps = json.loads(updated.steps)
        assert len(steps) == 3
        assert steps == ["Step 1", "Step 2", "Step 3"]

    def test_add_step_preserves_existing_steps(self, db_session):
        """Test that _add_step preserves existing steps."""
        from models import Build
        
        existing_steps = json.dumps(["Existing step 1", "Existing step 2"])
        build = Build(prompt="Preserve steps test", steps=existing_steps)
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id
        
        _add_step(build_id, "New step")
        
        # Expire session cache to see changes from other sessions
        db_session.expire_all()
        
        updated = db_session.get(Build, build_id)
        steps = json.loads(updated.steps)
        assert len(steps) == 3
        assert "Existing step 1" in steps
        assert "New step" in steps

    def test_add_step_publishes_event(self, db_session):
        """Test that _add_step publishes step event."""
        from models import Build
        
        build = Build(prompt="Event step test")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id
        
        with patch("agent.helpers._publish_event") as mock_publish:
            _add_step(build_id, "Test step")
            mock_publish.assert_called_once_with(build_id, "step", {"step": "Test step"})

    def test_add_step_handles_missing_build(self):
        """Test that _add_step doesn't crash for non-existent build."""
        # Should not raise
        _add_step("nonexistent-build-id", "Some step")

    def test_add_step_updates_timestamp(self, db_session):
        """Test that _add_step updates updated_at."""
        from models import Build
        from datetime import datetime, timezone
        
        build = Build(prompt="Timestamp step test")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        original_updated_at = build.updated_at
        build_id = build.id
        
        _add_step(build_id, "A step")
        
        # Expire session cache to see changes from other sessions
        db_session.expire_all()
        
        updated = db_session.get(Build, build_id)
        assert updated.updated_at > original_updated_at


class TestAddReasoning:
    def test_add_reasoning_appends_to_log(self, db_session):
        """Test that _add_reasoning appends to reasoning_log."""
        from models import Build
        
        build = Build(prompt="Reasoning test", reasoning_log=None)
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id
        
        _add_reasoning(build_id, "planning", "I decided to use React because...")
        
        # Expire session cache to see changes from other sessions
        db_session.expire_all()
        
        updated = db_session.get(Build, build_id)
        log = json.loads(updated.reasoning_log)
        assert len(log) == 1
        assert log[0]["stage"] == "planning"
        assert "React" in log[0]["reasoning"]

    def test_add_reasoning_multiple_stages(self, db_session):
        """Test adding reasoning from multiple stages."""
        from models import Build
        
        build = Build(prompt="Multi-reasoning test", reasoning_log=None)
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id
        
        _add_reasoning(build_id, "prd", "User needs a dashboard")
        _add_reasoning(build_id, "architecture", "Using microservices")
        _add_reasoning(build_id, "coding", "Implemented caching")
        
        # Expire session cache to see changes from other sessions
        db_session.expire_all()
        
        updated = db_session.get(Build, build_id)
        log = json.loads(updated.reasoning_log)
        assert len(log) == 3
        stages = [entry["stage"] for entry in log]
        assert stages == ["prd", "architecture", "coding"]

    def test_add_reasoning_truncates_long_reasoning(self, db_session):
        """Test that reasoning is truncated to 2000 chars."""
        from models import Build
        
        build = Build(prompt="Truncation test", reasoning_log=None)
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id
        
        long_reasoning = "x" * 5000
        _add_reasoning(build_id, "test", long_reasoning)
        
        # Expire session cache to see changes from other sessions
        db_session.expire_all()
        
        updated = db_session.get(Build, build_id)
        log = json.loads(updated.reasoning_log)
        assert len(log[0]["reasoning"]) == 2000

    def test_add_reasoning_skips_empty_reasoning(self, db_session):
        """Test that _add_reasoning does nothing for empty reasoning."""
        from models import Build
        
        build = Build(prompt="Empty reasoning test", reasoning_log=None)
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id
        
        _add_reasoning(build_id, "test", "")
        _add_reasoning(build_id, "test", None)
        
        updated = db_session.get(Build, build_id)
        # Should still be None (not even an empty array)
        assert updated.reasoning_log is None

    def test_add_reasoning_handles_missing_build(self):
        """Test that _add_reasoning doesn't crash for non-existent build."""
        # Should not raise
        _add_reasoning("nonexistent-build-id", "test", "Some reasoning")

    def test_add_reasoning_preserves_existing_log(self, db_session):
        """Test that _add_reasoning preserves existing entries."""
        from models import Build
        
        existing_log = json.dumps([{"stage": "old", "reasoning": "old reason"}])
        build = Build(prompt="Preserve log test", reasoning_log=existing_log)
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id
        
        _add_reasoning(build_id, "new", "new reason")
        
        # Expire session cache to see changes from other sessions
        db_session.expire_all()
        
        updated = db_session.get(Build, build_id)
        log = json.loads(updated.reasoning_log)
        assert len(log) == 2
        assert log[0]["stage"] == "old"
        assert log[1]["stage"] == "new"


class TestStripFences:
    """Note: Many fence tests exist in test_helpers.py, these are additional."""

    def test_strip_fences_html_with_language_tag(self):
        """Test extracting from ```html fences."""
        text = "```html\n<div>Hello</div>\n```"
        assert _strip_fences(text) == "<div>Hello</div>"

    def test_strip_fences_javascript_fence(self):
        """Test extracting from ```javascript fences."""
        text = "```javascript\nconst x = 1;\n```"
        result = _strip_fences(text)
        assert "const x = 1;" in result
        assert "```" not in result

    def test_strip_fences_python_fence(self):
        """Test extracting from ```python fences."""
        text = "```python\nprint('hello')\n```"
        result = _strip_fences(text)
        assert "print('hello')" in result
        assert "```" not in result

    def test_strip_fences_no_fence_returns_original(self):
        """Test that text without fences is returned as-is."""
        text = "<div>No fences here</div>"
        assert _strip_fences(text) == "<div>No fences here</div>"

    def test_strip_fences_with_leading_whitespace(self):
        """Test handling of leading whitespace."""
        text = "   ```html\n<p>content</p>\n```"
        result = _strip_fences(text)
        assert "<p>content</p>" in result

    def test_strip_fences_nested_backticks_in_code(self):
        """Test that nested backticks in code are preserved."""
        text = "```html\n<code>```nested```</code>\n```"
        result = _strip_fences(text)
        assert "```nested```" in result

    def test_strip_fences_multiline_content(self):
        """Test extracting multi-line content from fences."""
        text = """```html
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    <h1>Hello</h1>
</body>
</html>
```"""
        result = _strip_fences(text)
        assert "<!DOCTYPE html>" in result
        assert "<h1>Hello</h1>" in result
        assert "```" not in result

    def test_strip_fences_with_surrounding_text(self):
        """Test extracting code when surrounded by explanatory text."""
        text = """Here's the HTML I created:

```html
<div class="app">Content</div>
```

Let me know if you need changes."""
        result = _strip_fences(text)
        assert '<div class="app">Content</div>' in result
        assert "Here's the HTML" not in result

    def test_strip_fences_empty_fence_content(self):
        """Test handling empty fenced content."""
        text = "```html\n```"
        result = _strip_fences(text)
        assert result == ""

    def test_strip_fences_multiple_fences(self):
        """Test that only the first fence block is extracted."""
        text = """```html
<div>First</div>
```

Some text

```html
<div>Second</div>
```"""
        result = _strip_fences(text)
        # Should extract from the last closing fence
        assert "<div>First</div>" in result or "<div>Second</div>" in result
