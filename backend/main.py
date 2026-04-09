"""Buildy Backend — FastAPI app entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import settings
from database import create_db_and_tables
from routers import builds, gallery, prompts, twitter
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


limiter = Limiter(key_func=get_remote_address)

tags_metadata = [
    {
        "name": "Health",
        "description": "Service health checks and diagnostics.",
    },
    {
        "name": "Builds",
        "description": "Create, read, modify, deploy, and manage app builds. "
        "Supports text-to-app, screenshot-to-app, remix, cloud deploy, and more.",
    },
    {
        "name": "Gallery",
        "description": "Public gallery of deployed apps. Browse and discover apps built by the community.",
    },
    {
        "name": "Twitter",
        "description": "Twitter integration — mention polling, scraper ingestion, and auto-reply. "
        "Builddy watches for Twitter mentions and automatically builds apps from them.",
    },
    {
        "name": "Prompts",
        "description": "Prompt version control and A/B testing. Manage prompt versions, "
        "run experiments to compare prompt effectiveness, and track success metrics.",
    },
    {
        "name": "Proxy",
        "description": "Reverse proxy for running app backends. Forwards API requests to "
        "the live Express process of a deployed build.",
    },
]

app = FastAPI(
    title="Builddy",
    description=(
        "# Builddy API\n\n"
        "AI-powered app builder that turns natural-language prompts and tweets into "
        "deployed web apps in minutes.\n\n"
        "## Quick Start\n"
        "1. **Create a build** — `POST /api/builds` with a text prompt, or "
        "`POST /api/builds/from-image` with a screenshot.\n"
        "2. **Stream progress** — `GET /api/builds/{id}/stream` (SSE) for real-time status.\n"
        "3. **View the app** — Once deployed, the app is served at `/apps/{id}/`.\n"
        "4. **Iterate** — Modify, remix, retry, or cloud-deploy your build.\n\n"
        "## Features\n"
        "- Text-to-app and screenshot-to-app pipelines\n"
        "- Real-time SSE streaming of build progress\n"
        "- Multi-file fullstack builds with auto-deploy\n"
        "- Cloud deployment to Railway or Render\n"
        "- Twitter bot integration (mention → build → reply)\n"
        "- Prompt version control & A/B testing\n"
        "- Gallery of deployed apps\n"
    ),
    version="1.0.0",
    contact={
        "name": "Builddy",
        "url": "https://github.com/builddy",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Cache-Control"],
)

# Mount routers
app.include_router(builds.router)
app.include_router(twitter.router)
app.include_router(gallery.router)
app.include_router(prompts.router)


# Health check
@app.get(
    "/api/health",
    tags=["Health"],
    summary="Health check",
    description="Returns the service health status, name, and version. "
    "Use this to verify the API is up and running.",
    response_model=dict,
    responses={
        200: {"description": "Service is healthy"},
        500: {"description": "Service is unhealthy"},
    },
)
async def health():
    return {"status": "ok", "service": "buildy", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Reverse proxy: forward /apps/{build_id}/api/* to the running Express process
# IMPORTANT — this MUST be registered before the catch-all static mount.
# ---------------------------------------------------------------------------

@app.api_route(
    "/apps/{build_id}/api/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Proxy"],
    summary="Reverse proxy to app backend",
    description="Forwards API requests to the running Express process for a deployed build. "
    "Used when builds include a backend that needs its own API endpoints.",
    responses={
        200: {"description": "Request successfully proxied"},
        502: {"description": "Proxy error — upstream server error"},
        503: {"description": "App backend not available — process not running"},
        504: {"description": "App backend timed out"},
    },
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


@app.get(
    "/api/processes",
    tags=["Health"],
    summary="List running processes",
    description="Returns a list of all currently running app preview processes (Express servers).",
    response_model=dict,
)
async def list_processes():
    """List all running app preview processes."""
    return {"processes": process_manager.list_running()}


# Serve thumbnails directly (before the html=True static mount which mangles non-HTML)
DEPLOYED_DIR = Path(__file__).parent / "deployed"
DEPLOYED_DIR.mkdir(parents=True, exist_ok=True)


@app.get(
    "/apps/{build_id}/thumbnail.png",
    tags=["Builds"],
    summary="Get app thumbnail",
    description="Serves the screenshot thumbnail image for a deployed build. "
    "Returns a PNG image if available, or a 404 if no thumbnail exists.",
    responses={
        200: {"description": "PNG thumbnail image", "content": {"image/png": {}}},
        404: {"description": "No thumbnail available for this build"},
    },
)
async def get_thumbnail(build_id: str):
    """Serve the app screenshot thumbnail."""
    thumb = DEPLOYED_DIR / build_id / "thumbnail.png"
    if thumb.exists():
        return Response(content=thumb.read_bytes(), media_type="image/png")
    return JSONResponse(status_code=404, content={"error": "No thumbnail"})


# Serve deployed apps as static files
app.mount("/apps", StaticFiles(directory=str(DEPLOYED_DIR), html=True), name="deployed-apps")
