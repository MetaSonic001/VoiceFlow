"""
/api/rag routes — mirrors Express src/routes/rag.ts
Query and conversation management.
"""
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Agent, CallLog, Tenant
from app.config import settings

logger = logging.getLogger("voiceflow.rag")
router = APIRouter()


@router.post("/query")
async def rag_query(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    query = body.get("query", "").strip()
    agent_id = body.get("agentId")
    session_id = body.get("sessionId", "default")

    if not query or not agent_id:
        return JSONResponse({"error": "query and agentId are required"}, status_code=400)

    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
    agent = result.scalar_one_or_none()

    system_prompt = "You are a helpful AI assistant."
    if agent and agent.systemPrompt:
        system_prompt = agent.systemPrompt

    # Get Groq key
    groq_key = settings.GROQ_API_KEY
    tr = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = tr.scalar_one_or_none()
    if tenant and tenant.settings:
        k = tenant.settings.get("groqApiKey")
        if k and isinstance(k, str) and k.startswith("gsk_"):
            groq_key = k

    response_text = "I don't have enough context. Please configure a Groq API key."
    if groq_key:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": query},
                        ],
                        "max_tokens": 4096,
                        "temperature": 0.7,
                    },
                )
                if resp.status_code == 200:
                    response_text = resp.json()["choices"][0]["message"]["content"]
        except Exception:
            logger.exception("Groq API call failed")

    return {"response": response_text, "agentId": agent_id, "sessionId": session_id}


@router.get("/conversation/{session_id}")
async def get_conversation(session_id: str, agentId: str = "", auth: AuthContext = Depends(get_auth)):
    # Simplified — no Redis in Python backend demo
    return {"sessionId": session_id, "conversation": []}


@router.delete("/conversation/{session_id}")
async def delete_conversation(session_id: str, auth: AuthContext = Depends(get_auth)):
    return JSONResponse(None, status_code=204)
