"""
/api/voice routes — Patent Claims 8, 12.
Twilio TwiML voice handling: inbound calls → STT → RAG pipeline → TTS response.
Post-call LLM analysis runs as a background task.
"""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.responses import Response, JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.auth import AuthContext, get_auth
from app.models import Agent, CallLog, Tenant
from app.config import settings
from app.services.credentials import decrypt_safe

logger = logging.getLogger("voiceflow.voice")
router = APIRouter()


def _get_twilio_creds(tenant_settings: dict) -> tuple[str | None, str | None]:
    """Extract and decrypt Twilio credentials from tenant settings."""
    sid = tenant_settings.get("twilioAccountSid")
    token_enc = tenant_settings.get("twilioAuthToken")
    if not sid or not token_enc:
        return None, None
    return sid, decrypt_safe(token_enc)


# ── Inbound call webhook (Twilio posts here) ────────────────────────────────

@router.post("/gather-inbound/{agent_id}")
async def voice_inbound(agent_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Twilio Gather-loop: greet and collect speech input.
    Called directly when telephony_provider == 'twilio-gather'.
    """
    from twilio.twiml.voice_response import VoiceResponse, Gather

    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    resp = VoiceResponse()
    if not agent:
        resp.say("Sorry, the requested agent is not available.", voice="Polly.Joanna")
        resp.hangup()
        return Response(content=str(resp), media_type="application/xml")

    agent_name = agent.name or "your AI assistant"
    gather = Gather(
        input="speech",
        action=f"/api/voice/gather/{agent_id}",
        method="POST",
        speech_timeout="auto",
        language="en-US",
    )
    gather.say(
        f"Hello, you've reached {agent_name}. How can I help you today?",
        voice="Polly.Joanna",
    )
    resp.append(gather)
    # If caller doesn't say anything
    resp.say("I didn't hear anything. Goodbye.", voice="Polly.Joanna")
    resp.hangup()

    return Response(content=str(resp), media_type="application/xml")


# ── Gather callback (speech recognized) ─────────────────────────────────────

@router.post("/gather/{agent_id}")
async def voice_gather(
    agent_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Twilio posts recognized speech here. We run it through the RAG pipeline
    and respond with TTS via TwiML <Say>.
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
        # Schedule post-call analysis as background task
        background_tasks.add_task(analyze_call, log.id, agent.tenantId)
    except Exception:
        logger.exception("Failed to persist voice call log")

    # Increment totalCalls
    try:
        agent.totalCalls = (agent.totalCalls or 0) + 1
        await db.commit()
    except Exception:
        pass

    # Respond with TTS and re-gather for multi-turn conversation
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
    Background task: analyze a completed call transcript with LLM.
    Stores sentiment, intent, key topics, and action items.
    """
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(CallLog).where(CallLog.id == call_log_id))
            log = result.scalar_one_or_none()
            if not log:
                return

            transcript = log.transcript or "[]"

            # Get Groq key
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
                logger.warning("No Groq key available for post-call analysis")
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
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={
                        "model": "llama-3.1-8b-instant",
                        "messages": [
                            {"role": "system", "content": "You are a call analysis assistant. Return valid JSON only."},
                            {"role": "user", "content": analysis_prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1024,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    # Parse the JSON from the response
                    try:
                        analysis = json.loads(content)
                    except json.JSONDecodeError:
                        # Try extracting JSON from markdown code block
                        import re
                        match = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
                        if match:
                            analysis = json.loads(match.group(1))
                        else:
                            analysis = {"summary": content, "sentiment": "unknown"}

                    log.analysis = analysis
                    await db.commit()
                    logger.info(f"Post-call analysis completed for call {call_log_id}")
                else:
                    logger.warning(f"Groq API returned {resp.status_code} for call analysis")

        except Exception:
            logger.exception(f"Post-call analysis failed for {call_log_id}")


# ── Voice status callback ───────────────────────────────────────────────────

@router.post("/gather-status/{agent_id}")
async def voice_status(agent_id: str, request: Request):
    """Twilio status callback (Gather-loop path) — logs call status changes."""
    form = await request.form()
    call_status = form.get("CallStatus", "unknown")
    call_sid = form.get("CallSid", "")
    logger.info(f"Call {call_sid} for agent {agent_id}: status={call_status}")
    return Response(status_code=204)


# ── List calls for an agent ─────────────────────────────────────────────────

@router.get("/calls/{agent_id}")
async def get_voice_calls(
    agent_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Return call logs with analysis for an agent."""
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
                "id": l.id,
                "callerPhone": l.callerPhone,
                "startedAt": l.startedAt.isoformat() if l.startedAt else None,
                "endedAt": l.endedAt.isoformat() if l.endedAt else None,
                "durationSeconds": l.durationSeconds,
                "transcript": l.transcript,
                "analysis": l.analysis,
                "rating": l.rating,
                "flaggedForRetraining": l.flaggedForRetraining,
            }
            for l in logs
        ]
    }
