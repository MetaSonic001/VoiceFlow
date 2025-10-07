from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from .db import get_db, engine, Base, SessionLocal
from .async_runner import run_coro_sync
from .models import PipelineAgent, Pipeline
import pathlib
import sys
import json
import asyncio
import logging
import importlib

# initialize logging early so guarded imports can use logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-runner")

# Attempt to import document-ingestion services (embedder, vector_store, db manager)
_DOC_INGEST_AVAILABLE = False
_embedder = None
_vector_store = None
_db_manager = None
_summarizer = None
try:
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    ingestion_path = repo_root / 'document-ingestion'
    if ingestion_path.exists():
        sys.path.insert(0, str(ingestion_path))
        try:
            # dynamically import the services package modules used by the ingestion API
            mod_embed = importlib.import_module('services.embedder')
            mod_vs = importlib.import_module('services.vector_store')
            mod_db = importlib.import_module('services.database')
            try:
                mod_sum = importlib.import_module('services.summarizer')
                Summarizer = getattr(mod_sum, 'Summarizer', None)
            except Exception:
                Summarizer = None

            TextEmbedder = getattr(mod_embed, 'TextEmbedder', None)
            VectorStore = getattr(mod_vs, 'VectorStore', None)
            DatabaseManager = getattr(mod_db, 'DatabaseManager', None)

            # instantiate local helpers (keep lightweight)
            _embedder = TextEmbedder() if TextEmbedder else None
            _vector_store = VectorStore() if VectorStore else None
            _db_manager = DatabaseManager() if DatabaseManager else None
            _summarizer = Summarizer() if Summarizer else None
            _DOC_INGEST_AVAILABLE = True
            logger.info("Agent-runner: document-ingestion services available and initialized")
        except Exception as e:
            logger.exception(f"Failed to initialize document-ingestion services: {e}")
            _DOC_INGEST_AVAILABLE = False
    else:
        logger.info("document-ingestion folder not found; running with local fallback tools")
except Exception as e:
    logger.exception(f"Error while attempting to import document-ingestion services: {e}")
from sqlalchemy.orm import Session
import uvicorn


app = FastAPI(title="Agent Runner Service")

# Create DB tables
Base.metadata.create_all(bind=engine)


class CreateAgentIn(BaseModel):
    name: str
    agent_type: str
    config: Optional[Dict[str, Any]] = {}


class CreatePipelineIn(BaseModel):
    name: str
    tenant_id: Optional[str]
    stages: List[Dict[str, Any]]


# Concrete tools for pipeline agents
class CuratorTool(BaseTool):
    name = "curator"
    description = "Extracts structured FAQs and embeddings from docs and stores them in Chroma"

    def _run(self, payload) -> str:
        """
        payload is expected to be a JSON-like string or dict with keys:
        - context: { tenant_id }
        - settings: may include document_ids or limit
        """
        try:
            if isinstance(payload, str):
                info = json.loads(payload)
            else:
                info = payload

            context = info.get('context', {})
            settings = info.get('settings', {})
            tenant_id = context.get('tenant_id')
            agent_id = context.get('agent_id') or settings.get('agent_id')

            # If document-ingestion services are available, use them
            if _DOC_INGEST_AVAILABLE and _db_manager and _embedder and _vector_store:
                # Determine documents to process
                doc_ids = settings.get('document_ids')
                docs = []
                if doc_ids:
                    for did in doc_ids:
                            doc = run_coro_sync(_db_manager.get_document(did))
                            if doc and doc.get('has_content'):
                                content = run_coro_sync(_db_manager.get_document_content(did))
                                text = (content.decode('utf-8') if isinstance(content, (bytes, bytearray)) else '')
                                docs.append({'id': did, 'content': text, 'metadata': doc.get('metadata', {})})
                else:
                    # fetch recent documents for tenant via db_manager.list_documents if available
                    try:
                        docs_list, total = run_coro_sync(_db_manager.list_documents(limit=settings.get('limit', 5), offset=0))
                        for d in docs_list:
                            if d.get('has_content'):
                                content = run_coro_sync(_db_manager.get_document_content(d['id']))
                                text = (content.decode('utf-8') if isinstance(content, (bytes, bytearray)) else '')
                                docs.append({'id': d['id'], 'content': text, 'metadata': d.get('metadata', {})})
                    except Exception:
                        # fallback to empty list
                        docs = []

                # For each document, chunk, embed, and store embeddings in Chroma with tenant/agent metadata
                stored = 0
                for d in docs:
                    chunks = _embedder.chunk_text(d.get('content', ''))
                    if not chunks:
                        continue
                    embeddings = run_coro_sync(_embedder.embed_chunks(chunks))
                    md = d.get('metadata', {}) or {}
                    md.update({'tenant_id': tenant_id, 'agent_id': agent_id})
                    run_coro_sync(_vector_store.store_embeddings(document_id=d['id'], chunks=chunks, embeddings=embeddings, metadata=md))
                    stored += len(embeddings)

                return f"curator_stored:{stored}"

        except Exception as e:
            logger.exception(f"CuratorTool error: {e}")

        # Fallback naive behavior
        return "[]"


