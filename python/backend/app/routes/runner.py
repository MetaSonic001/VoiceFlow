"""
/api/runner routes — mirrors Express src/routes/runner.ts
POST /chat, GET /agent/:agentId, POST /audio
"""
import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Agent, CallLog
from app.config import settings

logger = logging.getLogger("voiceflow.runner")
router = APIRouter()

MAX_RETRIES = 4


async def _call_groq(groq_key: str, system_prompt: str, message: str, max_tokens: int) -> str:
    """Call Groq with automatic retry on 429 rate-limit responses."""
    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(MAX_RETRIES):
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]

            if resp.status_code == 429:
                # Parse retry-after hint from Groq error body
                wait = 2.0 * (attempt + 1)  # default backoff
                try:
                    body = resp.json()
                    msg = body.get("error", {}).get("message", "")
                    m = re.search(r"try again in ([\d.]+)s", msg)
                    if m:
                        wait = float(m.group(1)) + 0.5  # add small buffer
                except Exception:
                    pass
                logger.info(f"Groq 429 — retrying in {wait:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})")
                await asyncio.sleep(wait)
                continue

            logger.warning(f"Groq API error: {resp.status_code} {resp.text}")
            return None

    logger.warning("Groq: all retries exhausted")
    return None


@router.post("/chat")
async def chat(request_data: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    message = request_data.get("message", "").strip()
    agent_id = request_data.get("agentId")
    session_id = request_data.get("sessionId", "default")

    if not message:
        return JSONResponse({"error": "\"message\" is required"}, status_code=400)
    if not agent_id:
        return JSONResponse({"error": "\"agentId\" is required"}, status_code=400)

    # Verify agent
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
    agent = result.scalar_one_or_none()

    system_prompt = "You are a helpful AI assistant. Provide clear, accurate, and concise responses."
    if agent and agent.systemPrompt:
        system_prompt = agent.systemPrompt

    token_limit = (agent.tokenLimit if agent else None) or 4096

    # Try to get tenant Groq key
    groq_key = settings.GROQ_API_KEY
    if agent:
        from app.models import Tenant
        tr = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
        tenant = tr.scalar_one_or_none()
        if tenant and tenant.settings:
            encrypted_key = tenant.settings.get("groqApiKey")
            if encrypted_key and isinstance(encrypted_key, str) and encrypted_key.startswith("gsk_"):
                groq_key = encrypted_key

    # Call Groq API with automatic retry on rate-limit
    response_text = "I'm sorry, the AI service is temporarily unavailable. Please try again in a moment."
    if groq_key:
        try:
            llm_reply = await _call_groq(groq_key, system_prompt, message, min(token_limit, 1024))
            if llm_reply:
                response_text = llm_reply
        except Exception:
            logger.exception("Groq API call failed")
    else:
        response_text = "No Groq API key configured. Please add one in Settings."

    # Log the interaction
    chat_start = datetime.now(timezone.utc)
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
