"""
/api/rag routes — mirrors Express src/routes/rag.ts
Query and conversation management with full RAG pipeline.
"""
import logging
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Agent
from app.services.rag_service import (
    process_query,
    get_conversation_history,
    delete_conversation_history,
)
from app.config import settings

logger = logging.getLogger("voiceflow.rag")
router = APIRouter()

def _tenant_key(request: Request) -> str:
    return request.headers.get("x-tenant-id", get_remote_address(request))

limiter = Limiter(key_func=_tenant_key, storage_uri=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1")


@router.post("/query")
@limiter.limit("30/minute")
async def rag_query(request: Request, body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    query = body.get("query", "").strip()
    agent_id = body.get("agentId")
    session_id = body.get("sessionId", "default")

    if not query or not agent_id:
        return JSONResponse({"error": "query and agentId are required"}, status_code=400)

    # Verify agent belongs to tenant
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    # Full RAG pipeline: context injection → ChromaDB → policy scoring → prompt → Groq
    rag_result = await process_query(db, auth.tenant_id, agent_id, query, session_id)

    return {
        "response": rag_result.get("response", ""),
        "agentId": agent_id,
        "sessionId": session_id,
        "sources": rag_result.get("sources", []),
        "model": rag_result.get("model", ""),
        "documentsRetrieved": rag_result.get("documentsRetrieved", 0),
    }


@router.get("/conversation/{session_id}")
async def get_conversation(session_id: str, agentId: str = "", auth: AuthContext = Depends(get_auth)):
    """Get conversation history from Redis."""
    history = await get_conversation_history(auth.tenant_id, agentId, session_id)
    return {"sessionId": session_id, "conversation": history}


@router.delete("/conversation/{session_id}")
async def del_conversation(session_id: str, agentId: str = "", auth: AuthContext = Depends(get_auth)):
    """Delete conversation history from Redis."""
    await delete_conversation_history(auth.tenant_id, agentId, session_id)
    return Response(status_code=204)
