"""Buildy configuration — reads from .env via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


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

    # Twitter Scraper
    ENABLE_TWITTER_SCRAPER: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./buildy.db"

    # App
    MAX_STEPS: int = 30
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:3001"]'
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @property
    def cors_origins_list(self) -> List[str]:
        import json
        try:
            return json.loads(self.CORS_ORIGINS)
        except Exception:
            return ["http://localhost:3000", "http://localhost:3001"]


settings = Settings()
