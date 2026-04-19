"""
Twilio Gather-loop voice handler — legacy inbound flow.

Renamed from voice.py (Prompt 3).
All routes live here so voice_inbound_router.py can delegate to handle_inbound_call().
"""
import json
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.auth import AuthContext, get_auth
from app.models import Agent, CallLog, Tenant
from app.config import settings
from app.services.credentials import decrypt_safe

# Pre-compiled pattern for extracting JSON from LLM markdown code blocks
_JSON_CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)

logger = logging.getLogger("voiceflow.gather")
router = APIRouter()


def _get_twilio_creds(tenant_settings: dict) -> tuple[str | None, str | None]:
    """Extract and decrypt Twilio credentials from tenant settings."""
    sid = tenant_settings.get("twilioAccountSid")
    token_enc = tenant_settings.get("twilioAuthToken")
    if not sid or not token_enc:
        return None, None
    return sid, decrypt_safe(token_enc)


# ── Public function called by voice_inbound_router ───────────────────────────

async def handle_inbound_call(agent: Agent, request: Request) -> Response:
    """
    Return TwiML <Gather> that greets the caller and collects speech.
    Called by voice_inbound_router when telephony_provider == 'twilio-gather'.
    """
    from twilio.twiml.voice_response import VoiceResponse, Gather

    agent_name = agent.name or "your AI assistant"
    resp = VoiceResponse()
    gather = Gather(
        input="speech",
        action=f"/api/voice/gather/{agent.id}",
        method="POST",
        speech_timeout="auto",
        language="en-US",
    )
    gather.say(
        f"Hello, you've reached {agent_name}. How can I help you today?",
        voice="Polly.Joanna",
    )
    resp.append(gather)
    resp.say("I didn't hear anything. Goodbye.", voice="Polly.Joanna")
    resp.hangup()
    return Response(content=str(resp), media_type="application/xml")


# ── Inbound call webhook (Twilio posts here for gather-loop agents) ──────────

