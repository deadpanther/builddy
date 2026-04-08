"""Tests for services/visual_validator.py."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestValidateHtml:
    """Tests for validate_html function."""

    @pytest.mark.asyncio
    async def test_function_exists(self):
        """Test that function exists."""
        from services.visual_validator import validate_html
        assert callable(validate_html)

    @pytest.mark.asyncio
    async def test_returns_dict(self):
        """Test that function returns a dictionary."""
        from services.visual_validator import validate_html
        
        # Mock playwright to avoid browser dependency
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_page.title = AsyncMock(return_value="Test Page")
        mock_page.screenshot = AsyncMock(return_value=b"fake_screenshot")
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.on = MagicMock()
        
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()
        
        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)
        
        mock_pw = AsyncMock()
        mock_pw.chromium = mock_chromium
        mock_pw.__aenter__ = AsyncMock(return_value=mock_pw)
        mock_pw.__aexit__ = AsyncMock()
        
        with patch('services.visual_validator.async_playwright', return_value=mock_pw):
            result = await validate_html("<html><body>Test</body></html>")
        
        assert isinstance(result, dict)
        assert "console_errors" in result
        assert "screenshot_base64" in result
        assert "page_title" in result
        assert "has_errors" in result

    @pytest.mark.asyncio
    async def test_handles_empty_html(self):
        """Test handling of empty HTML."""
        from services.visual_validator import validate_html
        
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_page.title = AsyncMock(return_value="")
        mock_page.screenshot = AsyncMock(return_value=b"")
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.on = MagicMock()
        
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()
        
        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)
        
        mock_pw = AsyncMock()
        mock_pw.chromium = mock_chromium
        mock_pw.__aenter__ = AsyncMock(return_value=mock_pw)
        mock_pw.__aexit__ = AsyncMock()
        
        with patch('services.visual_validator.async_playwright', return_value=mock_pw):
            result = await validate_html("")
        
        assert isinstance(result, dict)


class TestValidateDeployedUrl:
    """Tests for validate_deployed_url function."""

    @pytest.mark.asyncio
    async def test_function_exists(self):
        """Test that function exists."""
        from services.visual_validator import validate_deployed_url
        assert callable(validate_deployed_url)

    @pytest.mark.asyncio
    async def test_returns_dict(self):
        """Test that function returns a dictionary."""
        from services.visual_validator import validate_deployed_url
        
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_page.title = AsyncMock(return_value="Test Page")
        mock_page.screenshot = AsyncMock(return_value=b"fake_screenshot")
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.on = MagicMock()
        
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()
        
        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)
        
        mock_pw = AsyncMock()
        mock_pw.chromium = mock_chromium
        mock_pw.__aenter__ = AsyncMock(return_value=mock_pw)
        mock_pw.__aexit__ = AsyncMock()
        
        with patch('services.visual_validator.async_playwright', return_value=mock_pw):
            result = await validate_deployed_url("http://example.com")
        
        assert isinstance(result, dict)
        assert "console_errors" in result

    @pytest.mark.asyncio
    async def test_handles_invalid_url(self):
        """Test handling of invalid URL."""
        from services.visual_validator import validate_deployed_url
        
        # Should return a dict with error when playwright fails
        mock_pw = AsyncMock()
        mock_pw.__aenter__ = AsyncMock(side_effect=Exception("Failed"))
        mock_pw.__aexit__ = AsyncMock()
        
        with patch('services.visual_validator.async_playwright', return_value=mock_pw):
            result = await validate_deployed_url("not-a-url")
        
        assert isinstance(result, dict)
        assert "console_errors" in result
        assert result["has_errors"] is True
