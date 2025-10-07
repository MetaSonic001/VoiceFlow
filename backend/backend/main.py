from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, BackgroundTasks, Security, Request
from fastapi.responses import JSONResponse
from fastapi import Request
from pydantic import BaseModel
from .db import get_session
from .models import Tenant, Agent, Document
from .models import PipelineAgent, Pipeline
from .minio_helper import upload_file, get_minio_client
from .worker import schedule_ingestion
from .chroma_helper import ensure_collection, delete_collection, list_collections, collection_name
from dotenv import load_dotenv
import os
import pathlib
import uuid
from typing import Optional
from fastapi.security.api_key import APIKeyHeader
import sys
import asyncio
import io
from .auth import create_access_token, get_current_user, require_role
from .models import User, UserRole
from passlib.context import CryptContext
from pydantic import EmailStr

pwd_ctx = CryptContext(schemes=['bcrypt'], deprecated='auto')


class SignupPayload(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = 'user'


class LoginPayload(BaseModel):
    email: EmailStr
    password: str

load_dotenv()

# Simple logging and metrics
import logging
logger = logging.getLogger('backend')
logging.basicConfig(level=logging.INFO)

import httpx
AGENT_RUNNER_URL = os.getenv('AGENT_RUNNER_URL', 'http://localhost:8110')

# Simple in-memory metrics
metrics = {
    'requests': 0,
    'errors': 0,
    'last_error': None,
}
app = FastAPI(title='VoiceFlow Backend')


@app.middleware('http')
async def log_requests(request: Request, call_next):
    metrics['requests'] += 1
    logger.info(f"{request.method} {request.url}")
    try:
        resp = await call_next(request)
        return resp
    except Exception as e:
        metrics['errors'] += 1
        metrics['last_error'] = str(e)
        logger.exception('Unhandled exception')
        raise

# Mount agent-workflow if available
try:
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    agent_path = repo_root / 'agent-workflow'
    if str(agent_path) not in sys.path and agent_path.exists():
        sys.path.insert(0, str(agent_path))
    import app as agent_app_module
    agent_fastapi = getattr(agent_app_module, 'app', None)
    if agent_fastapi:
        app.mount('/agent', agent_fastapi)
        print('Mounted agent-workflow at /agent')
except Exception:
    pass

# Simple API Key auth for admin endpoints. Replace with real auth in production.
API_KEY = os.getenv('BACKEND_API_KEY', None)
api_key_header = APIKeyHeader(name='X-API-Key', auto_error=False)


async def require_api_key(api_key: Optional[str] = Security(api_key_header)):
    if API_KEY is None:
        # If no API key configured, allow through (dev mode)
        return True
    if not api_key or api_key != API_KEY:
        raise HTTPException(status_code=403, detail='Invalid or missing API Key')
    return True


def _ensure_ingestion_imports():
    # Ensure document-ingestion path is importable and import required services
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    ingestion_path = repo_root / 'document-ingestion'
    if str(ingestion_path) not in sys.path and ingestion_path.exists():
        sys.path.insert(0, str(ingestion_path))


@app.post('/admin/reindex/{agent_id}')
async def reindex_agent(agent_id: str, background_tasks: BackgroundTasks, api_key=Depends(require_api_key), user=Depends(require_role('admin'))):
    """Trigger a full re-sync of documents for an agent into the vector store."""
    try:
        _ensure_ingestion_imports()
        # dynamic imports
        from services.vector_store import VectorStore
        from services.embedder import TextEmbedder
        from services.ocr_processor import OCRProcessor
        from services.web_scraper import WebScraper
        from services.file_detector import FileDetector
        try:
            from services.summarizer import Summarizer
        except Exception:
            Summarizer = None
        from services.database import DatabaseManager
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import ingestion services: {e}")

    # Create instances and schedule the sync
    vs = VectorStore()
    ed = TextEmbedder()
    ocr = OCRProcessor()
    ws = WebScraper()
    fd = FileDetector()
    dbm = DatabaseManager()
    try:
        # Schedule background sync using the vector store's sync_from_database
        async def _sync():
            await vs.sync_from_database(dbm, ocr, ws, ed, fd, summarizer=None)

        # BackgroundTasks expects a callable; pass asyncio.create_task and the coroutine
        background_tasks.add_task(asyncio.create_task, _sync())
        return {'status': 'scheduled'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule sync: {e}")


class TenantCreate(BaseModel):
    name: str


class AgentCreate(BaseModel):
    tenant_id: str
    name: str


@app.post('/tenants')
async def create_tenant(payload: TenantCreate):
    async for session in get_session():
        t = Tenant(name=payload.name)
        session.add(t)
        await session.commit()
        await session.refresh(t)
        return JSONResponse({'id': str(t.id), 'name': t.name})


@app.post('/agents')
async def create_agent(payload: AgentCreate):
    async for session in get_session():
        a = Agent(name=payload.name, tenant_id=payload.tenant_id)
        session.add(a)
        await session.commit()
        await session.refresh(a)
        return JSONResponse({'id': str(a.id), 'name': a.name})


@app.post('/admin/collections/ensure')
async def api_ensure_collection(tenant_id: str, agent_id: str, api_key=Depends(require_api_key), user=Depends(require_role('admin'))):
    coll = ensure_collection(tenant_id, agent_id)
    return {'collection': coll.name}


@app.post('/admin/collections/delete')
async def api_delete_collection(tenant_id: str, agent_id: str, api_key=Depends(require_api_key), user=Depends(require_role('admin'))):
    ok = delete_collection(tenant_id, agent_id)
    return {'deleted': ok}


@app.get('/admin/collections')
async def api_list_collections(api_key=Depends(require_api_key), user=Depends(require_role('admin'))):
    cols = list_collections()
    return {'collections': cols}


@app.post('/upload/{tenant_id}/{agent_id}')
async def upload_document(tenant_id: str, agent_id: str, file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    # Store file to MinIO
    filename = file.filename
    dest_path = f"tenants/{tenant_id}/assets/uploaded_docs/{uuid.uuid4().hex}_{filename}"
    client = get_minio_client()
    # MinIO put via fileobj
    await file.seek(0)
    content = await file.read()
    buf = io.BytesIO(content)
    upload_file(buf, dest_path, client=client)

    # Use document-ingestion's DatabaseManager as the canonical document store
    try:
        # Ensure ingestion services importable
        repo_root = pathlib.Path(__file__).resolve().parents[2]
        ingestion_path = repo_root / 'document-ingestion'
        if str(ingestion_path) not in sys.path and ingestion_path.exists():
            sys.path.insert(0, str(ingestion_path))

        from services.database import DatabaseManager
        dbm = DatabaseManager()
        # store_document returns the canonical document_id used by ingestion pipeline
        document_id = await dbm.store_document(filename, content, file.content_type or 'application/octet-stream', {'tenant_id': tenant_id, 'agent_id': agent_id})
    except Exception as e:
        # Fall back to backend-only behavior if ingestion manager isn't available
        document_id = None
        print(f"Warning: failed to store via ingestion DatabaseManager: {e}")

    # Insert metadata row into backend DB, referencing ingestion document_id when available
    async for session in get_session():
        doc = Document(id=document_id or uuid.uuid4(), agent_id=agent_id, tenant_id=tenant_id, filename=filename, file_path=dest_path, file_type=file.content_type)
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        # Ensure collection exists for this agent
        ensure_collection(tenant_id, agent_id)
        # Schedule ingestion (pass ingestion document_id when available)
        scheduled_doc_id = str(doc.id)
        if document_id:
            scheduled_doc_id = document_id

            if background_tasks is not None:
                schedule_ingestion(background_tasks, scheduled_doc_id, dest_path, agent_id, tenant_id)
            else:
                # Fire-and-forget
                asyncio.create_task(ingest_via_worker(scheduled_doc_id, dest_path, agent_id, tenant_id))
            return {'id': scheduled_doc_id, 'file_path': dest_path}



    @app.post('/auth/signup')
    async def signup(payload: SignupPayload):
        async for session in get_session():
            # Check existing
            res = await session.execute("SELECT id FROM users WHERE email = :email", {'email': payload.email})
            if res.fetchone():
                raise HTTPException(status_code=400, detail='User already exists')
            hashed = pwd_ctx.hash(payload.password)
            # Map role string to enum if provided
            try:
                role_enum = UserRole(payload.role) if payload.role else UserRole.user
            except Exception:
                role_enum = UserRole.user

            u = User(email=payload.email, password_hash=hashed, role=role_enum)
            session.add(u)
            await session.commit()
            await session.refresh(u)
            token = create_access_token(payload.email, role=u.role.value if hasattr(u.role, 'value') else str(u.role))
            return {'access_token': token, 'user': {'id': str(u.id), 'email': u.email, 'role': u.role.value if hasattr(u.role, 'value') else u.role}}


    @app.post('/auth/login')
    async def login(payload: LoginPayload):
        async for session in get_session():
            res = await session.execute("SELECT id, email, password_hash, role FROM users WHERE email = :email", {'email': payload.email})
            row = res.fetchone()
            if not row:
                raise HTTPException(status_code=401, detail='Invalid credentials')
            uid, email, password_hash, role = row
            if not pwd_ctx.verify(payload.password, password_hash):
                raise HTTPException(status_code=401, detail='Invalid credentials')
            # normalize role
            role_value = role.value if hasattr(role, 'value') else role
            token = create_access_token(email, role=role_value)
            return {'access_token': token, 'user': {'id': str(uid), 'email': email, 'role': role_value}}


    @app.post('/auth/logout')
    async def logout(user=Depends(get_current_user)):
        # Stateless JWT: logout is a client-side operation (remove token). Provide endpoint for symmetry.
        return {'success': True}


    @app.post('/auth/guest')
    async def guest():
        # Issue a short-lived guest token
        token = create_access_token('guest@local', role=UserRole.guest.value, expires_minutes=60)
        return {'access_token': token, 'user': {'id': 'guest', 'email': 'guest@local', 'role': UserRole.guest.value}}


    @app.get('/auth/me')
    async def me(user=Depends(get_current_user)):
        # Return lightweight user info encoded in the token
        return {'user': user}


async def ingest_via_worker(document_id, s3_path, agent_id, tenant_id):
    # Helper to call the same worker logic when BackgroundTasks isn't wired by FastAPI
    from .worker import ingest_document_task
    await ingest_document_task(document_id, s3_path, agent_id, tenant_id)


@app.get('/documents/{agent_id}')
async def list_documents(agent_id: str):
    async for session in get_session():
        q = await session.execute(
            "SELECT id, filename, file_path, embedding_status, uploaded_at FROM documents WHERE agent_id = :agent",
            {'agent': agent_id}
        )
        # Use ORM mapping via the Document model
        rows = await session.execute(
            "SELECT id FROM documents WHERE agent_id = :agent ORDER BY uploaded_at DESC",
            {'agent': agent_id}
        )
        ids = [r[0] for r in rows.fetchall()]
        docs = []
        for did in ids:
            d = await session.get(Document, did)
            docs.append({'id': str(d.id), 'filename': d.filename, 'file_path': d.file_path, 'status': d.embedding_status, 'uploaded_at': d.uploaded_at.isoformat() if d.uploaded_at else None})
        return {'documents': docs}


@app.get('/health')
async def health():
    checks = {'db': False, 'minio': False, 'chroma': False}
    # DB check
    try:
        async for session in get_session():
            await session.execute('SELECT 1')
            checks['db'] = True
    except Exception:
        checks['db'] = False

    # MinIO check
    try:
        client = get_minio_client()
        # ensure bucket check doesn't raise
        from botocore.exceptions import BotoCoreError  # type: ignore
        try:
            exists = client.bucket_exists(os.getenv('MINIO_BUCKET', 'voiceflow'))
            checks['minio'] = True
        except Exception:
            checks['minio'] = False
    except Exception:
        checks['minio'] = False

    # Chroma check
    try:
        from .chroma_helper import _get_client
        c = _get_client()
        _ = c.list_collections()
        checks['chroma'] = True
    except Exception:
        checks['chroma'] = False

    status = 200 if all(checks.values()) else 503
    return JSONResponse({'status': 'ok' if all(checks.values()) else 'degraded', 'checks': checks}, status_code=status)


@app.get('/metrics')
async def get_metrics():
    return metrics


@app.post('/ingest/trigger/{document_id}')
async def trigger_ingest(document_id: str, background_tasks: BackgroundTasks):
    # Fetch document metadata from DB and schedule ingestion
    async for session in get_session():
        doc = await session.get(Document, document_id)
        if not doc:
            raise HTTPException(404, 'Document not found')
        schedule_ingestion(background_tasks, str(doc.id), doc.file_path, str(doc.agent_id), str(doc.tenant_id))
        return {'status': 'scheduled'}


    ### Agent-runner proxy endpoints (backend as orchestrator)
    async def _forward_to_runner(request: Request, method: str, path: str, json_body=None):
        """Forward an incoming request to the configured agent-runner service.

        Preserves Authorization header if present.
        Returns parsed JSON or raises HTTPException on failure.
        """
        headers = {}
        auth = request.headers.get('authorization')
        if auth:
            headers['Authorization'] = auth

        url = AGENT_RUNNER_URL.rstrip('/') + path
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.request(method, url, json=json_body, headers=headers, timeout=30.0)
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Failed to contact agent-runner: {e}")

        if resp.status_code >= 400:
            # attempt to forward runner's error message
            try:
                data = resp.json()
            except Exception:
                data = {'detail': resp.text}
            raise HTTPException(status_code=resp.status_code, detail=data)

        try:
            return resp.json()
        except Exception:
            return {'result': resp.text}


    @app.get('/runner/agents')
    async def runner_list_agents(request: Request):
        return await _forward_to_runner(request, 'GET', '/agents')


    @app.post('/runner/agents')
    async def runner_create_agent(request: Request):
        payload = await request.json()
        return await _forward_to_runner(request, 'POST', '/agents', json_body=payload)


    @app.get('/runner/pipelines')
    async def runner_list_pipelines(request: Request):
        return await _forward_to_runner(request, 'GET', '/pipelines')


    @app.post('/runner/pipelines')
    async def runner_create_pipeline(request: Request):
        payload = await request.json()
        return await _forward_to_runner(request, 'POST', '/pipelines', json_body=payload)


    @app.post('/runner/pipelines/{pipeline_id}/trigger')
    async def runner_trigger_pipeline(pipeline_id: int, request: Request):
        payload = None
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        return await _forward_to_runner(request, 'POST', f'/pipelines/{pipeline_id}/trigger', json_body=payload)


    @app.get('/runner/agents/{agent_id}')
    async def runner_get_agent(agent_id: int, request: Request):
        return await _forward_to_runner(request, 'GET', f'/agents/{agent_id}')


    @app.put('/runner/agents/{agent_id}')
    async def runner_update_agent(agent_id: int, request: Request):
        payload = await request.json()
        return await _forward_to_runner(request, 'PUT', f'/agents/{agent_id}', json_body=payload)


    @app.delete('/runner/agents/{agent_id}')
    async def runner_delete_agent(agent_id: int, request: Request):
        return await _forward_to_runner(request, 'DELETE', f'/agents/{agent_id}')


    @app.post('/runner/agents/{agent_id}/pause')
    async def runner_pause_agent(agent_id: int, request: Request):
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        return await _forward_to_runner(request, 'POST', f'/agents/{agent_id}/pause', json_body=payload)


    @app.post('/runner/agents/{agent_id}/activate')
    async def runner_activate_agent(agent_id: int, request: Request):
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        return await _forward_to_runner(request, 'POST', f'/agents/{agent_id}/activate', json_body=payload)


    @app.get('/runner/pipelines/{pipeline_id}')
    async def runner_get_pipeline(pipeline_id: int, request: Request):
        return await _forward_to_runner(request, 'GET', f'/pipelines/{pipeline_id}')


    @app.put('/runner/pipelines/{pipeline_id}')
    async def runner_update_pipeline(pipeline_id: int, request: Request):
        payload = await request.json()
        return await _forward_to_runner(request, 'PUT', f'/pipelines/{pipeline_id}', json_body=payload)


    @app.delete('/runner/pipelines/{pipeline_id}')
    async def runner_delete_pipeline(pipeline_id: int, request: Request):
        return await _forward_to_runner(request, 'DELETE', f'/pipelines/{pipeline_id}')


    @app.get('/runner/health')
    async def runner_health(request: Request):
        return await _forward_to_runner(request, 'GET', '/health')


    @app.get('/runner/metrics')
    async def runner_metrics(request: Request):
        return await _forward_to_runner(request, 'GET', '/metrics')


class PipelineAgentCreate(BaseModel):
    tenant_id: str
    name: str
    agent_type: str
    agent_id: Optional[str] = None
    config: Optional[dict] = None


@app.post('/admin/pipeline_agents')
async def create_pipeline_agent(payload: PipelineAgentCreate, api_key=Depends(require_api_key), user=Depends(require_role('admin'))):
    async for session in get_session():
        pa = PipelineAgent(tenant_id=payload.tenant_id, name=payload.name, agent_type=payload.agent_type, agent_id=payload.agent_id, config=payload.config)
        session.add(pa)
        await session.commit()
        await session.refresh(pa)
        return {'id': str(pa.id), 'name': pa.name}


@app.get('/admin/pipeline_agents')
async def list_pipeline_agents(api_key=Depends(require_api_key), user=Depends(require_role('admin'))):
    async for session in get_session():
        res = await session.execute("SELECT id, tenant_id, agent_id, name, agent_type, config FROM pipeline_agents")
        rows = res.fetchall()
        out = []
        for r in rows:
            out.append({'id': str(r[0]), 'tenant_id': str(r[1]), 'agent_id': str(r[2]) if r[2] else None, 'name': r[3], 'agent_type': r[4], 'config': r[5]})
        return {'pipeline_agents': out}


class PipelineCreate(BaseModel):
    tenant_id: str
    name: str
    agent_id: Optional[str] = None
    stages: list


@app.post('/admin/pipelines')
async def create_pipeline(payload: PipelineCreate, api_key=Depends(require_api_key), user=Depends(require_role('admin'))):
    async for session in get_session():
        p = Pipeline(tenant_id=payload.tenant_id, name=payload.name, agent_id=payload.agent_id, stages=payload.stages)
        session.add(p)
        await session.commit()
        await session.refresh(p)
        return {'id': str(p.id), 'name': p.name}


@app.get('/admin/pipelines')
async def list_pipelines(api_key=Depends(require_api_key), user=Depends(require_role('admin'))):
    async for session in get_session():
        res = await session.execute("SELECT id, tenant_id, agent_id, name, stages FROM pipelines")
        rows = res.fetchall()
        out = []
        for r in rows:
            out.append({'id': str(r[0]), 'tenant_id': str(r[1]), 'agent_id': str(r[2]) if r[2] else None, 'name': r[3], 'stages': r[4]})
        return {'pipelines': out}


@app.post('/admin/pipelines/trigger')
async def trigger_pipeline(pipeline_id: str, target_agent_id: Optional[str] = None, background_tasks: BackgroundTasks = None, api_key=Depends(require_api_key), user=Depends(require_role('admin'))):
    """Trigger a pipeline run asynchronously. For pre-call pipelines, target_agent_id may be provided to prime that agent."""
    # Fetch pipeline definition
    async for session in get_session():
        p = await session.get(Pipeline, pipeline_id)
        if not p:
            raise HTTPException(status_code=404, detail='Pipeline not found')
        # Schedule an async task to run stages
        async def _run_pipeline():
            from .worker import run_pipeline_stages
            try:
                await run_pipeline_stages(pipeline_id, target_agent_id)
            except Exception:
                logger.exception('Pipeline run failed')

        if background_tasks is not None:
            background_tasks.add_task(asyncio.create_task, _run_pipeline())
            return {'status': 'scheduled'}
        else:
            asyncio.create_task(_run_pipeline())
            return {'status': 'scheduled'}
