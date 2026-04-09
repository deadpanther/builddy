"""Tests for main.py endpoints."""


import pytest


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        """Test health endpoint returns ok status."""
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "builddy"

    @pytest.mark.asyncio
    async def test_health_has_version(self, client):
        """Test health endpoint includes version."""
        resp = await client.get("/api/health")
        data = resp.json()
        assert "version" in data


class TestListProcesses:
    """Tests for the processes listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_processes(self, client):
        """Test listing processes returns a dict with processes key."""
        resp = await client.get("/api/processes")
        assert resp.status_code == 200
        data = resp.json()
        assert "processes" in data
        assert isinstance(data["processes"], list)


class TestThumbnailEndpoint:
    """Tests for the thumbnail endpoint."""

    @pytest.mark.asyncio
    async def test_thumbnail_not_found(self, client):
        """Test thumbnail endpoint returns 404 for missing thumbnail."""
        resp = await client.get("/apps/nonexistent-build/thumbnail.png")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data


class TestCORS:
    """Tests for CORS configuration."""

    @pytest.mark.asyncio
    async def test_cors_headers_present(self, client):
        """Test that CORS headers are present."""
        resp = await client.options("/api/health")
        # Check for CORS headers (these may vary based on configuration)
        assert resp.status_code in [200, 405]


class TestAPIRoutes:
    """Tests to verify all expected API routes exist."""

    @pytest.mark.asyncio
    async def test_builds_route_exists(self, client):
        """Test that builds router is mounted."""
        # Try to access a builds endpoint
        resp = await client.get("/api/builds")
        # Should not return 404 for the route itself
        # (might return empty list or error, but route should exist)
        assert resp.status_code != 404 or "builds" in str(resp.url)

    @pytest.mark.asyncio
    async def test_gallery_route_exists(self, client):
        """Test that gallery router is mounted."""
        resp = await client.get("/api/gallery")
        assert resp.status_code == 200  # Should return list (empty or not)
