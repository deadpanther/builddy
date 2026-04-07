"""Code Autopsy -- FastAPI main app"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, update

from config import settings
from database import init_db, async_session, Autopsy, Evidence
from agent.forensic import ForensicAnalyst
from agent.reviver import RevivalPlanner


# Store active analyses and their subscribers
active_analyses: dict = {}  # autopsy_id -> list of websockets


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Code Autopsy", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AutopsyRequest(BaseModel):
    repo_url: str
    github_token: Optional[str] = None


class AutopsyResponse(BaseModel):
    autopsy_id: str
    repo_url: str
    status: str


@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "Code Autopsy", "version": "1.0.0"}


@app.post("/api/autopsy", response_model=AutopsyResponse)
async def create_autopsy(req: AutopsyRequest):
    autopsy_id = uuid.uuid4().hex[:12]

    # Extract repo name from URL
    repo_name = req.repo_url.rstrip("/").split("/")[-1].replace(".git", "")

    async with async_session() as session:
        autopsy = Autopsy(
            id=autopsy_id,
            repo_url=req.repo_url,
            repo_name=repo_name,
            status="pending",
        )
        session.add(autopsy)
        await session.commit()

    # Start analysis in background
    asyncio.create_task(run_autopsy(autopsy_id, req.repo_url, req.github_token))

    return AutopsyResponse(
        autopsy_id=autopsy_id,
        repo_url=req.repo_url,
        status="pending"
    )


async def run_autopsy(autopsy_id: str, repo_url: str, github_token: Optional[str] = None):
    """Background task to run the full forensic analysis"""
    analyst = ForensicAnalyst(autopsy_id, repo_url, github_token=github_token)

    async def progress(phase: str, message: str):
        # Save evidence to DB
        async with async_session() as session:
            evidence = Evidence(
                id=uuid.uuid4().hex[:12],
                autopsy_id=autopsy_id,
                phase=phase,
                observation=message,
            )
            session.add(evidence)

            if phase == "cloning":
                await session.execute(
                    update(Autopsy).where(Autopsy.id == autopsy_id).values(status="cloning")
                )
            elif phase == "analyzing":
                await session.execute(
                    update(Autopsy).where(Autopsy.id == autopsy_id).values(status="analyzing")
                )
            elif phase == "complete":
                await session.execute(
                    update(Autopsy).where(Autopsy.id == autopsy_id).values(status="complete")
                )
            elif phase == "error":
                await session.execute(
                    update(Autopsy).where(Autopsy.id == autopsy_id).values(
                        status="failed", error_message=message
                    )
                )
            await session.commit()

        # Broadcast to WebSocket subscribers
        if autopsy_id in active_analyses:
            payload = json.dumps({"phase": phase, "message": message})
            dead = []
            for ws in active_analyses[autopsy_id]:
                try:
                    await ws.send_text(payload)
                except:
                    dead.append(ws)
            for ws in dead:
                active_analyses[autopsy_id].remove(ws)

    try:
        # Phase 1: Clone
        await analyst.clone_repo(progress_callback=progress)

        # Phase 2-3: Analyze
        report = await analyst.analyze(progress_callback=progress)

        if report:
            certificate = analyst.generate_death_certificate(report)

            async with async_session() as session:
                await session.execute(
                    update(Autopsy).where(Autopsy.id == autopsy_id).values(
                        status="complete",
                        cause_of_death=report.get("cause_of_death"),
                        contributing_factors=report.get("contributing_factors", []),
                        timeline=report.get("timeline", []),
                        fatal_commits=report.get("fatal_commits", []),
                        findings=report.get("findings", {}),
                        lessons_learned=report.get("lessons_learned", []),
                        death_certificate=certificate,
                        completed_at=datetime.utcnow(),
                    )
                )
                await session.commit()

            # Send final report to WebSocket subscribers
            if autopsy_id in active_analyses:
                payload = json.dumps({"phase": "complete", "report": report, "certificate": certificate})
                for ws in active_analyses[autopsy_id]:
                    try:
                        await ws.send_text(payload)
                    except:
                        pass
        else:
            await progress("error", "Analysis did not produce a report")

    except Exception as e:
        await progress("error", str(e)[:500])


@app.get("/api/autopsy/{autopsy_id}")
async def get_autopsy(autopsy_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(Autopsy).where(Autopsy.id == autopsy_id)
        )
        autopsy = result.scalar_one_or_none()
        if not autopsy:
            raise HTTPException(404, "Autopsy not found")

        cert = autopsy.death_certificate or {}
        health_score = cert.get("health_score")
        prognosis = cert.get("prognosis")

        return {
            "id": autopsy.id,
            "repo_url": autopsy.repo_url,
            "repo_name": autopsy.repo_name,
            "status": autopsy.status,
            "cause_of_death": autopsy.cause_of_death,
            "contributing_factors": autopsy.contributing_factors,
            "timeline": autopsy.timeline,
            "fatal_commits": autopsy.fatal_commits,
            "findings": autopsy.findings,
            "health_score": health_score,
            "prognosis": prognosis,
            "lessons_learned": autopsy.lessons_learned,
            "error_message": autopsy.error_message,
            "created_at": autopsy.created_at.isoformat() if autopsy.created_at else None,
            "completed_at": autopsy.completed_at.isoformat() if autopsy.completed_at else None,
            "revival_status": autopsy.revival_status,
        }


@app.get("/api/autopsy/{autopsy_id}/certificate")
async def get_certificate(autopsy_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(Autopsy).where(Autopsy.id == autopsy_id)
        )
        autopsy = result.scalar_one_or_none()
        if not autopsy:
            raise HTTPException(404, "Autopsy not found")
        if not autopsy.death_certificate:
            raise HTTPException(404, "Certificate not ready yet")
        return autopsy.death_certificate


@app.get("/api/autopsies")
async def list_autopsies():
    async with async_session() as session:
        result = await session.execute(
            select(Autopsy).order_by(Autopsy.created_at.desc()).limit(20)
        )
        autopsies = result.scalars().all()
        return [
            {
                "id": a.id,
                "repo_name": a.repo_name,
                "repo_url": a.repo_url,
                "status": a.status,
                "cause_of_death": a.cause_of_death,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in autopsies
        ]


@app.get("/api/autopsy/{autopsy_id}/evidence")
async def get_evidence(autopsy_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(Evidence).where(Evidence.autopsy_id == autopsy_id).order_by(Evidence.created_at)
        )
        evidence = result.scalars().all()
        return [
            {
                "id": e.id,
                "phase": e.phase,
                "tool_name": e.tool_name,
                "tool_input": e.tool_input,
                "observation": e.observation,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in evidence
        ]


@app.post("/api/autopsy/{autopsy_id}/revive")
async def start_revival(autopsy_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(Autopsy).where(Autopsy.id == autopsy_id)
        )
        autopsy = result.scalar_one_or_none()
        if not autopsy:
            raise HTTPException(404, "Autopsy not found")
        if autopsy.status != "complete":
            raise HTTPException(400, "Autopsy must be complete before revival")
        if autopsy.revival_status == "generating":
            return {"autopsy_id": autopsy_id, "revival_status": "generating"}

        await session.execute(
            update(Autopsy).where(Autopsy.id == autopsy_id).values(
                revival_status="generating",
                revival_plan=None,
                revival_features=None,
                revival_created_at=None,
            )
        )
        await session.commit()

    asyncio.create_task(run_revive(autopsy_id))
    return {"autopsy_id": autopsy_id, "revival_status": "generating"}


async def run_revive(autopsy_id: str):
    """Background task to generate the revival plan from existing autopsy findings."""
    async def progress(phase: str, message: str):
        # Save evidence to DB
        async with async_session() as session:
            evidence = Evidence(
                id=uuid.uuid4().hex[:12],
                autopsy_id=autopsy_id,
                phase=phase,
                observation=message,
            )
            session.add(evidence)
            await session.commit()

        # Broadcast to WebSocket subscribers
        if autopsy_id in active_analyses:
            payload = json.dumps({"phase": phase, "message": message})
            dead = []
            for ws in active_analyses[autopsy_id]:
                try:
                    await ws.send_text(payload)
                except:
                    dead.append(ws)
            for ws in dead:
                active_analyses[autopsy_id].remove(ws)

    try:
        # Load existing autopsy data
        async with async_session() as session:
            result = await session.execute(
                select(Autopsy).where(Autopsy.id == autopsy_id)
            )
            autopsy = result.scalar_one_or_none()

        if not autopsy:
            return

        cert = autopsy.death_certificate or {}
        autopsy_data = {
            "repo_url": autopsy.repo_url,
            "repo_name": autopsy.repo_name,
            "cause_of_death": autopsy.cause_of_death,
            "contributing_factors": autopsy.contributing_factors or [],
            "timeline": autopsy.timeline or [],
            "fatal_commits": autopsy.fatal_commits or [],
            "findings": autopsy.findings or {},
            "health_score": cert.get("health_score"),
            "prognosis": cert.get("prognosis"),
            "lessons_learned": autopsy.lessons_learned or [],
        }

        planner = RevivalPlanner(autopsy_id, autopsy_data)
        revival_plan, revival_features = await planner.generate(progress_callback=progress)

        async with async_session() as session:
            await session.execute(
                update(Autopsy).where(Autopsy.id == autopsy_id).values(
                    revival_status="complete",
                    revival_plan=revival_plan,
                    revival_features=revival_features,
                    revival_created_at=datetime.utcnow(),
                )
            )
            await session.commit()

        # Broadcast completion
        if autopsy_id in active_analyses:
            payload = json.dumps({
                "phase": "revival_complete",
                "revival_plan": revival_plan,
                "revival_features": revival_features,
            })
            for ws in active_analyses[autopsy_id]:
                try:
                    await ws.send_text(payload)
                except:
                    pass

    except Exception as e:
        await progress("error", f"Revival failed: {str(e)[:500]}")
        async with async_session() as session:
            await session.execute(
                update(Autopsy).where(Autopsy.id == autopsy_id).values(
                    revival_status="failed"
                )
            )
            await session.commit()


@app.get("/api/autopsy/{autopsy_id}/revival")
async def get_revival(autopsy_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(Autopsy).where(Autopsy.id == autopsy_id)
        )
        autopsy = result.scalar_one_or_none()
        if not autopsy:
            raise HTTPException(404, "Autopsy not found")
        if not autopsy.revival_status:
            raise HTTPException(404, "Revival not started")
        return {
            "revival_status": autopsy.revival_status,
            "revival_plan": autopsy.revival_plan,
            "revival_features": autopsy.revival_features,
            "revival_created_at": autopsy.revival_created_at.isoformat() if autopsy.revival_created_at else None,
        }


@app.websocket("/api/autopsy/{autopsy_id}/stream")
async def stream_autopsy(websocket: WebSocket, autopsy_id: str):
    await websocket.accept()

    if autopsy_id not in active_analyses:
        active_analyses[autopsy_id] = []
    active_analyses[autopsy_id].append(websocket)

    try:
        # Send current status first
        async with async_session() as session:
            result = await session.execute(
                select(Autopsy).where(Autopsy.id == autopsy_id)
            )
            autopsy = result.scalar_one_or_none()
            if autopsy:
                await websocket.send_text(json.dumps({
                    "phase": "status",
                    "status": autopsy.status,
                    "cause_of_death": autopsy.cause_of_death,
                }))

        # Keep alive until disconnect
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if autopsy_id in active_analyses and websocket in active_analyses[autopsy_id]:
            active_analyses[autopsy_id].remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