class EvaluatorTool(BaseTool):
    name = "evaluator"
    description = "Evaluates relevance and accuracy of embeddings or results using vector store"

    def _run(self, payload) -> str:
        try:
            if isinstance(payload, str):
                info = json.loads(payload)
            else:
                info = payload
            context = info.get('context', {})
            settings = info.get('settings', {})
            tenant_id = context.get('tenant_id')
            agent_id = context.get('agent_id') or settings.get('agent_id')

            # If vector store available and we have an embedding to test
            if _DOC_INGEST_AVAILABLE and _vector_store:
                embedding = settings.get('embedding')
                if embedding:
                    results = run_coro_sync(_vector_store.search(query_embedding=embedding, limit=settings.get('top_k', 5), tenant_id=tenant_id, agent_id=agent_id))
                    # crude evaluation: pass if we get any results with distance < threshold
                    ok = any((r.get('distance') is not None and r.get('distance') < 0.3) for r in results)
                    return "pass" if ok else "fail"

        except Exception as e:
            logger.exception(f"EvaluatorTool error: {e}")
        return "fail"


class SummarizerTool(BaseTool):
    name = "summarizer"
    description = "Generates short summary from previous calls/docs using ingestion summarizer if available"

    def _run(self, payload) -> str:
        try:
            if isinstance(payload, str):
                info = json.loads(payload)
            else:
                info = payload
            context = info.get('context', {})
            settings = info.get('settings', {})
            texts = settings.get('texts') or []

            if _DOC_INGEST_AVAILABLE and _summarizer:
                # summarizer.summarize expects list input
                summary = run_coro_sync(_summarizer.summarize(texts, max_length=settings.get('max_length', 200)))
                # summarizer may return list
                if isinstance(summary, list):
                    return summary[0] if summary else ''
                return str(summary)

            joined = "\n".join(texts)
            return joined[:200] + ("..." if len(joined) > 200 else "")
        except Exception as e:
            logger.exception(f"SummarizerTool error: {e}")
            return ""


class QATool(BaseTool):
    name = "qa"
    description = "Audits transcripts for tone, compliance, and missed intents using backend data when available"

    def _run(self, payload) -> str:
        try:
            if isinstance(payload, str):
                info = json.loads(payload)
            else:
                info = payload
            # payload may contain transcript text directly or a transcript_id
            transcript = info.get('transcript')
            transcript_id = info.get('transcript_id')

            # If a transcript_id is provided and backend adapter exists in db_manager, try to fetch it
            if _DOC_INGEST_AVAILABLE and _db_manager and transcript_id:
                try:
                    # document-ingestion's DatabaseManager may expose adapters to backend models
                    # For now, if provided, fetch document content as a placeholder
                    content = run_coro_sync(_db_manager.get_document_content(transcript_id))
                    if content:
                        transcript = content.decode('utf-8') if isinstance(content, (bytes, bytearray)) else str(content)
                except Exception:
                    pass

            issues = []
            if transcript and 'sorry' in transcript.lower():
                issues.append('apology_detected')
            if transcript and len(transcript.split()) < 5:
                issues.append('short_transcript')
            logger.info(f"QA found issues: {issues}")
            return str(issues)
        except Exception as e:
            logger.exception(f"QATool error: {e}")
            return str([])


