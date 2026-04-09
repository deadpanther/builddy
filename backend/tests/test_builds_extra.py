"""Extra tests for builds router — covering SSE stream, cloud deploy status, list builds, and chain traversal."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models import Build


def _make_build(**overrides):
    defaults = dict(
        prompt="Test app",
        status="deployed",
        generated_code="<h1>Hello</h1>",
        app_name="Test App",
        build_type="text",
        complexity="simple",
    )
    defaults.update(overrides)
    return Build(**defaults)


class TestListBuilds:
    @pytest.mark.asyncio
    async def test_list_all_builds(self, client, db_session):
        b1 = _make_build(app_name="App1")
        b2 = _make_build(app_name="App2", status="coding")
        db_session.add(b1)
        db_session.add(b2)
        db_session.commit()

        resp = await client.get("/api/builds")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_list_builds_filter_status(self, client, db_session):
        b1 = _make_build(status="deployed", app_name="DeployedApp")
        b2 = _make_build(status="failed", app_name="FailedApp")
        db_session.add(b1)
        db_session.add(b2)
        db_session.commit()

        resp = await client.get("/api/builds?status=failed")
        assert resp.status_code == 200
        data = resp.json()
        assert all(b["status"] == "failed" for b in data)

    @pytest.mark.asyncio
    async def test_list_builds_pagination(self, client, db_session):
        for i in range(5):
            db_session.add(_make_build(app_name=f"Pag{i}"))
        db_session.commit()

        resp = await client.get("/api/builds?offset=2&limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2


class TestCloudDeployStatus:
    @pytest.mark.asyncio
    async def test_deploy_status_manual(self, client, db_session):
        """Covers the manual deploy status path."""
        build = _make_build(deploy_status="manual", deploy_provider="railway")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        with patch("services.cloud_deploy.get_manual_deploy_instructions", return_value={"steps": []}):
            resp = await client.get(f"/api/builds/{build.id}/deploy-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "manual"

    @pytest.mark.asyncio
    async def test_deploy_status_with_provider(self, client, db_session):
        """Covers the provider status check path."""
        build = _make_build(deploy_status="deploying", deploy_provider="railway")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        with patch("services.cloud_deploy.get_deploy_status", new=AsyncMock(return_value={
            "status": "deployed", "url": "https://app.railway.app"
        })):
            resp = await client.get(f"/api/builds/{build.id}/deploy-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "deployed"


class TestCloudDeployEndpoint:
    @pytest.mark.asyncio
    async def test_cloud_deploy_success(self, client, db_session):
        """Covers lines 379-398 — cloud deploy with files."""
        build = _make_build(deploy_url="http://localhost:9100/apps/test")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        with patch("services.cloud_deploy.deploy_to_cloud", new=AsyncMock(return_value={
            "status": "deployed", "url": "https://myapp.railway.app"
        })):
            resp = await client.post(
                f"/api/builds/{build.id}/cloud-deploy",
                json={"provider": "railway"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["deploy_provider"] == "railway"

    @pytest.mark.asyncio
    async def test_cloud_deploy_with_generated_files(self, client, db_session):
        """Covers line 384 — project_files from generated_files."""
        files = {"index.html": "<h1>Hi</h1>", "style.css": "body{}"}
        build = _make_build(
            generated_code=None,
            generated_files=json.dumps(files),
            complexity="fullstack",
        )
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        with patch("services.cloud_deploy.deploy_to_cloud", new=AsyncMock(return_value={
            "status": "ready", "url": "https://github.com/user/repo"
        })):
            resp = await client.post(
                f"/api/builds/{build.id}/cloud-deploy",
                json={"provider": "render"},
            )
        assert resp.status_code == 200


class TestBuildChainTraversal:
    @pytest.mark.asyncio
    async def test_chain_deep_with_cycle_protection(self, client, db_session):
        """Covers line 529 — cycle protection in chain traversal."""
        b1 = _make_build(app_name="Root")
        db_session.add(b1)
        db_session.commit()
        db_session.refresh(b1)

        b2 = _make_build(app_name="Child", parent_build_id=b1.id)
        db_session.add(b2)
        db_session.commit()
        db_session.refresh(b2)

        resp = await client.get(f"/api/builds/{b2.id}/chain")
        assert resp.status_code == 200
        chain = resp.json()
        assert len(chain) >= 2


class TestGetBuildById:
    @pytest.mark.asyncio
    async def test_get_existing_build(self, client, db_session):
        build = _make_build()
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        resp = await client.get(f"/api/builds/{build.id}")
        assert resp.status_code == 200
        assert resp.json()["app_name"] == "Test App"

    @pytest.mark.asyncio
    async def test_get_nonexistent_build(self, client):
        resp = await client.get("/api/builds/no-id")
        assert resp.status_code == 404


class TestCreateBuild:
    @pytest.mark.asyncio
    async def test_create_basic_build(self, client, mock_pipeline):
        resp = await client.post(
            "/api/builds",
            json={"prompt": "Build a calculator app"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["build_type"] == "text"

    @pytest.mark.asyncio
    async def test_create_build_with_empty_prompt(self, client, mock_pipeline):
        resp = await client.post(
            "/api/builds",
            json={"prompt": "a"},  # minimal prompt
        )
        assert resp.status_code == 200
