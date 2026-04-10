"""Buildy configuration — reads from .env via pydantic-settings."""


from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # GLM API
    GLM_API_KEY: str = ""
    GLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/"
    GLM_MODEL: str = "glm-5.1"               # Best model — used for planning, PRD, QA, review
    GLM_FAST_MODEL: str = "glm-4.5"         # Higher concurrency (10) — used for bulk file generation
    GLM_FALLBACK_MODEL: str = "glm-5"       # Fallback if primary is rate-limited
    GLM_VISION_MODEL: str = "glm-5v-turbo"
    GLM_IMAGE_MODEL: str = "cogView-4-250304"
    # Cap simultaneous outbound GLM HTTP calls (chat, vision, image). Multiple
    # Twitter mentions each spawn a full pipeline via create_task — without this
    # they all hit the API at once and trigger HTTP 429. Set to 1 to serialize.
    GLM_MAX_CONCURRENT_REQUESTS: int = 1
    ENABLE_THINKING: bool = True
    ENABLE_WEB_SEARCH: bool = True
    ENABLE_IMAGE_GEN: bool = True

    # Twitter API v2
    TWITTER_BEARER_TOKEN: str = ""
    TWITTER_API_KEY: str = ""
    TWITTER_API_SECRET: str = ""
    TWITTER_ACCESS_TOKEN: str = ""
    TWITTER_ACCESS_SECRET: str = ""

    # Cloud Deploy
    RAILWAY_API_TOKEN: str = ""
    GITHUB_TOKEN: str = ""  # for creating temp repos
    GITHUB_ORG: str = "builddy-apps"  # org/user for temp repos

    # Twitter Scraper (Playwright-based login)
    TWITTER_USERNAME: str = ""      # @handle or email for auto-login
    TWITTER_PASSWORD: str = ""      # password for auto-login
    ENABLE_TWITTER_SCRAPER: bool = True
    # How many @builddy mention builds may run pipelines at once (each is dozens of GLM calls).
    # Set to 1 so a batch of mentions does not multiply rate limits on the same API key.
    TWITTER_MAX_CONCURRENT_PIPELINES: int = 1

    # Post-processing agents
    ENABLE_AUTOPILOT: bool = True            # Auto-fix runtime errors via headless browser loop
    ENABLE_AUTO_TEST_GEN: bool = True        # Generate + deploy test suites after build

    # Database
    DATABASE_URL: str = "sqlite:///./buildy.db"

    # App
    MAX_STEPS: int = 30
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:3001"]'
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    # Public URL of this API (for acceptance checks / webhooks resolving /apps/... URLs)
    PUBLIC_BACKEND_URL: str = "http://127.0.0.1:8000"
    # Optional global webhook for all builds (build.webhook_url overrides)
    DEFAULT_WEBHOOK_URL: str = ""
    WEBHOOK_SIGNING_SECRET: str = ""
    # Discord-style ingest (shared secret header)
    DISCORD_INGEST_SECRET: str = ""
    ENABLE_PIPELINE_QUALITY_CHECKS: bool = False  # reserved for heavier checks

    @property
    def cors_origins_list(self) -> list[str]:
        import json
        try:
            return json.loads(self.CORS_ORIGINS)
        except Exception:
            return ["http://localhost:3000", "http://localhost:3001"]


settings = Settings()
