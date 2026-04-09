"""
/api/runner routes — mirrors Express src/routes/runner.ts
POST /chat, GET /agent/:agentId, POST /audio
"""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Agent, CallLog
from app.config import settings

logger = logging.getLogger("voiceflow.runner")
router = APIRouter()


@router.post("/chat")
async def chat(request_data: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
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
):
    # Basic stub — full ASR pipeline is complex
    return {
        "transcript": "[Audio processing not available in Python backend demo]",
        "response": "Audio processing requires the TTS microservice. Please use text chat instead.",
        "agentId": agentId,
        "sessionId": sessionId,
    }
