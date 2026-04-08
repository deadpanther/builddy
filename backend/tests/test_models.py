"""Tests for models.py."""

import pytest
from datetime import datetime, timezone


class TestBuildModel:
    """Tests for the Build model."""

    def test_build_model_exists(self):
        """Test that Build model can be imported."""
        from models import Build
        assert Build is not None

    def test_build_creation(self):
        """Test creating a Build instance."""
        from models import Build
        
        build = Build(prompt="Test app")
        assert build.prompt == "Test app"
        assert build.status == "pending"  # Default status

    def test_build_default_values(self):
        """Test Build default values."""
        from models import Build
        
        build = Build(prompt="Test")
        assert build.status == "pending"
        assert build.build_type == "text"
        assert build.complexity == "simple"
        assert build.remix_count == 0

    def test_build_with_all_fields(self):
        """Test Build with all fields."""
        from models import Build
        
        build = Build(
            prompt="Test app",
            status="deployed",
            app_name="TestApp",
            app_description="A test app",
            generated_code="<html></html>",
            deploy_url="/apps/test/",
        )
        
        assert build.prompt == "Test app"
        assert build.status == "deployed"
        assert build.app_name == "TestApp"
        assert build.generated_code == "<html></html>"

    def test_build_id_is_string(self):
        """Test that Build ID is a string (UUID)."""
        from models import Build
        
        build = Build(prompt="Test")
        # ID should be set automatically or be None before save
        # After save, it should be a string UUID
        assert build.id is None or isinstance(build.id, str)


class TestBuildStatus:
    """Tests for Build status values."""

    def test_pending_status(self):
        """Test pending status."""
        from models import Build
        build = Build(prompt="Test", status="pending")
        assert build.status == "pending"

    def test_coding_status(self):
        """Test coding status."""
        from models import Build
        build = Build(prompt="Test", status="coding")
        assert build.status == "coding"

    def test_deployed_status(self):
        """Test deployed status."""
        from models import Build
        build = Build(prompt="Test", status="deployed")
        assert build.status == "deployed"

    def test_failed_status(self):
        """Test failed status."""
        from models import Build
        build = Build(prompt="Test", status="failed")
        assert build.status == "failed"


class TestBuildOptionalFields:
    """Tests for Build optional fields."""

    def test_error_field(self):
        """Test error field."""
        from models import Build
        build = Build(prompt="Test", error="Something went wrong")
        assert build.error == "Something went wrong"

    def test_twitter_username(self):
        """Test twitter_username field."""
        from models import Build
        build = Build(prompt="Test", twitter_username="testuser")
        assert build.twitter_username == "testuser"

    def test_tech_stack(self):
        """Test tech_stack field."""
        from models import Build
        build = Build(prompt="Test", tech_stack='["react", "tailwind"]')
        assert build.tech_stack == '["react", "tailwind"]'

    def test_generated_files(self):
        """Test generated_files field."""
        from models import Build
        import json
        files = {"index.html": "<html></html>", "app.js": "console.log(1);"}
        build = Build(prompt="Test", generated_files=json.dumps(files))
        assert json.loads(build.generated_files) == files
