"""Buildy Backend — FastAPI app entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from database import create_db_and_tables
from routers import builds, twitter, gallery
from services.deployer import ensure_deployed_dir

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("Buildy starting up...")
    create_db_and_tables()
    ensure_deployed_dir()
    logger.info("Database tables created, deployed dir ready")
    yield
    logger.info("Buildy shutting down...")


app = FastAPI(
    title="Buildy",
    description="AI-powered app builder that turns tweets into deployed web apps",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(builds.router)
app.include_router(twitter.router)
app.include_router(gallery.router)


# Health check
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "buildy", "version": "1.0.0"}


# Serve deployed apps as static files
DEPLOYED_DIR = Path(__file__).parent / "deployed"
DEPLOYED_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/apps", StaticFiles(directory=str(DEPLOYED_DIR), html=True), name="deployed-apps")
