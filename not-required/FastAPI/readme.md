FastAPI service for VoiceFlow

This folder contains a lightweight FastAPI application used by the VoiceFlow project for onboarding, agent management, and Twilio webhook handling.

What changed recently

- Onboarding endpoints were extended to accept a `phone_number` during channel setup and to persist onboarding metadata for agent provisioning.
- A Twilio helper endpoint was added to list incoming phone numbers (requires Twilio credentials). The deploy/go-live step will attempt to update the Twilio incoming phone number webhook to point to your PUBLIC_BASE_URL when Twilio env vars are set.
- The backend will attempt to write ingestion metadata (tenant_id and agent_id) to the document-ingestion vector store when available.

Environment (.env.example)

Copy this file to `FastAPI/.env` and edit values for local development.

BACKEND_DATABASE_URL=sqlite+aiosqlite:///./voiceflow.db
# or a postgres example:
# BACKEND_DATABASE_URL=postgresql+asyncpg://doc_user:doc_password@localhost:5433/documents_db

# Twilio (optional - required for updating incoming number webhooks)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
PUBLIC_BASE_URL=http://localhost:8000

# Chroma / embedding settings (optional)
CHROMA_PERSIST_DIR=./chroma_db
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=

# MinIO / S3 (optional)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=voiceflow

Quick start (Windows cmd.exe)

1) Install Python deps:
   pip install -r FastAPI/requirements.txt

2) Create `.env` from `.env.example` and adjust values.

3) Run the API:
   uvicorn main:app --reload --port 8000

Notes

- If you don't set Twilio credentials the Twilio-related endpoints will degrade gracefully.
- For production use configure a real database (Postgres) and object storage (S3/MinIO).
