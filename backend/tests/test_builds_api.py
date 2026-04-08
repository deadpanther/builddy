"""Tests for the /api/builds endpoints."""

import pytest
from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# GET /api/builds  — list builds
# ---------------------------------------------------------------------------


class TestListBuilds:
    @pytest.mark.asyncio
    async def test_empty_list(self, client):
        resp = await client.get("/api/builds")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


# ---------------------------------------------------------------------------
# GET /api/builds/{id}  — get single build
# ---------------------------------------------------------------------------


class TestGetBuild:
    @pytest.mark.asyncio
    async def test_not_found(self, client):
        resp = await client.get("/api/builds/nonexistent-id-123")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /api/builds  — create a build
# ---------------------------------------------------------------------------


class TestCreateBuild:
    @pytest.mark.asyncio
    async def test_create_build(self, client, mock_pipeline):
        resp = await client.post(
            "/api/builds",
            json={"prompt": "Build a todo app", "tweet_text": "Build a todo app"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "pending"
        assert body["id"]  # non-empty UUID
        assert body["prompt"] == "Build a todo app"

    @pytest.mark.asyncio
    async def test_create_build_returns_build_fields(self, client, mock_pipeline):
        resp = await client.post(
            "/api/builds",
            json={"prompt": "Calculator app"},
        )
        assert resp.status_code == 200
        body = resp.json()
        # Should have core fields
        assert "id" in body
        assert "status" in body
        assert "created_at" in body
        assert "updated_at" in body
        assert body["build_type"] == "text"

    @pytest.mark.asyncio
    async def test_created_build_appears_in_list(self, client, mock_pipeline):
        create_resp = await client.post(
            "/api/builds",
            json={"prompt": "A weather dashboard"},
        )
        build_id = create_resp.json()["id"]

        list_resp = await client.get("/api/builds")
        ids = [b["id"] for b in list_resp.json()]
        assert build_id in ids

    @pytest.mark.asyncio
    async def test_created_build_fetchable_by_id(self, client, mock_pipeline):
        create_resp = await client.post(
            "/api/builds",
            json={"prompt": "A chat app"},
        )
        build_id = create_resp.json()["id"]

        get_resp = await client.get(f"/api/builds/{build_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == build_id


# ---------------------------------------------------------------------------
# PUT /api/builds/{id}/files  — update a file (path traversal)
# ---------------------------------------------------------------------------


class TestUpdateBuildFile:
    @pytest.mark.asyncio
    async def test_rejects_path_traversal_dotdot(self, client, mock_pipeline, db_session):
        # Create a deployed build so the path traversal check is reached
        from models import Build
        build = Build(prompt="Some app", status="deployed", generated_code="<h1>hi</h1>")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id

        resp = await client.put(
            f"/api/builds/{build_id}/files",
            json={"file_path": "../etc/passwd", "content": "evil"},
        )
        # Should reject with 400 (path traversal)
        assert resp.status_code == 400
        assert "invalid" in resp.json()["detail"].lower() or "path" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_rejects_path_traversal_absolute(self, client, mock_pipeline):
        create_resp = await client.post(
            "/api/builds",
            json={"prompt": "Some app"},
        )
        build_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/builds/{build_id}/files",
            json={"file_path": "/etc/passwd", "content": "evil"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_path_traversal_backslash(self, client, mock_pipeline):
        create_resp = await client.post(
            "/api/builds",
            json={"prompt": "Some app"},
        )
        build_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/builds/{build_id}/files",
            json={"file_path": "\\windows\\system32\\evil.dll", "content": "evil"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_empty_file_path(self, client, mock_pipeline):
        create_resp = await client.post(
            "/api/builds",
            json={"prompt": "Some app"},
        )
        build_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/builds/{build_id}/files",
            json={"file_path": "", "content": "stuff"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_edit_on_non_deployed_build(self, client, mock_pipeline):
        """Only deployed builds can have files edited."""
        create_resp = await client.post(
            "/api/builds",
            json={"prompt": "Some app"},
        )
        build_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/builds/{build_id}/files",
            json={"file_path": "index.html", "content": "<h1>Hi</h1>"},
        )
        # Build is still "pending", so this should be rejected
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/builds/{id}
# ---------------------------------------------------------------------------


class TestDeleteBuild:
    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, client):
        resp = await client.delete("/api/builds/does-not-exist-999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_existing_build(self, client, mock_pipeline):
        create_resp = await client.post(
            "/api/builds",
            json={"prompt": "Ephemeral app"},
        )
        build_id = create_resp.json()["id"]

        # Mock the process_manager.stop_app (imported inside delete handler)
        with patch("services.process_manager.process_manager") as pm:
            pm.stop_app = AsyncMock()
            del_resp = await client.delete(f"/api/builds/{build_id}")

        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "deleted"

        # Confirm it's gone
        get_resp = await client.get(f"/api/builds/{build_id}")
        assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/health  — quick sanity check
# ---------------------------------------------------------------------------


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "buildy"