# Helper to materialize a crew agent from a PipelineAgent DB model
def materialize_agent(db_agent: PipelineAgent):
    tools = []
    if db_agent.agent_type == "curator":
        tools = [CuratorTool()]
        role = "Knowledge Curator"
    elif db_agent.agent_type == "evaluator":
        tools = [EvaluatorTool()]
        role = "Evaluator"
    elif db_agent.agent_type == "summarizer":
        tools = [SummarizerTool()]
        role = "Summarizer"
    elif db_agent.agent_type == "qa":
        tools = [QATool()]
        role = "QA Agent"
    else:
        tools = []
        role = db_agent.agent_type

    agent = Agent(
        role=role,
        goal=db_agent.config.get("goal") if db_agent.config else "Execute pipeline stage",
        backstory=db_agent.config.get("backstory") if db_agent.config else "",
        tools=tools,
        verbose=False,
        allow_delegation=False,
    )
    return agent


def run_pipeline(db: Session, pipeline: Pipeline, context: Dict[str, Any]):
    logger.info(f"Running pipeline {pipeline.id} - {pipeline.name}")
    for idx, stage in enumerate(pipeline.stages or []):
        agent_id = stage.get("agent_id")
        stage_type = stage.get("type")
        settings = stage.get("settings", {})

        db_agent = db.query(PipelineAgent).filter(PipelineAgent.id == agent_id).first() if agent_id else None
        if not db_agent:
            logger.warning(f"Stage {idx} missing agent {agent_id}; skipping")
            continue

        crew_agent = materialize_agent(db_agent)
        if not crew_agent:
            logger.warning(f"Could not materialize agent {db_agent.id}")
            continue

        # Build a task using the context + settings
        task_description = settings.get("prompt") or f"Run {stage_type} on tenant {pipeline.tenant_id}"
        task = Task(description=task_description, agent=crew_agent, expected_output=settings.get("expected", "text"))

        crew = Crew(agents=[crew_agent], tasks=[task], process=Process.sequential)
        try:
            result = crew.kickoff()
            logger.info(f"Stage {idx} ({stage_type}) result: {result}")
            # store artifact in context for downstream stages
            context_key = f"stage_{idx}_result"
            context[context_key] = str(result)
        except Exception as e:
            logger.exception(f"Error running stage {idx}: {e}")
            context[f"stage_{idx}_error"] = str(e)

    logger.info(f"Pipeline {pipeline.id} completed")
    return context


@app.post("/agents", response_model=Dict[str, Any])
def create_agent(inp: CreateAgentIn, db: Session = Depends(get_db)):
    agent = PipelineAgent(name=inp.name, agent_type=inp.agent_type, config=inp.config or {})
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return {"id": agent.id, "name": agent.name, "agent_type": agent.agent_type}


@app.get("/agents")
def list_agents(db: Session = Depends(get_db)):
    agents = db.query(PipelineAgent).all()
    return [{"id": a.id, "name": a.name, "agent_type": a.agent_type, "config": a.config} for a in agents]


@app.post("/pipelines", response_model=Dict[str, Any])
def create_pipeline(inp: CreatePipelineIn, db: Session = Depends(get_db)):
    pipeline = Pipeline(name=inp.name, tenant_id=inp.tenant_id, stages=inp.stages)
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)
    return {"id": pipeline.id, "name": pipeline.name}


@app.get("/pipelines")
def list_pipelines(db: Session = Depends(get_db)):
    pls = db.query(Pipeline).all()
    return [{"id": p.id, "name": p.name, "tenant_id": p.tenant_id, "stages": p.stages} for p in pls]


@app.post("/pipelines/{pipeline_id}/trigger")
def trigger_pipeline(pipeline_id: int, payload: Optional[Dict[str, Any]] = None, background_tasks: BackgroundTasks = Depends(), db: Session = Depends(get_db)):
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    # Allow caller to provide context (tenant_id, agent_id, document_ids, transcript, etc.)
    context: Dict[str, Any] = {"tenant_id": pipeline.tenant_id}
    if payload and isinstance(payload, dict):
        context.update(payload)

    # schedule background execution
    background_tasks.add_task(run_pipeline, db, pipeline, context)
    return {"message": "Pipeline scheduled", "pipeline_id": pipeline.id}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8110)
