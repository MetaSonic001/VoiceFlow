# Agent Runner Service

This lightweight FastAPI service runs multi-agent pipelines using CrewAI. It provides endpoints to create pipeline agents and pipelines, and to trigger asynchronous runs.

Key endpoints

- POST /agents — create an agent (types: curator, evaluator, summarizer, qa)
- GET /agents — list agents
- POST /pipelines — create a pipeline (stages list)
- GET /pipelines — list pipelines
- POST /pipelines/{pipeline_id}/trigger — schedule a background run

Environment variables

- AGENT_RUNNER_DATABASE_URL (optional) - explicit database URL for the agent runner service. Use Postgres (asyncpg) in production. Example: `postgresql+asyncpg://user:pass@localhost:5433/voiceflow`
- BACKEND_DATABASE_URL (optional) - fallback canonical backend DB. If `AGENT_RUNNER_DATABASE_URL` is not set, the service will try this value before falling back to a local sqlite file.
- CHROMA_PERSIST_PATH (optional) - path to Chroma persistent directory. Default in this repo: `document-ingestion/chroma_db`.
- INGESTION_LOG_DIR (optional) - path for ingestion temporary files or logs. Default: `ingestion_logs`.
- AGENT_RUNNER_API_KEY (optional) - placeholder if you want to add a simple API key protection for runner endpoints.

You can copy the provided `.env.example` to `.env` and edit values for local development.

Quick start (dev)

1. Copy the example env and edit as needed:

```powershell
copy .\agent_runner_service\.env.example .\agent_runner_service\.env
# edit .\agent_runner_service\.env in your favorite editor
```

2. Install Python dependencies (use your environment manager):

```powershell
conda activate fastapi-cv
pip install -r backend/requirements.txt
pip install -r agent_runner_service/requirements.txt || pip install crewai fastapi uvicorn
```

3. Create DB tables (sqlite fallback will create a local file):

```powershell
python -c "from agent_runner_service.db import Base, engine; Base.metadata.create_all(bind=engine); print('tables created')"
```

4. Run the service locally:

```powershell
uvicorn agent_runner_service.main:app --reload --port 8110
```

Testing

Tests use pytest and FastAPI TestClient. Run them from the repository root:

```powershell
conda activate fastapi-cv
pip install pytest
pytest agent_runner_service/tests -q
```

Notes & next steps

- Current CrewAI-driven tools are simple placeholders. Replace `CuratorTool`, `EvaluatorTool`, `SummarizerTool`, and `QATool` with richer implementations that call into `document-ingestion` and your Chroma vector store. The tools expose a single `_run` method compatible with CrewAI's `BaseTool`.
- Consider adding authentication/authorization and wiring pipeline scheduling into the backend admin UI.
# Agent Runner Service

This lightweight FastAPI service runs multi-agent pipelines using CrewAI. It provides endpoints to create pipeline agents and pipelines, and to trigger asynchronous runs.

Key endpoints
- POST /agents — create an agent (types: curator, evaluator, summarizer, qa)
- GET /agents — list agents
- POST /pipelines — create a pipeline (stages list)
- GET /pipelines — list pipelines
- POST /pipelines/{pipeline_id}/trigger — schedule a background run

Integration
- The service will use the `AGENT_RUNNER_DATABASE_URL` environment variable if set. If not present, it falls back to `BACKEND_DATABASE_URL` (so it can share the canonical backend Postgres) or to a local SQLite DB for dev.
- To integrate with the main backend, set `AGENT_RUNNER_DATABASE_URL` to the same Postgres URL used by the backend (`BACKEND_DATABASE_URL`).

Testing
- Tests use pytest and FastAPI TestClient. Run them from the repository root:

```bash
conda activate fastapi-cv
pip install -r backend/requirements.txt
pip install pytest
pytest agent_runner_service/tests -q
```

Notes & next steps
- Current CrewAI-driven tools are simple placeholders. Replace `CuratorTool`, `EvaluatorTool`, `SummarizerTool`, and `QATool` with richer implementations that call into `document-ingestion` and your Chroma vector store. The tools expose a single `_run` method compatible with CrewAI's `BaseTool`.
- Consider adding authentication/authorization and wiring pipeline scheduling into the backend admin UI.
