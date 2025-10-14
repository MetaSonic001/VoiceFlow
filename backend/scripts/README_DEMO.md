Demo orchestration: ingest FR CRCE websites and create an agent

This folder contains a small orchestration script which demonstrates the document ingestion -> embedding -> agent workflow end-to-end.

Files
- `ingest_and_create_agent_demo.py` - main demo script (uses services at default local ports; see env vars below)
- `demo_config.example.json` - example config showing where to change URLs

Usage:
- Ensure these services are running locally:
  - Document Ingestion API (default: http://localhost:8002)
  - Backend API (default: http://localhost:8000)
  - Agent Workflow API (default: http://localhost:8001)
- (Optional) Set env vars to override endpoints:
  - BACKEND_URL, INGESTION_URL, AGENT_WORKFLOW_URL
- Run the demo:

```cmd
python backend\scripts\ingest_and_create_agent_demo.py
```

Logs will be appended to `ingest_demo.log` in the current working directory. The script prints each step and saves inputs/outputs for inspection.

Notes
- The script uses a small list of likely FR CRCE URLs; please update `DEFAULT_FR_CRCE_URLS` in the script with the sites you want to ingest.
- The demo does a best-effort attach of documents to the agent; if your backend does not expose `/agents/{agent_id}/attach_documents` the script will continue but the agent-workflow may need to be pointed at the same ChromaDB or have documents linked by metadata.
