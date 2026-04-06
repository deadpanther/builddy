"""Process manager for live Express.js app previews."""

import asyncio
import logging
import os
import signal
import time
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

DEPLOYED_DIR = Path(__file__).parent.parent / "deployed"
BASE_PORT = 9100  # Starting port for Express processes
MAX_CONCURRENT = 20
IDLE_TIMEOUT_SECONDS = 1800  # 30 minutes
NPM_INSTALL_TIMEOUT = 60  # seconds
STARTUP_WAIT_SECONDS = 5
GRACEFUL_SHUTDOWN_SECONDS = 5
CLEANUP_INTERVAL_SECONDS = 60


@dataclass
class AppProcess:
    """State for a single running Express.js app."""

    build_id: str
    port: int
    process: asyncio.subprocess.Process | None = None
    started_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    status: str = "starting"  # "starting" | "running" | "stopped" | "error"
    error: str | None = None


class ProcessManager:
    """Singleton that manages all running Express.js preview processes."""

    def __init__(self) -> None:
        self._processes: dict[str, AppProcess] = {}
        self._next_port: int = BASE_PORT
        self._ports_in_use: set[int] = set()
        self._cleanup_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Port allocation
    # ------------------------------------------------------------------

    def _allocate_port(self) -> int:
        """Allocate the next available port, reusing freed ports first."""
        # Try to find a freed port below _next_port
        for port in range(BASE_PORT, self._next_port):
            if port not in self._ports_in_use:
                self._ports_in_use.add(port)
                return port

        # Otherwise use the next sequential port
        port = self._next_port
        self._ports_in_use.add(port)
        self._next_port = port + 1
        return port

    def _release_port(self, port: int) -> None:
        """Return a port to the available pool."""
        self._ports_in_use.discard(port)

    # ------------------------------------------------------------------
    # Process lifecycle
    # ------------------------------------------------------------------

    async def start_app(self, build_id: str) -> AppProcess:
        """Start an Express.js app for the given build.

        If the app is already running, updates last_accessed and returns
        the existing process info. Evicts the oldest idle process when
        the concurrency limit is reached.
        """
        # Already running — touch and return
        existing = self._processes.get(build_id)
        if existing is not None and existing.status in ("starting", "running"):
            existing.last_accessed = time.time()
            return existing

        # Enforce concurrency limit
        if len(self._processes) >= MAX_CONCURRENT:
            await self._evict_oldest_idle()

        app_dir = DEPLOYED_DIR / build_id
        if not app_dir.is_dir():
            error_msg = f"Build directory does not exist: {app_dir}"
            logger.error(error_msg)
            app = AppProcess(
                build_id=build_id,
                port=0,
                status="error",
                error=error_msg,
            )
            return app

        port = self._allocate_port()
        app = AppProcess(build_id=build_id, port=port)
        self._processes[build_id] = app

        try:
            # npm install (skip if node_modules already present)
            await self._npm_install(app_dir)

            # Seed database if init-data.js exists and data/app.db doesn't
            await self._seed_database(app_dir)

            # Start the Express server
            env = {**os.environ, "PORT": str(port), "NODE_ENV": "production"}
            server_path = app_dir / "backend" / "server.js"
            if not server_path.exists():
                raise FileNotFoundError(
                    f"Server entry point not found: {server_path}"
                )

            proc = await asyncio.create_subprocess_exec(
                "node",
                str(server_path),
                cwd=str(app_dir),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            app.process = proc

            # Give the server a moment to start
            await asyncio.sleep(STARTUP_WAIT_SECONDS)

            # Check if it crashed during startup
            if proc.returncode is not None:
                stderr_bytes = await proc.stderr.read() if proc.stderr else b""
                stderr_text = stderr_bytes.decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"Server exited immediately with code {proc.returncode}: "
                    f"{stderr_text[:500]}"
                )

            app.status = "running"
            logger.info(
                "Started app %s on port %d (pid %d)",
                build_id,
                port,
                proc.pid,
            )

        except Exception as exc:
            app.status = "error"
            app.error = str(exc)
            self._release_port(port)
            logger.error("Failed to start app %s: %s", build_id, exc)

        return app

    async def stop_app(self, build_id: str) -> None:
        """Stop a running Express.js app gracefully, falling back to SIGKILL."""
        app = self._processes.pop(build_id, None)
        if app is None:
            return

        await self._terminate_process(app)
        self._release_port(app.port)
        logger.info("Stopped app %s (port %d)", build_id, app.port)

    def get_app(self, build_id: str) -> AppProcess | None:
        """Return process info for a build, updating last_accessed."""
        app = self._processes.get(build_id)
        if app is not None:
            app.last_accessed = time.time()
        return app

    def get_port(self, build_id: str) -> int | None:
        """Return the port for a running build, or None."""
        app = self._processes.get(build_id)
        if app is not None and app.status == "running":
            return app.port
        return None

    async def ensure_running(self, build_id: str) -> int:
        """Start the app if not running and return its port.

        Raises RuntimeError if the app cannot be started.
        """
        app = self._processes.get(build_id)
        if app is not None and app.status == "running":
            app.last_accessed = time.time()
            return app.port

        result = await self.start_app(build_id)
        if result.status == "error":
            raise RuntimeError(
                f"Cannot start app {build_id}: {result.error}"
            )
        return result.port

    async def cleanup_idle(self) -> None:
        """Background loop that reaps idle and dead processes."""
        while True:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
                now = time.time()
                to_stop: list[str] = []

                for build_id, app in list(self._processes.items()):
                    # Reap processes that died unexpectedly
                    if (
                        app.process is not None
                        and app.process.returncode is not None
                        and app.status == "running"
                    ):
                        logger.warning(
                            "App %s died unexpectedly (exit code %d)",
                            build_id,
                            app.process.returncode,
                        )
                        to_stop.append(build_id)
                        continue

                    # Reap idle processes
                    idle_seconds = now - app.last_accessed
                    if idle_seconds > IDLE_TIMEOUT_SECONDS:
                        logger.info(
                            "App %s idle for %.0fs, stopping",
                            build_id,
                            idle_seconds,
                        )
                        to_stop.append(build_id)

                for build_id in to_stop:
                    await self.stop_app(build_id)

            except asyncio.CancelledError:
                logger.info("Cleanup loop cancelled")
                break
            except Exception:
                logger.exception("Error in cleanup loop")

    async def start_cleanup_loop(self) -> None:
        """Launch the background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self.cleanup_idle())
            logger.info("Cleanup loop started")

    async def stop_all(self) -> None:
        """Stop every running process (called on server shutdown)."""
        # Cancel the cleanup task first
        if self._cleanup_task is not None and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        build_ids = list(self._processes.keys())
        for build_id in build_ids:
            await self.stop_app(build_id)
        logger.info("All processes stopped")

    def list_running(self) -> list[dict]:
        """Return summary dicts for all tracked processes."""
        now = time.time()
        results: list[dict] = []
        for build_id, app in self._processes.items():
            results.append(
                {
                    "build_id": build_id,
                    "port": app.port,
                    "status": app.status,
                    "uptime_seconds": round(now - app.started_at, 1),
                    "idle_seconds": round(now - app.last_accessed, 1),
                }
            )
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _npm_install(self, app_dir: Path) -> None:
        """Run npm install --production if node_modules is absent."""
        node_modules = app_dir / "node_modules"
        package_json = app_dir / "package.json"

        if node_modules.is_dir() or not package_json.exists():
            return

        logger.info("Running npm install in %s", app_dir)
        try:
            proc = await asyncio.create_subprocess_exec(
                "npm",
                "install",
                "--production",
                cwd=str(app_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=NPM_INSTALL_TIMEOUT
            )
            if proc.returncode != 0:
                stderr_text = stderr_bytes.decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"npm install failed (exit {proc.returncode}): "
                    f"{stderr_text[:500]}"
                )
            logger.info("npm install completed in %s", app_dir)
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(
                f"npm install timed out after {NPM_INSTALL_TIMEOUT}s"
            )

    async def _seed_database(self, app_dir: Path) -> None:
        """Run init-data.js if it exists and the database hasn't been seeded."""
        init_script = app_dir / "init-data.js"
        db_file = app_dir / "data" / "app.db"

        if not init_script.exists() or db_file.exists():
            return

        logger.info("Seeding database via init-data.js in %s", app_dir)
        try:
            proc = await asyncio.create_subprocess_exec(
                "node",
                str(init_script),
                cwd=str(app_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=30
            )
            if proc.returncode != 0:
                stderr_text = stderr_bytes.decode("utf-8", errors="replace")
                logger.warning(
                    "init-data.js failed (exit %d): %s",
                    proc.returncode,
                    stderr_text[:500],
                )
            else:
                logger.info("Database seeded in %s", app_dir)
        except asyncio.TimeoutError:
            proc.kill()
            logger.warning("init-data.js timed out after 30s in %s", app_dir)

    async def _terminate_process(self, app: AppProcess) -> None:
        """Send SIGTERM, wait for graceful shutdown, then SIGKILL if needed."""
        proc = app.process
        if proc is None or proc.returncode is not None:
            app.status = "stopped"
            return

        try:
            proc.send_signal(signal.SIGTERM)
        except ProcessLookupError:
            app.status = "stopped"
            return

        try:
            await asyncio.wait_for(
                proc.wait(), timeout=GRACEFUL_SHUTDOWN_SECONDS
            )
        except asyncio.TimeoutError:
            logger.warning(
                "App %s did not exit gracefully, sending SIGKILL",
                app.build_id,
            )
            try:
                proc.kill()
                await proc.wait()
            except ProcessLookupError:
                pass

        app.status = "stopped"

    async def _evict_oldest_idle(self) -> None:
        """Stop the process with the oldest last_accessed timestamp."""
        if not self._processes:
            return

        oldest_id = min(
            self._processes,
            key=lambda bid: self._processes[bid].last_accessed,
        )
        logger.info("Evicting oldest idle app %s to free a slot", oldest_id)
        await self.stop_app(oldest_id)


# Module-level singleton
process_manager = ProcessManager()
