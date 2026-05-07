"""
Environment / settings loaded once from .env or env vars.
Used by FastAPI backend routes and services.
"""
from typing import Optional

from pydantic_settings import BaseSettings


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

    # LLMs
    GROQ_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    SUPPORTED_LLMS: list[str] = ["groq", "openai", "gemini", "ollama"]
    DEFAULT_LLM: str = "groq"

    # TTS
    KOKORO_TTS_URL: str = "http://localhost:8880"
    PIPER_TTS_URL: str = "http://localhost:8890"
    ORPHEUS_URL: str = "http://localhost:8080/v1/chat/completions"

    # STT
    VOSK_MODEL_PATH: str = "./models/vosk-model-small-en-us-0.15"
    VOSK_MODEL_URL: str = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    STT_ENGINE: str = "faster-whisper"

    # Audio
    AUDIO_PROCESSOR: str = "pydub"

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

    # Platform API keys — used for MCP (Managed Cloud Plan) tenants who don't
    # supply their own keys. Set these in production; leave blank in dev.
    PLATFORM_GROQ_KEY: Optional[str] = None
    PLATFORM_SARVAM_KEY: Optional[str] = None
    PLATFORM_OPENAI_KEY: Optional[str] = None
    PLATFORM_GEMINI_KEY: Optional[str] = None
    PLATFORM_TWILIO_SID: Optional[str] = None
    PLATFORM_TWILIO_TOKEN: Optional[str] = None
    PLATFORM_EXOTEL_SID: Optional[str] = None
    PLATFORM_EXOTEL_KEY: Optional[str] = None
    PLATFORM_EXOTEL_TOKEN: Optional[str] = None

    # Stripe billing
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_VOICE_MINUTES_METER_ID: Optional[str] = None

    # Owner accounts — never billed (comma-separated tenant IDs)
    OWNER_TENANT_IDS: str = ""

    # Security
    # Set to false in production to reject header-auth requests with empty x-tenant-id
    ALLOW_DEMO_FALLBACK: bool = True
    # Pre-shared secret appended as ?token= to Exotel callback URLs
    EXOTEL_WEBHOOK_SECRET: Optional[str] = None

    # MinIO (optional)
    MINIO_ENDPOINT: Optional[str] = None
    MINIO_ACCESS_KEY: Optional[str] = None
    MINIO_SECRET_KEY: Optional[str] = None

    # Sarvam AI (optional — enables Indian language TTS voices)
    SARVAM_API_KEY: Optional[str] = None

    # Voice clone reference audio storage (local fallback when MinIO is not configured)
    VOICE_CLONE_DIR: str = "/tmp/voiceflow_clones"
    VOICE_PREVIEW_CACHE_DIR: str = "/tmp/voiceflow_voice_previews"

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
