"""Tests for builds router endpoints — modify, remix, download, retry, delete, chain, files, cloud deploy."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from models import Build


def _make_build(**overrides):
    """Helper to create a Build with sensible defaults."""
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


class TestModifyBuild:
    @pytest.mark.asyncio
    async def test_modify_simple_build(self, client, db_session, mock_all_pipelines):
        original = _make_build()
        db_session.add(original)
        db_session.commit()
        db_session.refresh(original)

        resp = await client.post(
            f"/api/builds/{original.id}/modify",
            json={"modification": "Change the color to blue"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["parent_build_id"] == original.id
        assert "v2" in data["app_name"]

    @pytest.mark.asyncio
    async def test_modify_fullstack_build(self, client, db_session, mock_all_pipelines):
        original = _make_build(
            complexity="fullstack",
            generated_code=None,
            generated_files=json.dumps({"index.html": "<h1>Hi</h1>", "style.css": "body{}"}),
        )
        db_session.add(original)
        db_session.commit()
        db_session.refresh(original)

        resp = await client.post(
            f"/api/builds/{original.id}/modify",
            json={"modification": "Add dark mode"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["complexity"] == "fullstack"
        mock_all_pipelines["run_modify_fullstack_pipeline"].assert_awaited_once()

    @pytest.mark.asyncio
    async def test_modify_nonexistent_build(self, client, mock_all_pipelines):
        resp = await client.post(
            "/api/builds/nonexistent-id/modify",
            json={"modification": "Change something"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_modify_build_no_code(self, client, db_session, mock_all_pipelines):
        original = _make_build(generated_code=None, generated_files=None)
        db_session.add(original)
        db_session.commit()
        db_session.refresh(original)

        resp = await client.post(
            f"/api/builds/{original.id}/modify",
            json={"modification": "Change it"},
        )
        assert resp.status_code == 400


class TestRemixBuild:
    @pytest.mark.asyncio
    async def test_remix_deployed_build(self, client, db_session, mock_all_pipelines):
        original = _make_build()
        db_session.add(original)
        db_session.commit()
        db_session.refresh(original)

        resp = await client.post(
            f"/api/builds/{original.id}/remix",
            json={"prompt": "Make it a weather app"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["prompt"] == "Make it a weather app"
        assert data["parent_build_id"] == original.id

        # Check remix_count incremented on original
        db_session.refresh(original)
        assert original.remix_count == 1

    @pytest.mark.asyncio
    async def test_remix_non_deployed_build(self, client, db_session, mock_all_pipelines):
        original = _make_build(status="coding")
        db_session.add(original)
        db_session.commit()
        db_session.refresh(original)

        resp = await client.post(
            f"/api/builds/{original.id}/remix",
            json={"prompt": "Make it different"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_remix_nonexistent(self, client, mock_all_pipelines):
        resp = await client.post(
            "/api/builds/no-such-id/remix",
            json={"prompt": "test"},
        )
        assert resp.status_code == 404


class TestDownloadBuild:
    @pytest.mark.asyncio
    async def test_download_no_zip(self, client, db_session):
        build = _make_build()
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        resp = await client.get(f"/api/builds/{build.id}/download")
        # No zip_url set
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_download_nonexistent(self, client):
        resp = await client.get("/api/builds/no-id/download")
        assert resp.status_code == 404


class TestRetryBuild:
    @pytest.mark.asyncio
    async def test_retry_failed_build(self, client, db_session, mock_all_pipelines):
        build = _make_build(status="failed", error="[coding] Something went wrong", generated_code=None)
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        resp = await client.post(f"/api/builds/{build.id}/retry")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["error"] is None
        mock_all_pipelines["run_retry_pipeline"].assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retry_already_deployed(self, client, db_session, mock_all_pipelines):
        build = _make_build(status="deployed")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        resp = await client.post(f"/api/builds/{build.id}/retry")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_retry_nonexistent(self, client, mock_all_pipelines):
        resp = await client.post("/api/builds/no-id/retry")
        assert resp.status_code == 404


class TestDeleteBuild:
    @pytest.mark.asyncio
    async def test_delete_existing_build(self, client, db_session):
        build = _make_build()
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id

        resp = await client.delete(f"/api/builds/{build_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        # Verify deleted from DB (expire cache to see the commit from the endpoint's session)
        db_session.expire_all()
        assert db_session.get(Build, build_id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, client):
        resp = await client.delete("/api/builds/no-id")
        assert resp.status_code == 404


class TestBuildChain:
    @pytest.mark.asyncio
    async def test_chain_single_build(self, client, db_session):
        build = _make_build()
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        resp = await client.get(f"/api/builds/{build.id}/chain")
        assert resp.status_code == 200
        chain = resp.json()
        assert len(chain) == 1
        assert chain[0]["id"] == build.id

    @pytest.mark.asyncio
    async def test_chain_with_parent(self, client, db_session):
        parent = _make_build(app_name="Parent App")
        db_session.add(parent)
        db_session.commit()
        db_session.refresh(parent)

        child = _make_build(app_name="Child App", parent_build_id=parent.id)
        db_session.add(child)
        db_session.commit()
        db_session.refresh(child)

        resp = await client.get(f"/api/builds/{child.id}/chain")
        assert resp.status_code == 200
        chain = resp.json()
        assert len(chain) == 2

    @pytest.mark.asyncio
    async def test_chain_nonexistent(self, client):
        resp = await client.get("/api/builds/no-id/chain")
        assert resp.status_code == 404


class TestGetBuildFiles:
    @pytest.mark.asyncio
    async def test_get_files_multi(self, client, db_session):
        files = {"index.html": "<h1>Hi</h1>", "style.css": "body{}"}
        build = _make_build(generated_code=None, generated_files=json.dumps(files), complexity="fullstack")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        resp = await client.get(f"/api/builds/{build.id}/files")
        assert resp.status_code == 200
        data = resp.json()
        assert data["file_count"] == 2
        assert "index.html" in data["files"]

    @pytest.mark.asyncio
    async def test_get_files_single(self, client, db_session):
        build = _make_build()
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        resp = await client.get(f"/api/builds/{build.id}/files")
        assert resp.status_code == 200
        data = resp.json()
        assert data["file_count"] == 1
        assert "index.html" in data["files"]

    @pytest.mark.asyncio
    async def test_get_files_no_code(self, client, db_session):
        build = _make_build(generated_code=None, generated_files=None)
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        resp = await client.get(f"/api/builds/{build.id}/files")
        assert resp.status_code == 404


class TestUpdateBuildFile:
    @pytest.mark.asyncio
    async def test_update_file_simple_build(self, client, db_session):
        build = _make_build()
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        with patch("services.deployer.deploy_html") as mock_deploy:
            mock_deploy.return_value = f"http://localhost:9100/apps/{build.id}"
            resp = await client.put(
                f"/api/builds/{build.id}/files",
                json={"file_path": "index.html", "content": "<h1>Updated</h1>"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"

    @pytest.mark.asyncio
    async def test_update_file_path_traversal(self, client, db_session):
        build = _make_build()
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        resp = await client.put(
            f"/api/builds/{build.id}/files",
            json={"file_path": "../etc/passwd", "content": "evil"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_file_non_deployed(self, client, db_session):
        build = _make_build(status="coding")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        resp = await client.put(
            f"/api/builds/{build.id}/files",
            json={"file_path": "index.html", "content": "<h1>Hi</h1>"},
        )
        assert resp.status_code == 400


class TestDeployBuild:
    @pytest.mark.asyncio
    async def test_deploy_simple_build(self, client, db_session):
        build = _make_build(status="coding")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        with patch("services.deployer.deploy_html") as mock_deploy:
            mock_deploy.return_value = f"http://localhost:9100/apps/{build.id}"
            resp = await client.post(f"/api/builds/{build.id}/deploy")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "deployed"
        assert data["deploy_url"] is not None

    @pytest.mark.asyncio
    async def test_deploy_no_code(self, client, db_session):
        build = _make_build(generated_code=None)
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        resp = await client.post(f"/api/builds/{build.id}/deploy")
        assert resp.status_code == 400


class TestCloudDeploy:
    @pytest.mark.asyncio
    async def test_cloud_deploy_not_deployed(self, client, db_session):
        build = _make_build(status="coding")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        resp = await client.post(
            f"/api/builds/{build.id}/cloud-deploy",
            json={"provider": "railway"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_cloud_deploy_invalid_provider(self, client, db_session):
        build = _make_build()
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        resp = await client.post(
            f"/api/builds/{build.id}/cloud-deploy",
            json={"provider": "aws"},
        )
        assert resp.status_code == 400


class TestGenerateTests:
    @pytest.mark.asyncio
    async def test_generate_tests_not_deployed(self, client, db_session):
        build = _make_build(status="coding")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        resp = await client.post(f"/api/builds/{build.id}/generate-tests")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_tests_no_code(self, client, db_session):
        build = _make_build(generated_code=None, generated_files=None)
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        resp = await client.post(f"/api/builds/{build.id}/generate-tests")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_tests_success(self, client, db_session):
        build = _make_build()
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        fake_tests = {"tests.html": "<html>test suite</html>"}
        import tempfile
        from pathlib import Path
        tmp = Path(tempfile.mkdtemp()) / build.id
        tmp.mkdir(parents=True, exist_ok=True)

        with patch("agent.test_gen.generate_tests", new=AsyncMock(return_value=fake_tests)), \
             patch("services.deployer.deploy_project", new=AsyncMock()), \
             patch("services.deployer.DEPLOYED_DIR", tmp.parent):
            resp = await client.post(f"/api/builds/{build.id}/generate-tests")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "generated"
        assert data["test_count"] == 1


class TestBuildFromImage:
    @pytest.mark.asyncio
    async def test_create_from_image(self, client, mock_all_pipelines):
        resp = await client.post(
            "/api/builds/from-image",
            json={"image_base64": "data:image/png;base64,iVBOR...", "prompt": "Build this"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["build_type"] == "screenshot"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_from_image_no_prompt(self, client, mock_all_pipelines):
        resp = await client.post(
            "/api/builds/from-image",
            json={"image_base64": ["iVBOR...", "iVBOR..."]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["app_name"] == "App from Screenshot"


class TestDeployStatus:
    @pytest.mark.asyncio
    async def test_deploy_status_no_provider(self, client, db_session):
        build = _make_build()
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        resp = await client.get(f"/api/builds/{build.id}/deploy-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "none"
        assert data["provider"] is None
