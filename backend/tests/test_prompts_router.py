"""Tests for prompts router — CRUD versions, experiments, assignments."""

import json
from unittest.mock import patch

import pytest

from models import PromptVersion, PromptExperiment, ExperimentAssignment


def _make_version(**overrides):
    defaults = dict(
        name="Test Prompt",
        prompt="You are a helpful coding assistant",
        prompt_type="system",
        version=1,
    )
    defaults.update(overrides)
    return PromptVersion(**defaults)


class TestListPromptVersions:
    @pytest.mark.asyncio
    async def test_list_empty(self, client, db_session):
        resp = await client.get("/api/prompts/versions")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_with_data(self, client, db_session):
        v1 = _make_version(name="V1")
        v2 = _make_version(name="V2", prompt_type="plan")
        db_session.add(v1)
        db_session.add(v2)
        db_session.commit()

        resp = await client.get("/api/prompts/versions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_list_filter_by_type(self, client, db_session):
        v1 = _make_version(prompt_type="system")
        v2 = _make_version(prompt_type="plan")
        db_session.add(v1)
        db_session.add(v2)
        db_session.commit()

        resp = await client.get("/api/prompts/versions?prompt_type=plan")
        assert resp.status_code == 200
        data = resp.json()
        assert all(v["prompt_type"] == "plan" for v in data)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_list_filter_active_only(self, client, db_session):
        v1 = _make_version(is_active=True)
        v2 = _make_version(is_active=False)
        db_session.add(v1)
        db_session.add(v2)
        db_session.commit()

        resp = await client.get("/api/prompts/versions?is_active=true")
        assert resp.status_code == 200
        data = resp.json()
        assert all(v["is_active"] for v in data)
        assert len(data) >= 1


class TestCreatePromptVersion:
    @pytest.mark.asyncio
    async def test_create_basic(self, client, db_session):
        resp = await client.post(
            "/api/prompts/versions",
            json={
                "name": "New Prompt",
                "prompt": "Build something cool",
                "prompt_type": "system",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New Prompt"
        assert data["version"] == 1

    @pytest.mark.asyncio
    async def test_create_with_parent(self, client, db_session):
        parent = _make_version(version=3)
        db_session.add(parent)
        db_session.commit()
        db_session.refresh(parent)

        resp = await client.post(
            "/api/prompts/versions",
            json={
                "name": "Child Prompt",
                "prompt": "Better version",
                "parent_version_id": parent.id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == 4

    @pytest.mark.asyncio
    async def test_create_with_tags(self, client, db_session):
        resp = await client.post(
            "/api/prompts/versions",
            json={
                "name": "Tagged",
                "prompt": "test",
                "tags": ["v2", "production"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tags"] is not None


class TestGetPromptVersion:
    @pytest.mark.asyncio
    async def test_get_existing(self, client, db_session):
        v = _make_version()
        db_session.add(v)
        db_session.commit()
        db_session.refresh(v)

        resp = await client.get(f"/api/prompts/versions/{v.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Prompt"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, client, db_session):
        resp = await client.get("/api/prompts/versions/no-such-id")
        assert resp.status_code == 404


class TestUpdatePromptVersion:
    @pytest.mark.asyncio
    async def test_update_name(self, client, db_session):
        v = _make_version()
        db_session.add(v)
        db_session.commit()
        db_session.refresh(v)

        resp = await client.patch(
            f"/api/prompts/versions/{v.id}",
            json={"name": "Updated Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_active(self, client, db_session):
        v = _make_version()
        db_session.add(v)
        db_session.commit()
        db_session.refresh(v)

        resp = await client.patch(
            f"/api/prompts/versions/{v.id}",
            json={"is_active": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, client, db_session):
        resp = await client.patch(
            "/api/prompts/versions/no-id",
            json={"name": "test"},
        )
        assert resp.status_code == 404


class TestDeletePromptVersion:
    @pytest.mark.asyncio
    async def test_delete_soft(self, client, db_session):
        v = _make_version()
        db_session.add(v)
        db_session.commit()
        db_session.refresh(v)

        resp = await client.delete(f"/api/prompts/versions/{v.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        # Verify soft delete via a new query (expire cache first)
        db_session.expire_all()
        refreshed = db_session.get(PromptVersion, v.id)
        assert refreshed.is_active is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, client, db_session):
        resp = await client.delete("/api/prompts/versions/no-id")
        assert resp.status_code == 404


class TestExperiments:
    def _setup_prompts(self, db_session):
        c = _make_version(name="Control")
        v = _make_version(name="Variant")
        db_session.add(c)
        db_session.add(v)
        db_session.commit()
        db_session.refresh(c)
        db_session.refresh(v)
        return c, v

    @pytest.mark.asyncio
    async def test_list_experiments_empty(self, client, db_session):
        resp = await client.get("/api/prompts/experiments")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_experiment(self, client, db_session):
        c, v = self._setup_prompts(db_session)

        resp = await client.post(
            "/api/prompts/experiments",
            json={
                "name": "A/B Test 1",
                "control_prompt_id": c.id,
                "variant_prompt_id": v.id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "A/B Test 1"
        assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_create_experiment_invalid_prompts(self, client, db_session):
        resp = await client.post(
            "/api/prompts/experiments",
            json={
                "name": "Bad Test",
                "control_prompt_id": "no-id",
                "variant_prompt_id": "no-id",
            },
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_get_experiment(self, client, db_session):
        c, v = self._setup_prompts(db_session)
        exp = PromptExperiment(
            name="Test Exp",
            control_prompt_id=c.id,
            variant_prompt_id=v.id,
            variant_traffic_percent=50,
        )
        db_session.add(exp)
        db_session.commit()
        db_session.refresh(exp)

        resp = await client.get(f"/api/prompts/experiments/{exp.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Exp"
        assert data["control_prompt"] is not None
        assert data["variant_prompt"] is not None

    @pytest.mark.asyncio
    async def test_update_experiment(self, client, db_session):
        c, v = self._setup_prompts(db_session)
        exp = PromptExperiment(
            name="Test Exp",
            control_prompt_id=c.id,
            variant_prompt_id=v.id,
        )
        db_session.add(exp)
        db_session.commit()
        db_session.refresh(exp)

        resp = await client.patch(
            f"/api/prompts/experiments/{exp.id}",
            json={"name": "Updated Exp", "status": "completed"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Exp"
        assert resp.json()["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_list_filter_by_status(self, client, db_session):
        c, v = self._setup_prompts(db_session)
        e1 = PromptExperiment(name="Running", control_prompt_id=c.id, variant_prompt_id=v.id, status="running")
        e2 = PromptExperiment(name="Completed", control_prompt_id=c.id, variant_prompt_id=v.id, status="completed")
        db_session.add(e1)
        db_session.add(e2)
        db_session.commit()

        resp = await client.get("/api/prompts/experiments?status=running")
        assert resp.status_code == 200
        data = resp.json()
        assert all(e["status"] == "running" for e in data)
        assert len(data) >= 1
        assert any(e["name"] == "Running" for e in data)


class TestAssignExperiment:
    @pytest.mark.asyncio
    async def test_assign_no_running_experiments(self, client, db_session):
        # Use a type that has no experiments
        resp = await client.post("/api/prompts/assign?prompt_type=nonexistent_type_xyz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["experiment_id"] is None

    @pytest.mark.asyncio
    async def test_assign_with_experiment(self, client, db_session):
        c = _make_version(name="Control", prompt_type="system")
        v = _make_version(name="Variant", prompt_type="system")
        db_session.add(c)
        db_session.add(v)
        db_session.commit()
        db_session.refresh(c)
        db_session.refresh(v)

        exp = PromptExperiment(
            name="Live Test",
            control_prompt_id=c.id,
            variant_prompt_id=v.id,
            status="running",
            prompt_type="system",
            variant_traffic_percent=100,  # always variant for deterministic test
        )
        db_session.add(exp)
        db_session.commit()

        resp = await client.post("/api/prompts/assign?prompt_type=system")
        assert resp.status_code == 200
        data = resp.json()
        assert data["experiment_id"] is not None
        assert data["variant"] in ("control", "variant")

    @pytest.mark.asyncio
    async def test_create_assignment(self, client, db_session):
        from models import Build
        c = _make_version()
        v = _make_version()
        db_session.add(c)
        db_session.add(v)
        db_session.commit()
        db_session.refresh(c)
        db_session.refresh(v)

        # Need a real Build row for the FK constraint on build_id
        build = Build(prompt="test", status="deployed", app_name="Test")
        db_session.add(build)
        db_session.commit()
        db_session.refresh(build)

        exp = PromptExperiment(
            name="Test",
            control_prompt_id=c.id,
            variant_prompt_id=v.id,
        )
        db_session.add(exp)
        db_session.commit()
        db_session.refresh(exp)

        resp = await client.post(
            f"/api/prompts/assignments?experiment_id={exp.id}&build_id={build.id}&variant=control",
        )
        # Endpoint creates an ExperimentAssignment; 200 means success
        assert resp.status_code == 200


class TestRecordResult:
    @pytest.mark.asyncio
    async def test_record_result(self, client, db_session):
        c = _make_version()
        v = _make_version()
        db_session.add(c)
        db_session.add(v)
        db_session.commit()
        db_session.refresh(c)
        db_session.refresh(v)

        exp = PromptExperiment(
            name="Test",
            control_prompt_id=c.id,
            variant_prompt_id=v.id,
        )
        db_session.add(exp)
        db_session.commit()
        db_session.refresh(exp)

        assignment = ExperimentAssignment(
            experiment_id=exp.id,
            build_id="test-build",
            assigned_variant="control",
        )
        db_session.add(assignment)
        db_session.commit()

        resp = await client.post(
            f"/api/prompts/experiments/{exp.id}/record-result?build_id=test-build&success=true",
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "recorded"

    @pytest.mark.asyncio
    async def test_record_result_no_experiment(self, client, db_session):
        resp = await client.post(
            "/api/prompts/experiments/no-id/record-result?build_id=x&success=true",
        )
        assert resp.status_code == 404


class TestCalculateConfidence:
    def test_confidence_identical_rates(self):
        from routers.prompts import calculate_confidence
        result = calculate_confidence(50, 100, 50, 100)
        assert result == 0.0

    def test_confidence_different_rates(self):
        from routers.prompts import calculate_confidence
        result = calculate_confidence(30, 100, 70, 100)
        assert result > 0.0

    def test_confidence_zero_pool(self):
        from routers.prompts import calculate_confidence
        result = calculate_confidence(0, 100, 0, 100)
        assert result == 0.0