@router.post("/gather-inbound/{agent_id}")
async def voice_inbound(agent_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Twilio Gather-loop inbound: greet and collect speech.
    This route is kept for agents that still have Twilio's webhook set directly
    to /api/voice/gather-inbound/{agent_id}.
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        from twilio.twiml.voice_response import VoiceResponse

        resp = VoiceResponse()
        resp.say("Sorry, the requested agent is not available.", voice="Polly.Joanna")
        resp.hangup()
        return Response(content=str(resp), media_type="application/xml")

    return await handle_inbound_call(agent, request)


# ── Gather callback (speech recognized) ─────────────────────────────────────

@router.post("/gather/{agent_id}")
async def voice_gather(
    agent_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Twilio posts recognized speech here.
    Runs speech through the RAG pipeline and responds with TTS via TwiML <Say>.
    """
    from twilio.twiml.voice_response import VoiceResponse, Gather

    form = await request.form()
    speech_result = form.get("SpeechResult", "")
    caller = form.get("From", "unknown")
    call_sid = form.get("CallSid", "")

    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    resp = VoiceResponse()

    if not agent or not speech_result:
        resp.say("I couldn't process that. Goodbye.", voice="Polly.Joanna")
        resp.hangup()
        return Response(content=str(resp), media_type="application/xml")

    # Run RAG pipeline
    from app.services.rag_service import process_query

    call_start = datetime.now(timezone.utc)
    try:
        rag_result = await process_query(
            db, agent.tenantId, agent_id, speech_result, f"call-{call_sid}"
        )
        answer = rag_result.get("response", "I'm not sure how to answer that.")
    except Exception:
        logger.exception("RAG pipeline failed during voice call")
        answer = "I encountered an error processing your request."

    call_end = datetime.now(timezone.utc)
    duration = int((call_end - call_start).total_seconds())

    # Persist call log
    transcript = json.dumps([
        {"role": "user", "content": speech_result},
        {"role": "assistant", "content": answer},
    ])
    log_id: str | None = None
    try:
        log = CallLog(
            tenantId=agent.tenantId,
            agentId=agent_id,
            callerPhone=caller,
            startedAt=call_start,
            endedAt=call_end,
            durationSeconds=duration,
            transcript=transcript,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        log_id = log.id
        background_tasks.add_task(analyze_call, log_id, agent.tenantId)
    except Exception:
        logger.exception("Failed to persist voice call log")

    # Increment totalCalls
    try:
        agent.totalCalls = (agent.totalCalls or 0) + 1
        await db.commit()
    except Exception:
        pass

    # Re-gather for multi-turn conversation
    gather = Gather(
        input="speech",
        action=f"/api/voice/gather/{agent_id}",
        method="POST",
        speech_timeout="auto",
        language="en-US",
    )
    gather.say(answer, voice="Polly.Joanna")
    resp.append(gather)
    resp.say("Thank you for calling. Goodbye.", voice="Polly.Joanna")
    resp.hangup()

    return Response(content=str(resp), media_type="application/xml")


# ── Post-call LLM analysis (Claim 12) ───────────────────────────────────────

async def analyze_call(call_log_id: str, tenant_id: str):
    """
    Background task: analyse a completed call transcript with an LLM.
    Stores sentiment, intent, key topics, and action items in CallLog.analysis.
    """
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(CallLog).where(CallLog.id == call_log_id))
            log = result.scalar_one_or_none()
            if not log:
                return

            transcript = log.transcript or "[]"

            t_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
            tenant = t_result.scalar_one_or_none()
            groq_key = None
            if tenant and tenant.settings:
                enc_key = tenant.settings.get("groqApiKey")
                if enc_key:
                    decrypted = decrypt_safe(enc_key)
                    if decrypted.startswith("gsk_"):
                        groq_key = decrypted
            if not groq_key:
                groq_key = settings.GROQ_API_KEY
            if not groq_key:
                logger.warning("No Groq key for post-call analysis")
                return

            import httpx
            analysis_prompt = f"""Analyze this customer service call transcript. Return a JSON object with:
- "sentiment": overall sentiment (positive/neutral/negative)
- "intent": primary caller intent in 1-2 sentences
- "topics": array of key topics discussed
- "actionItems": array of follow-up actions needed
- "qualityScore": 1-10 rating of the AI agent's response quality
- "summary": 2-3 sentence summary

Transcript:
{transcript}"""

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {groq_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "llama-3.1-8b-instant",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a call analysis assistant. Return valid JSON only.",
                            },
                            {"role": "user", "content": analysis_prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1024,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    try:
                        analysis = json.loads(content)
                    except json.JSONDecodeError:
                        match = _JSON_CODE_BLOCK_RE.search(content)
                        if match:
                            analysis = json.loads(match.group(1))
                        else:
                            analysis = {"summary": content, "sentiment": "unknown"}

                    log.analysis = analysis
                    await db.commit()
                    logger.info("Post-call analysis completed for call %s", call_log_id)
                else:
                    logger.warning("Groq API returned %s for call analysis", resp.status_code)

        except Exception:
            logger.exception("Post-call analysis failed for %s", call_log_id)


# ── Status callback ──────────────────────────────────────────────────────────

@router.post("/gather-status/{agent_id}")
async def voice_status(agent_id: str, request: Request):
    """Twilio status callback for Gather-loop agents."""
    form = await request.form()
    call_status = form.get("CallStatus", "unknown")
    call_sid = form.get("CallSid", "")
    logger.info("Gather call %s agent=%s status=%s", call_sid, agent_id, call_status)
    return Response(status_code=204)


# ── List calls ───────────────────────────────────────────────────────────────

@router.get("/calls/{agent_id}")
async def get_voice_calls(
    agent_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Return recent call logs with post-call analysis for an agent."""
    result = await db.execute(
        select(CallLog)
        .where(CallLog.agentId == agent_id, CallLog.tenantId == auth.tenant_id)
        .order_by(CallLog.createdAt.desc())
        .limit(50)
    )
    logs = result.scalars().all()
    return {
        "calls": [
            {
                "id": log.id,
                "callerPhone": log.callerPhone,
                "startedAt": log.startedAt.isoformat() if log.startedAt else None,
                "endedAt": log.endedAt.isoformat() if log.endedAt else None,
                "durationSeconds": log.durationSeconds,
                "transcript": log.transcript,
                "analysis": log.analysis,
                "rating": log.rating,
                "flaggedForRetraining": log.flaggedForRetraining,
            }
            for log in logs
        ]
    }
