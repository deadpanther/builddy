"""Tests for routers/gallery.py."""

from datetime import UTC, datetime

import pytest

from models import Build


class TestGalleryEndpoints:
    @pytest.mark.asyncio
    async def test_list_gallery_returns_list(self, client):
        """Test gallery endpoint returns a list."""
        resp = await client.get("/api/gallery")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_gallery_with_builds(self, client, db_session):
        """Test gallery endpoint returns deployed builds."""
        import uuid
        unique = str(uuid.uuid4())[:8]

        # Create some builds with unique identifiers
        build1 = Build(
            prompt=f"First app {unique}",
            status="deployed",
            app_name=f"App1-{unique}",
            deploy_url=f"/apps/build1-{unique}/",
            deployed_at=datetime.now(UTC),
        )
        build2 = Build(
            prompt=f"Second app {unique}",
            status="deployed",
            app_name=f"App2-{unique}",
            deploy_url=f"/apps/build2-{unique}/",
            deployed_at=datetime.now(UTC),
        )
        build3 = Build(
            prompt=f"Failed app {unique}",
            status="failed",
            app_name=f"FailedApp-{unique}",
        )
        db_session.add_all([build1, build2, build3])
        db_session.commit()

        resp = await client.get("/api/gallery")
        assert resp.status_code == 200
        data = resp.json()

        # Find our specific builds
        app_names = [b["app_name"] for b in data]
        assert f"App1-{unique}" in app_names
        assert f"App2-{unique}" in app_names
        assert f"FailedApp-{unique}" not in app_names

    @pytest.mark.asyncio
    async def test_list_gallery_limits_results(self, client, db_session):
        """Test gallery endpoint respects limit parameter."""
        # Create many builds
        for i in range(15):
            build = Build(
                prompt=f"App {i}",
                status="deployed",
                app_name=f"App{i}",
                deploy_url=f"/apps/build{i}/",
                deployed_at=datetime.now(UTC),
            )
            db_session.add(build)
        db_session.commit()

        resp = await client.get("/api/gallery?limit=10")
        assert resp.status_code == 200
        data = resp.json()

        # Should limit to 10
        assert len(data) == 10

    @pytest.mark.asyncio
    async def test_list_gallery_excludes_pending(self, client, db_session):
        """Test gallery excludes pending/coding builds."""
        # Use unique identifiers to avoid conflicts with other tests
        import uuid
        unique = str(uuid.uuid4())[:8]

        build1 = Build(prompt=f"Pending-{unique}", status="pending")
        build2 = Build(prompt=f"Coding-{unique}", status="coding")
        build3 = Build(
            prompt=f"Deployed-{unique}",
            status="deployed",
            deploy_url="/apps/x/",
            deployed_at=datetime.now(UTC),
        )
        db_session.add_all([build1, build2, build3])
        db_session.commit()

        resp = await client.get("/api/gallery")
        data = resp.json()

        # Find our specific build
        deployed = [b for b in data if b.get("deploy_url") == "/apps/x/"]
        assert len(deployed) == 1

    @pytest.mark.asyncio
    async def test_gallery_detail(self, client, db_session):
        """Test getting a single build from gallery."""
        build = Build(
            prompt="Detail app",
            status="deployed",
            app_name="DetailApp",
            generated_code="<html>Detail</html>",
            deploy_url="/apps/detail/",
            deployed_at=datetime.now(UTC),
        )
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)
        build_id = build.id

        resp = await client.get(f"/api/gallery/{build_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["app_name"] == "DetailApp"
        assert data["generated_code"] == "<html>Detail</html>"

    @pytest.mark.asyncio
    async def test_gallery_detail_not_found(self, client):
        """Test getting non-existent build from gallery."""
        resp = await client.get("/api/gallery/nonexistent-id")
        assert resp.status_code == 404
