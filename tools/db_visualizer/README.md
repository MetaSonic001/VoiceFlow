DB Visualizer
=============

Purpose
-------

Lightweight visualizer to inspect three parts of the project: MinIO (object storage), Postgres (metadata), and Chroma (embeddings sqlite). It provides an interactive graph linking objects -> Postgres rows -> Chroma entries using heuristics.

Quick start
-----------

1. From the repository root (recommended) run:

```cmd
python run_db_visualizer.py
```

2. Open `http://127.0.0.1:8765/` in your browser.

Environment
-----------

Create a `.env` file under `tools/db_visualizer/.env` or set env vars in your shell. The visualizer prefers `BACKEND_DATABASE_URL` but will fall back to common names.

Required/optional env vars (examples):

```ini
BACKEND_DATABASE_URL=postgresql+asyncpg://doc_user:doc_password@localhost:5433/documents_db

DATABASE_URL=postgresql+asyncpg://doc_user:doc_password@localhost:5433/documents_db

MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=voiceflow

CHROMA_PERSIST_DIR=./chroma_db
```

Notes
-----

- If `BACKEND_DATABASE_URL` contains `+asyncpg`, the visualizer will replace it with `+psycopg2` for synchronous inspection via SQLAlchemy.
- The graph builder uses heuristics (filename contains PK, matching strings) — to improve accuracy, provide schemas or examples and I can refine the matching.
- Do not expose this tool without authentication on public networks.

Requirements
------------

- See `requirements.txt`. Optional packages (boto3, sqlalchemy) are only necessary for MinIO/Postgres inspection.

Open `http://localhost:8765/` after starting the server.

This is intentionally lightweight: it only detects common locations and env vars. You can extend `/api/*` endpoints to connect to your services securely.

Tutorial & Quick Tour
---------------------

When you open the UI you'll see a left-side controls panel and a main graph area. The tutorial overlay appears on first run and explains:

- What MinIO / Postgres / Chroma are and what the visualizer shows
- How the graph is built (best-effort heuristics: filename/PK matching and document id matching)
- How to search, filter, save/load layouts and toggle grouping

If you dismiss "Don't show again" the overlay won't auto-appear next time. You can re-open it with the "Help / Tutorial" button in the left panel.
Quick local visualizer for Chroma (sqlite), MinIO, and Postgres environment detection.
