from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    GLM_API_KEY: str = ""
    GLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/"
    GLM_MODEL: str = "glm-4.5"
    DATABASE_URL: str = "sqlite+aiosqlite:///./autopsy.db"
    CLONE_DIR: str = "/tmp/code-autopsy"
    MAX_ANALYSIS_STEPS: int = 25
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"]

settings = Settings()
