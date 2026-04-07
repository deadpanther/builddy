"""Buildy Backend — FastAPI app entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from config import settings
from database import create_db_and_tables
from routers import builds, twitter, gallery
from routers.twitter import start_twitter_poll, stop_twitter_poll
from services.deployer import ensure_deployed_dir
from services.process_manager import process_manager
from services.twitter_scraper import scraper as twitter_scraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Quiet down noisy loggers so pipeline logs are visible
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("services.twitter").setLevel(logging.CRITICAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("Buildy starting up...")
    create_db_and_tables()
    ensure_deployed_dir()
    await process_manager.start_cleanup_loop()
    await start_twitter_poll()
    if settings.ENABLE_TWITTER_SCRAPER:
        twitter_scraper.start()
        logger.info("Twitter scraper started")
    else:
        logger.info("Twitter scraper disabled via ENABLE_TWITTER_SCRAPER=false")
    logger.info("Database tables created, deployed dir ready")
    yield
    logger.info("Buildy shutting down...")
    twitter_scraper.stop()
    await stop_twitter_poll()
    await process_manager.stop_all()


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


# ---------------------------------------------------------------------------
# Reverse proxy: forward /apps/{build_id}/api/* to the running Express process
# IMPORTANT — this MUST be registered before the catch-all static mount.
# ---------------------------------------------------------------------------

@app.api_route(
    "/apps/{build_id}/api/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy_app_api(build_id: str, path: str, request: Request):
    """Reverse proxy API requests to the running Express process for a build."""
    try:
        port = await process_manager.ensure_running(build_id)
    except RuntimeError as exc:
        return JSONResponse(
            status_code=503,
            content={"error": f"App backend not available: {exc}"},
        )

    # Build the target URL
    target_url = f"http://127.0.0.1:{port}/api/{path}"

    # Forward query params
    if request.query_params:
        target_url += f"?{request.query_params}"

    # Forward the request
    try:
        body = await request.body()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers={
                    k: v
                    for k, v in request.headers.items()
                    if k.lower() not in ("host", "connection", "transfer-encoding")
                },
                content=body if body else None,
            )

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={"error": "App backend timed out"},
        )
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"error": f"Proxy error: {str(exc)}"},
        )


@app.get("/api/processes")
async def list_processes():
    """List all running app preview processes."""
    return {"processes": process_manager.list_running()}


# Serve thumbnails directly (before the html=True static mount which mangles non-HTML)
DEPLOYED_DIR = Path(__file__).parent / "deployed"
DEPLOYED_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/apps/{build_id}/thumbnail.png")
async def get_thumbnail(build_id: str):
    """Serve the app screenshot thumbnail."""
    thumb = DEPLOYED_DIR / build_id / "thumbnail.png"
    if thumb.exists():
        return Response(content=thumb.read_bytes(), media_type="image/png")
    return JSONResponse(status_code=404, content={"error": "No thumbnail"})


# Serve deployed apps as static files
app.mount("/apps", StaticFiles(directory=str(DEPLOYED_DIR), html=True), name="deployed-apps")
