"""API routes for prompt version control and A/B testing."""

import json
import math
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from models import PromptVersion, PromptExperiment, ExperimentAssignment, Build
from database import get_session

router = APIRouter(prefix="/api/prompts", tags=["Prompts"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class PromptVersionCreate(BaseModel):
    name: str
    prompt: str
    prompt_type: str = "system"
    parent_version_id: Optional[str] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None


class PromptVersionUpdate(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class PromptExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    prompt_type: str = "system"
    control_prompt_id: str
    variant_prompt_id: str
    variant_traffic_percent: int = 50


class PromptExperimentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    variant_traffic_percent: Optional[int] = None
    status: Optional[str] = None


# ── Prompt Versions ───────────────────────────────────────────────────────────

@router.get("/versions")
def list_prompt_versions(
    prompt_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 50,
    session: Session = Depends(get_session),
):
    """List all prompt versions with optional filtering."""
    query = select(PromptVersion).order_by(PromptVersion.created_at.desc())

    if prompt_type:
        query = query.where(PromptVersion.prompt_type == prompt_type)
    if is_active is not None:
        query = query.where(PromptVersion.is_active == is_active)

    query = query.limit(limit)
    versions = session.exec(query).all()

    # Calculate success rate for each
    results = []
    for v in versions:
        d = v.model_dump()
        d["success_rate"] = v.success_count / v.total_builds if v.total_builds > 0 else None
        results.append(d)

    return results


@router.post("/versions")
def create_prompt_version(
    data: PromptVersionCreate,
    session: Session = Depends(get_session),
):
    """Create a new prompt version."""
    # Determine version number
    version = 1
    if data.parent_version_id:
        parent = session.get(PromptVersion, data.parent_version_id)
        if parent:
            version = parent.version + 1

    version = PromptVersion(
        name=data.name,
        prompt=data.prompt,
        prompt_type=data.prompt_type,
        version=version,
        parent_version_id=data.parent_version_id,
        tags=json.dumps(data.tags) if data.tags else None,
        notes=data.notes,
    )

    session.add(version)
    session.commit()
    session.refresh(version)

    return version


@router.get("/versions/{version_id}")
def get_prompt_version(version_id: str, session: Session = Depends(get_session)):
    """Get a specific prompt version."""
    version = session.get(PromptVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    return version


@router.patch("/versions/{version_id}")
def update_prompt_version(
    version_id: str,
    data: PromptVersionUpdate,
    session: Session = Depends(get_session),
):
    """Update a prompt version."""
    version = session.get(PromptVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Prompt version not found")

    if data.name is not None:
        version.name = data.name
    if data.prompt is not None:
        version.prompt = data.prompt
    if data.tags is not None:
        version.tags = json.dumps(data.tags)
    if data.notes is not None:
        version.notes = data.notes
    if data.is_active is not None:
        version.is_active = data.is_active

    version.updated_at = datetime.now(UTC)
    session.add(version)
    session.commit()
    session.refresh(version)

    return version


@router.delete("/versions/{version_id}")
def delete_prompt_version(version_id: str, session: Session = Depends(get_session)):
    """Delete a prompt version (soft delete by setting is_active=False)."""
    version = session.get(PromptVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Prompt version not found")

    version.is_active = False
    version.updated_at = datetime.now(UTC)
    session.add(version)
    session.commit()

    return {"status": "deleted"}


# ── Prompt Experiments (A/B Tests) ────────────────────────────────────────────

@router.get("/experiments")
def list_experiments(
    status: Optional[str] = None,
    limit: int = 50,
    session: Session = Depends(get_session),
):
    """List all A/B experiments."""
    query = select(PromptExperiment).order_by(PromptExperiment.created_at.desc())

    if status:
        query = query.where(PromptExperiment.status == status)

    query = query.limit(limit)
    experiments = session.exec(query).all()

    # Calculate success rates
    results = []
    for exp in experiments:
        d = exp.model_dump()
        d["control_success_rate"] = (
            exp.control_successes / exp.control_builds
            if exp.control_builds > 0 else None
        )
        d["variant_success_rate"] = (
            exp.variant_successes / exp.variant_builds
            if exp.variant_builds > 0 else None
        )
        results.append(d)

    return results


@router.post("/experiments")
def create_experiment(
    data: PromptExperimentCreate,
    session: Session = Depends(get_session),
):
    """Create a new A/B experiment."""
    # Validate prompt IDs
    control = session.get(PromptVersion, data.control_prompt_id)
    variant = session.get(PromptVersion, data.variant_prompt_id)

    if not control or not variant:
        raise HTTPException(status_code=400, detail="Invalid prompt IDs")

    experiment = PromptExperiment(
        name=data.name,
        description=data.description,
        prompt_type=data.prompt_type,
        control_prompt_id=data.control_prompt_id,
        variant_prompt_id=data.variant_prompt_id,
        variant_traffic_percent=data.variant_traffic_percent,
    )

    session.add(experiment)
    session.commit()
    session.refresh(experiment)

    return experiment


@router.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: str, session: Session = Depends(get_session)):
    """Get a specific experiment with details."""
    experiment = session.get(PromptExperiment, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    # Get the prompt versions
    control = session.get(PromptVersion, experiment.control_prompt_id)
    variant = session.get(PromptVersion, experiment.variant_prompt_id)

    return {
        **experiment.model_dump(),
        "control_prompt": control,
        "variant_prompt": variant,
        "control_success_rate": (
            experiment.control_successes / experiment.control_builds
            if experiment.control_builds > 0 else None
        ),
        "variant_success_rate": (
            experiment.variant_successes / experiment.variant_builds
            if experiment.variant_builds > 0 else None
        ),
    }


@router.patch("/experiments/{experiment_id}")
def update_experiment(
    experiment_id: str,
    data: PromptExperimentUpdate,
    session: Session = Depends(get_session),
):
    """Update an experiment."""
    experiment = session.get(PromptExperiment, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if data.name is not None:
        experiment.name = data.name
    if data.description is not None:
        experiment.description = data.description
    if data.variant_traffic_percent is not None:
        experiment.variant_traffic_percent = data.variant_traffic_percent
    if data.status is not None:
        experiment.status = data.status
        if data.status == "completed":
            experiment.completed_at = datetime.now(UTC)

    experiment.updated_at = datetime.now(UTC)
    session.add(experiment)
    session.commit()
    session.refresh(experiment)

    return experiment


@router.post("/experiments/{experiment_id}/record-result")
def record_experiment_result(
    experiment_id: str,
    build_id: str,
    success: bool,
    session: Session = Depends(get_session),
):
    """Record the result of a build in an experiment."""
    experiment = session.get(PromptExperiment, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    # Find the assignment
    assignment = session.exec(
        select(ExperimentAssignment).where(
            ExperimentAssignment.experiment_id == experiment_id,
            ExperimentAssignment.build_id == build_id,
        )
    ).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Update counts
    if assignment.assigned_variant == "control":
        experiment.control_builds += 1
        if success:
            experiment.control_successes += 1
    else:
        experiment.variant_builds += 1
        if success:
            experiment.variant_successes += 1

    # Check for statistical significance (simplified z-test)
    if experiment.control_builds >= 30 and experiment.variant_builds >= 30:
        experiment.confidence_score = calculate_confidence(
            experiment.control_successes,
            experiment.control_builds,
            experiment.variant_successes,
            experiment.variant_builds,
        )

    experiment.updated_at = datetime.now(UTC)
    session.add(experiment)
    session.commit()

    return {"status": "recorded"}


def calculate_confidence(
    control_successes: int,
    control_total: int,
    variant_successes: int,
    variant_total: int,
) -> float:
    """Calculate confidence score using a simplified z-test."""
    p1 = control_successes / control_total
    p2 = variant_successes / variant_total
    p_pooled = (control_successes + variant_successes) / (control_total + variant_total)

    if p_pooled == 0 or p_pooled == 1:
        return 0.0

    se = math.sqrt(p_pooled * (1 - p_pooled) * (1/control_total + 1/variant_total))
    if se == 0:
        return 0.0

    z = abs(p1 - p2) / se
    # Convert z-score to approximate confidence (simplified)
    # For a proper implementation, use scipy.stats.norm.cdf
    confidence = min(0.99, 1 - math.exp(-0.5 * z * z))

    return round(confidence, 3)


# ── Experiment Assignment ─────────────────────────────────────────────────────

@router.post("/assign")
def assign_experiment(
    prompt_type: str,
    session: Session = Depends(get_session),
):
    """Assign a build to an experiment and return the prompt to use."""
    # Find running experiments for this prompt type
    experiments = session.exec(
        select(PromptExperiment).where(
            PromptExperiment.prompt_type == prompt_type,
            PromptExperiment.status == "running",
        )
    ).all()

    if not experiments:
        return {"experiment_id": None, "prompt_id": None, "variant": None}

    # Pick one experiment (could be weighted by traffic)
    import random
    experiment = random.choice(experiments)

    # Determine variant
    variant = "variant" if random.randint(1, 100) <= experiment.variant_traffic_percent else "control"

    return {
        "experiment_id": experiment.id,
        "prompt_id": (
            experiment.variant_prompt_id if variant == "variant"
            else experiment.control_prompt_id
        ),
        "variant": variant,
    }


@router.post("/assignments")
def create_assignment(
    experiment_id: str,
    build_id: str,
    variant: str,
    session: Session = Depends(get_session),
):
    """Record an experiment assignment for a build."""
    assignment = ExperimentAssignment(
        experiment_id=experiment_id,
        build_id=build_id,
        assigned_variant=variant,
    )
    session.add(assignment)
    session.commit()

    return assignment
