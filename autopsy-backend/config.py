from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    GLM_API_KEY: str = ""
    GLM_BASE_URL: str = "https://open.z.ai/api/paas/v4/"
    GLM_MODEL: str = "glm-5.1"
    DATABASE_URL: str = "sqlite+aiosqlite:///./autopsy.db"
    CLONE_DIR: str = "/tmp/code-autopsy"
    MAX_ANALYSIS_STEPS: int = 25
    CORS_ORIGINS: List[str] = ["http://localhost:3002", "http://localhost:3000"]

    class Config:
        env_file = ".env"

settings = Settings()
