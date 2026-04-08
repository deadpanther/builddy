"""Additional tests for routers/builds.py - more endpoints."""

import pytest
import json
from unittest.mock import patch, AsyncMock


class TestBuildChain:
    """Tests for build chain endpoint."""

    @pytest.mark.asyncio
    async def test_get_build_chain_not_found(self, client):
        """Test getting chain for non-existent build."""
        resp = await client.get("/api/builds/nonexistent/chain")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_build_chain_success(self, client, db_session):
        """Test getting build chain."""
        from models import Build
        
        # Create parent and child builds
        parent = Build(prompt="Original", status="deployed", deploy_url="/apps/parent/")
        db_session.add(parent)
        db_session.commit()
        db_session.refresh(parent)
        parent_id = parent.id
        
        child = Build(
            prompt="Modified",
            status="deployed",
            parent_build_id=parent_id,
            deploy_url="/apps/child/",
        )
        db_session.add(child)
        db_session.commit()
        
        resp = await client.get(f"/api/builds/{parent_id}/chain")
        assert resp.status_code == 200
        data = resp.json()
        # Response is a list of builds
        assert isinstance(data, list)
        assert len(data) >= 1


class TestDeleteBuild:
    """Tests for delete build endpoint."""

    @pytest.mark.asyncio
    async def test_delete_build_not_found(self, client):
        """Test deleting non-existent build."""
        resp = await client.delete("/api/builds/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_build_success(self, client, db_session):
        """Test deleting a build."""
        from models import Build
        
        build = Build(prompt="To delete", status="pending")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id
        
        resp = await client.delete(f"/api/builds/{build_id}")
        assert resp.status_code == 200
        
        # Verify build is deleted
        resp2 = await client.get(f"/api/builds/{build_id}")
        assert resp2.status_code == 404


class TestUpdateBuildFile:
    """Tests for update build file endpoint."""

    @pytest.mark.asyncio
    async def test_update_file_not_found(self, client):
        """Test updating file for non-existent build."""
        resp = await client.put(
            "/api/builds/nonexistent/files",
            json={"path": "index.html", "content": "<html></html>"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_file_wrong_status(self, client, db_session):
        """Test updating file for non-deployed build."""
        from models import Build
        
        build = Build(prompt="Test", status="pending")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id
        
        resp = await client.put(
            f"/api/builds/{build_id}/files",
            json={"path": "index.html", "content": "<html></html>"}
        )
        assert resp.status_code == 400


class TestGetBuildSteps:
    """Tests for get build steps endpoint."""

    @pytest.mark.asyncio
    async def test_get_steps_not_found(self, client):
        """Test getting steps for non-existent build."""
        resp = await client.get("/api/builds/nonexistent/steps")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_steps_success(self, client, db_session):
        """Test getting build steps."""
        from models import Build
        
        steps = json.dumps(["Step 1", "Step 2", "Step 3"])
        build = Build(prompt="Test", status="deployed", steps=steps)
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id
        
        resp = await client.get(f"/api/builds/{build_id}/steps")
        assert resp.status_code == 200
        data = resp.json()
        assert "steps" in data


class TestDownloadBuild:
    """Tests for download build endpoint."""

    @pytest.mark.asyncio
    async def test_download_not_found(self, client):
        """Test downloading non-existent build."""
        resp = await client.get("/api/builds/nonexistent/download")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_download_no_code(self, client, db_session):
        """Test downloading build with no code."""
        from models import Build
        
        build = Build(prompt="Empty", status="pending")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id
        
        resp = await client.get(f"/api/builds/{build_id}/download")
        # Should return error or redirect
        assert resp.status_code in [400, 404]


class TestListBuilds:
    """Tests for list builds endpoint."""

    @pytest.mark.asyncio
    async def test_list_builds_empty(self, client):
        """Test listing builds when empty."""
        resp = await client.get("/api/builds")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_builds_with_data(self, client, db_session):
        """Test listing builds with data."""
        from models import Build
        
        for i in range(3):
            build = Build(prompt=f"Build {i}", status="pending")
            db_session.add(build)
        db_session.commit()
        
        resp = await client.get("/api/builds")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 3

    @pytest.mark.asyncio
    async def test_list_builds_pagination(self, client, db_session):
        """Test listing builds with pagination."""
        from models import Build
        
        for i in range(10):
            build = Build(prompt=f"Build {i}", status="pending")
            db_session.add(build)
        db_session.commit()
        
        resp = await client.get("/api/builds?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
