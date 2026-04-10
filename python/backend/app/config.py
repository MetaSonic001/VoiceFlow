"""
Environment / settings loaded once from .env or env vars.
Mirrors new_backend/express-backend/src/config/env.ts
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://vf_admin:vf_secure_2025!@localhost:8010/voiceflow_prod"

    # Sync URL for non-async operations (alembic, etc.)
    @property
    def DATABASE_URL_SYNC(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "").replace("asyncpg://", "postgresql://")

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 8020

    # Auth
    JWT_SECRET: str = "dev-secret"

    # Groq LLM
    GROQ_API_KEY: Optional[str] = None

    # Base URL for this API when handlers call themselves via HTTP (onboarding → ingestion).
    FASTAPI_URL: str = "http://127.0.0.1:8040"
    FRONTEND_URL: str = "http://localhost:8050"

    # Server
    PORT: int = 8040
    NODE_ENV: str = "development"

    # Twilio (optional)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WEBHOOK_BASE_URL: Optional[str] = None

    # MinIO (optional)
    MINIO_ENDPOINT: Optional[str] = None
    MINIO_ACCESS_KEY: Optional[str] = None
    MINIO_SECRET_KEY: Optional[str] = None

    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8030

    # Credential encryption key (64-char hex)
    CREDENTIALS_ENCRYPTION_KEY: Optional[str] = None

    model_config = {
        "env_file": ["../.env", ".env"],
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
