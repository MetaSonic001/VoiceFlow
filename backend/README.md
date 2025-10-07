# VoiceFlow Backend - Local Setup

This README explains how to run the backend API locally for development on Windows (cmd.exe), how to start the required services (Postgres, MinIO, Chroma), and how to run the integration test.

## Prerequisites

- Python 3.10+ and a conda environment (optional)
- Docker Desktop (recommended) or local installations of Postgres and MinIO

## 1) Install Python dependencies

```cmd
conda activate fastapi-cv
pip install -r requirements.txt
```

## 2) Start Postgres (using Docker)

```cmd
docker run --name vf-postgres -e POSTGRES_USER=doc_user -e POSTGRES_PASSWORD=doc_password -e POSTGRES_DB=documents_db -p 5433:5432 -d postgres:15
```

Set environment variable for backend to use Postgres (cmd.exe):

```cmd
set BACKEND_DATABASE_URL=postgresql+asyncpg://doc_user:doc_password@localhost:5433/documents_db
```

## 3) Start MinIO (using Docker)

```cmd
docker run -p 9000:9000 --name vf-minio -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin -d quay.io/minio/minio server /data
```

Set MinIO env vars (cmd.exe):

```cmd
set MINIO_ENDPOINT=localhost:9000
set MINIO_ACCESS_KEY=minioadmin
set MINIO_SECRET_KEY=minioadmin
set MINIO_BUCKET=voiceflow
```

## 4) (Optional) Start Chroma locally or use the default file-based persistent client

Chroma can run in-process using the `chromadb` PersistentClient (no Docker needed). Set `CHROMA_DB_PATH` if you want a specific path.

## 5) Initialize the database tables

```cmd
python -m backend.init_db
```

This will attempt to create tables in the configured Postgres DB.

## 6) Run the backend

```cmd
uvicorn backend.main:app --reload --port 8000
```

## 7) Run the integration test (local sqlite test)

```cmd
python -m pytest backend/tests/integration_test.py -q
```

## Notes

- For production deployments, replace the simple token logic and API key with a proper auth provider.
- Use Alembic to manage migrations instead of the simple `init_db` script.

## Backend FastAPI for VoiceFlow - Overview

This backend provides:

- Postgres-backed metadata for tenants, agents, and documents
- MinIO (S3-compatible) storage for file blobs
- Chroma integration for per-agent collections
- Background ingestion worker (FastAPI BackgroundTasks) to chunk, embed, and upsert into Chroma

## Multi-tenant Chroma note

This backend uses a per-tenant, per-agent collection scheme for ChromaDB. Collection names are normalized as `{tenant_id}_{agent_id}` (hyphens replaced with underscores).

To ensure embeddings are routed to the correct collection, any ingestion request or backend worker that stores embeddings must include `tenant_id` and `agent_id` in the document metadata. The ingestion VectorStore enforces this and will raise an error if tenant/agent are missing to avoid accidental global writes/reads.

Example metadata sent during upload or used when calling the VectorStore:

```py
metadata = {
    'tenant_id': 'tenant-1234',
    'agent_id': 'agent-5678',
    'original_filename': 'report.pdf'
}
```

## Quickstart

1. Copy `.env.example` into `backend/.env` and configure Postgres and MinIO credentials.
2. Install dependencies: `pip install -r backend/requirements.txt`
3. Run migrations (Alembic) - TODO: configure DB URL in alembic.ini
4. Start server: `uvicorn backend.main:app --reload --port 9000`

## About the folder layout: why is there `backend/backend`?

You may have noticed the repository contains a `backend/` top-level folder and inside it another `backend/` Python package (i.e. `backend/backend`). This pattern happened to keep the Python package self-contained for imports and to avoid name collisions when the repo is added to sys.path during testing or when other services import the package.

That said, having `backend/backend` is confusing. The inner `backend` is the actual Python package (contains `main.py`, `db.py`, `models.py`, etc.). The outer `backend` is the project folder containing docs, tests, and packaging. It's safe to rename the inner package to a clearer name like `backend_service` or `api`.

Safe rename plan (non-destructive)

1) Decide the new package name, for example `backend_service`.
2) Update imports in code to use the new package path (search/replace `from backend.` -> `from backend_service.` and similar). The repository uses relative imports in many places so in many cases no changes are required.
3) Move the inner package directory and test that everything still imports.

Windows (cmd.exe) commands to perform the rename and keep git history:

```cmd
:: from repo root (C:\VoiceFlow)
:: 1) Move the inner package
git mv backend/backend backend/backend_service

:: 2) Replace references in Python files (uses PowerShell's replace or a cross-platform tool like sed).
:: Example using PowerShell (run in PowerShell):
Get-ChildItem -Path . -Recurse -Include *.py | ForEach-Object { (Get-Content $_.FullName) -replace 'from backend\.', 'from backend_service.' | Set-Content $_.FullName }

:: 3) Run tests locally to pick up import errors
conda activate fastapi-cv
pip install -r backend/requirements.txt
python -m pytest -q

:: Commit the rename
git add -A
git commit -m "Rename inner backend package to backend_service to avoid nested naming"
```

Notes and caveats

- If you rely on `python -m backend.main` style module runs you may need to update invocation paths to `python -m backend_service.main`.
- If some parts of the repo import `backend` via `sys.path` insertion (the ingestion adapter did this), update those insertion points to the new package path.
- I recommend running the full test suite and doing a quick smoke test of the API after the rename.

## Recent changes (onboarding, Twilio, and frontend wiring)

- The onboarding flow (company -> agent -> knowledge -> voice -> channels -> go-live) now persists partial state in the frontend and calls new backend endpoints to create and configure agents.
- A Twilio helper endpoint was added to list incoming phone numbers. Channel setup accepts a `phone_number` (E.164) and persists it as part of the agent's channels configuration.
- The deploy/go-live endpoint attempts to update the Twilio incoming phone number webhook to point to your configured PUBLIC_BASE_URL when `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` are set. Twilio integration is guarded and will not raise errors when credentials are missing.
- The backend will attempt to write ingestion metadata (`tenant_id` and `agent_id`) when calling the document-ingestion helpers to ensure per-tenant/agent collection writes to Chroma.
- The agent-runner now uses a `run_coro_sync` helper to safely call async ingestion functions from synchronous CrewAI tool code.

For quick local development, check the `.env.example` files in each service folder (FastAPI, agent-runner, frontend, and document-ingestion) for the minimum env variables required to run that component.
