"""Additional tests for routers/builds.py - modify, cloud deploy, test generation."""

import json
from unittest.mock import AsyncMock, patch

import pytest


class TestModifyBuild:
    @pytest.mark.asyncio
    async def test_modify_build_not_found(self, client):
        """Test modifying a non-existent build."""
        resp = await client.post(
            "/api/builds/nonexistent/modify",
            json={"modification": "Add a button"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_modify_build_no_code(self, client, db_session):
        """Test modifying a build with no code."""
        from models import Build

        build = Build(prompt="Empty", status="deployed")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id

        resp = await client.post(
            f"/api/builds/{build_id}/modify",
            json={"modification": "Add a button"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_modify_build_success(self, client, db_session):
        """Test successful build modification."""
        from models import Build

        build = Build(
            prompt="Original app",
            status="deployed",
            app_name="TestApp",
            generated_code="<html><body>Original</body></html>",
            deploy_url="/apps/test/",
        )
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id

        with patch("routers.builds.run_modify_pipeline", new=AsyncMock()):
            resp = await client.post(
                f"/api/builds/{build_id}/modify",
                json={"modification": "Add a blue button"},
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["parent_build_id"] == build_id


class TestCloudDeploy:
    @pytest.mark.asyncio
    async def test_cloud_deploy_not_found(self, client):
        """Test cloud deploy for non-existent build."""
        resp = await client.post(
            "/api/builds/nonexistent/cloud-deploy",
            json={"provider": "railway"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cloud_deploy_wrong_status(self, client, db_session):
        """Test cloud deploy for non-deployed build."""
        from models import Build

        build = Build(prompt="App", status="pending")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id

        resp = await client.post(
            f"/api/builds/{build_id}/cloud-deploy",
            json={"provider": "railway"},
        )

        # Should fail because build is not deployed
        assert resp.status_code == 400


class TestGenerateTests:
    @pytest.mark.asyncio
    async def test_generate_tests_not_found(self, client):
        """Test test generation for non-existent build."""
        resp = await client.post("/api/builds/nonexistent/generate-tests")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_tests_wrong_status(self, client, db_session):
        """Test test generation for non-deployed build."""
        from models import Build

        build = Build(prompt="App", status="pending")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id

        resp = await client.post(f"/api/builds/{build_id}/generate-tests")

        assert resp.status_code == 400


class TestRemixBuild:
    @pytest.mark.asyncio
    async def test_remix_not_found(self, client):
        """Test remix for non-existent build."""
        resp = await client.post(
            "/api/builds/nonexistent/remix",
            json={"prompt": "New version"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_remix_not_deployed(self, client, db_session):
        """Test remix for non-deployed build."""
        from models import Build

        build = Build(prompt="App", status="pending")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id

        resp = await client.post(
            f"/api/builds/{build_id}/remix",
            json={"prompt": "Make it blue"},
        )

        assert resp.status_code == 400


class TestRetryBuild:
    @pytest.mark.asyncio
    async def test_retry_not_found(self, client):
        """Test retry for non-existent build."""
        resp = await client.post("/api/builds/nonexistent/retry")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_retry_failed_build(self, client, db_session):
        """Test retrying a failed build."""
        from models import Build

        build = Build(
            prompt="Failed app",
            status="failed",
            error_message="Something went wrong",
        )
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id

        with patch("routers.builds.run_retry_pipeline", new=AsyncMock()):
            resp = await client.post(f"/api/builds/{build_id}/retry")

            assert resp.status_code == 200


class TestBuildFiles:
    @pytest.mark.asyncio
    async def test_get_files_not_found(self, client):
        """Test getting files for non-existent build."""
        resp = await client.get("/api/builds/nonexistent/files")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_files_success(self, client, db_session):
        """Test getting files for a build."""
        from models import Build

        files = {"index.html": "<html></html>", "app.js": "console.log(1);"}
        build = Build(
            prompt="App",
            status="deployed",
            generated_files=json.dumps(files),
            file_manifest=json.dumps(list(files.keys())),
        )
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id

        resp = await client.get(f"/api/builds/{build_id}/files")

        assert resp.status_code == 200
        data = resp.json()
        # The response has a "files" key containing the file contents
        assert "files" in data
        assert "index.html" in data["files"]
        assert data["files"]["index.html"] == "<html></html>"
