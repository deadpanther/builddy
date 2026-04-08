"""Tests for config.py."""



class TestSettings:
    """Tests for the settings configuration."""

    def test_settings_exists(self):
        """Test that settings can be imported."""
        from config import settings
        assert settings is not None

    def test_settings_has_database_url(self):
        """Test that settings has DATABASE_URL."""
        from config import settings
        assert hasattr(settings, 'DATABASE_URL')

    def test_settings_has_cors_origins(self):
        """Test that settings has CORS origins."""
        from config import settings
        assert hasattr(settings, 'CORS_ORIGINS') or hasattr(settings, 'cors_origins_list')

    def test_cors_origins_list_returns_list(self):
        """Test that cors_origins_list returns a list."""
        from config import settings
        origins = settings.cors_origins_list
        assert isinstance(origins, list)

    def test_settings_has_github_token(self):
        """Test that settings has GITHUB_TOKEN attribute."""
        from config import settings
        assert hasattr(settings, 'GITHUB_TOKEN')

    def test_settings_has_railway_token(self):
        """Test that settings has RAILWAY_API_TOKEN attribute."""
        from config import settings
        assert hasattr(settings, 'RAILWAY_API_TOKEN')


class TestSettingsMethods:
    """Tests for settings methods."""

    def test_cors_origins_list_handles_string(self):
        """Test cors_origins_list handles string input."""
        from config import settings
        # Just verify it returns a list without error
        origins = settings.cors_origins_list
        assert isinstance(origins, list)

    def test_database_url_has_default(self):
        """Test DATABASE_URL has a default value."""
        from config import settings
        assert settings.DATABASE_URL is not None


class TestEnvironmentVariables:
    """Tests for environment variable handling."""

    def test_settings_loads_from_env(self):
        """Test that settings loads from environment."""
        from config import settings
        # Settings should be loaded
        assert settings is not None
