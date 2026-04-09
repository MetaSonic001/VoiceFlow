"""
/api/runner routes — mirrors Express src/routes/runner.ts
POST /chat, GET /agent/:agentId, POST /audio
"""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Agent, CallLog
from app.config import settings

logger = logging.getLogger("voiceflow.runner")
router = APIRouter()

def _tenant_key(request: Request) -> str:
    return request.headers.get("x-tenant-id", get_remote_address(request))

limiter = Limiter(key_func=_tenant_key, storage_uri=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1")


@router.post("/chat")
@limiter.limit("30/minute")
async def chat(request: Request, request_data: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    message = request_data.get("message", "").strip()
    agent_id = request_data.get("agentId")
    session_id = request_data.get("sessionId", "default")

    if not message:
        return JSONResponse({"error": "\"message\" is required"}, status_code=400)
    if not agent_id:
        return JSONResponse({"error": "\"agentId\" is required"}, status_code=400)

    # Verify agent belongs to tenant
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    # Full RAG pipeline
    from app.services.rag_service import process_query
    chat_start = datetime.now(timezone.utc)
    rag_result = await process_query(db, auth.tenant_id, agent_id, message, session_id)
    response_text = rag_result.get("response", "No response generated.")

    # Log the interaction
    try:
        log = CallLog(
            tenantId=auth.tenant_id,
            agentId=agent_id,
            callerPhone=None,
            startedAt=chat_start,
            endedAt=datetime.now(timezone.utc),
            durationSeconds=0,
            transcript=json.dumps([
                {"role": "user", "content": message},
                {"role": "assistant", "content": response_text},
            ]),
        )
        db.add(log)
        await db.commit()
    except Exception:
        logger.exception("Failed to persist chat log")

    return {"response": response_text, "agentId": agent_id, "sessionId": session_id}


@router.get("/agent/{agent_id}")
async def get_agent_info(agent_id: str, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    from app.models import Document
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    from sqlalchemy import func
    dc = await db.execute(select(func.count(Document.id)).where(Document.agentId == agent_id))
    doc_count = dc.scalar() or 0

    return {
        "id": agent.id,
        "name": agent.name,
        "systemPrompt": agent.systemPrompt,
        "voiceType": agent.voiceType,
        "llmPreferences": agent.llmPreferences,
        "tokenLimit": agent.tokenLimit,
        "contextWindowStrategy": agent.contextWindowStrategy,
        "createdAt": agent.createdAt.isoformat() if agent.createdAt else None,
        "_count": {"documents": doc_count},
    }


@router.post("/audio")
async def process_audio(
    audio: UploadFile = File(...),
    agentId: str = Form(...),
    sessionId: str = Form("default"),
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Process uploaded audio: STT via Groq Whisper → RAG → response."""
    audio_bytes = await audio.read()

    # Step 1: Speech-to-text via Groq Whisper API
    transcript = ""
    try:
        import httpx
        groq_key = settings.GROQ_API_KEY
        # Try to get tenant-specific key
        try:
            from app.services.credentials import decrypt_credential
            from app.models import Tenant
            result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
            tenant = result.scalar_one_or_none()
            if tenant and tenant.settings and tenant.settings.get("groqApiKey"):
                groq_key = decrypt_credential(tenant.settings["groqApiKey"])
        except Exception:
            pass

        if groq_key:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {groq_key}"},
                    files={"file": (audio.filename or "audio.webm", audio_bytes, audio.content_type or "audio/webm")},
                    data={"model": "whisper-large-v3-turbo", "language": "en"},
                )
                if resp.status_code == 200:
                    transcript = resp.json().get("text", "")
    except Exception as e:
        logger.warning("STT failed: %s", e)

    if not transcript:
        return {"transcript": "", "response": "Could not transcribe audio. Please try again or use text chat.", "agentId": agentId, "sessionId": sessionId}

    # Step 2: Process through RAG pipeline (reuse chat logic)
    result = await db.execute(select(Agent).where(Agent.id == agentId, Agent.tenantId == auth.tenant_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    from app.services.rag_service import process_query
    rag_result = await process_query(db, auth.tenant_id, agentId, transcript, sessionId)
    response_text = rag_result.get("response", "No response generated.")

    # Log
    try:
        log = CallLog(
            tenantId=auth.tenant_id, agentId=agentId, type="voice",
            startedAt=datetime.now(timezone.utc), endedAt=datetime.now(timezone.utc),
            transcript=json.dumps([
                {"role": "user", "content": transcript},
                {"role": "assistant", "content": response_text},
            ]),
        )
        db.add(log)
        await db.commit()
    except Exception:
        logger.exception("Failed to persist audio log")

    return {"transcript": transcript, "response": response_text, "agentId": agentId, "sessionId": sessionId}
