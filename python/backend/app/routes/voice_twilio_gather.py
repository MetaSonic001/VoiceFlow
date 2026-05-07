"""
Twilio Gather-loop voice handler — legacy inbound flow.

Renamed from voice.py (Prompt 3).
All routes live here so voice_inbound_router.py can delegate to handle_inbound_call().
"""
import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import uuid

from app.database import get_db, AsyncSessionLocal
from app.auth import AuthContext, get_auth
from app.models import Agent, CallLog, CoachingCard, Tenant
from app.config import settings
from app.services.credentials import decrypt_safe

# Pre-compiled pattern for extracting JSON from LLM markdown code blocks
_JSON_CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)

# Strip XML/SSML tags to prevent TwiML injection from LLM output
_XML_TAG_RE = re.compile(r"<[^>]+>")


# Detect LLM refusal phrases so we can rephrase gracefully for the caller.
_REFUSAL_RE = re.compile(
    r"\bI(?:'m| am) (?:not able|unable) to\b|\bI cannot\b|\bI can't\b"
    r"|\bcannot assist\b|\bnot something I can\b",
    re.I,
)


def _sanitize_for_twiml(text: str) -> str:
    """Remove XML/SSML tags, escape special chars, and guard against TwiML injection."""
    text = _XML_TAG_RE.sub("", text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.strip()
    # Leaked JSON (LLM returned a tool-call object instead of prose)
    if text.startswith("{") and text.endswith("}"):
        return "Could you please repeat that? I want to make sure I give you the right information."
    # LLM refusal — rephrase as a graceful deflection rather than reading it aloud
    if _REFUSAL_RE.search(text):
        return ("That's a bit outside what I can help with on this call. "
                "Let me connect you with someone who can assist. One moment.")
    return text or "I'm sorry, I couldn't process that."

logger = logging.getLogger("voiceflow.gather")
router = APIRouter()


def _get_twilio_creds(tenant_settings: dict) -> tuple[str | None, str | None]:
    """Extract and decrypt Twilio credentials from tenant settings."""
    sid = tenant_settings.get("twilioAccountSid")
    token_enc = tenant_settings.get("twilioAuthToken")
    if not sid or not token_enc:
        return None, None
    return sid, decrypt_safe(token_enc)


def _validate_twilio_signature(request: Request, form_data: dict) -> bool:
    """Return True if Twilio signature is valid (or Twilio creds not configured)."""
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN
    if not account_sid or not auth_token:
        return True
    try:
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(auth_token)
        signature = request.headers.get("X-Twilio-Signature", "")
        proto = request.headers.get("x-forwarded-proto", "https")
        host = request.headers.get("host", "localhost")
        url = f"{proto}://{host}{request.url.path}"
        return validator.validate(url, form_data, signature)
    except Exception:
        logger.warning("[gather] signature validation error — allowing request")
        return True


# ── Public function called by voice_inbound_router ───────────────────────────

async def handle_inbound_call(agent: Agent, request: Request) -> Response:
    """
    Return TwiML <Gather> that greets the caller and collects speech.
    Called by voice_inbound_router when telephony_provider == 'twilio-gather'.
    """
    from twilio.twiml.voice_response import VoiceResponse, Gather

    agent_name = agent.name or "your AI assistant"
    resp = VoiceResponse()

    # ── Pre-call caller enrichment ────────────────────────────────────────
    # Fetch caller phone from the inbound request and enrich via OmniCRM / HubSpot / Salesforce.
    # Store enriched context in Redis so the first gather turn can inject it.
    call_sid_inbound = ""
    try:
        form_data = await request.form()
        caller_phone_inbound = form_data.get("From", "")
        call_sid_inbound = form_data.get("CallSid", "")
        if caller_phone_inbound and call_sid_inbound:
            from app.services.crm_enrichment_service import enrich_caller, format_crm_context_for_prompt
            import redis.asyncio as _aioredis
            async with AsyncSessionLocal() as enrich_db:
                try:
                    caller_ctx = await enrich_caller(
                        tenant_id=agent.tenantId,
                        phone_number=caller_phone_inbound,
                        db=enrich_db,
                    )
                    if caller_ctx:
                        ctx_str = await format_crm_context_for_prompt(caller_ctx)
                        r = _aioredis.Redis(
                            host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                            db=2, decode_responses=True,
                        )
                        try:
                            await r.setex(f"caller_context:{call_sid_inbound}", 3600, ctx_str)
                        finally:
                            await r.aclose()
                except Exception:
                    logger.debug("[gather] caller enrichment error — continuing without context")
    except Exception:
        pass

    gather = Gather(
        input="dtmf speech",
        action=f"/api/voice/gather/{agent.id}",
        method="POST",
        speech_timeout="auto",
        language="en-US",
        num_digits=1,
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
    Twilio Gather-loop inbound: validate signature, greet and collect speech.
    """
    form = await request.form()
    if not _validate_twilio_signature(request, dict(form)):
        logger.warning("[gather] invalid Twilio signature on /gather-inbound/%s", agent_id)
        return Response(content="Forbidden", status_code=403, media_type="text/plain")

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
    if not _validate_twilio_signature(request, dict(form)):
        logger.warning("[gather] invalid Twilio signature on /gather/%s", agent_id)
        return Response(content="Forbidden", status_code=403, media_type="text/plain")

    speech_result = form.get("SpeechResult", "")
    digits = form.get("Digits", "")
    caller = form.get("From", "unknown")
    call_sid = form.get("CallSid", "")

    # If DTMF digits received, map to a text command for the RAG pipeline
    if digits and not speech_result:
        speech_result = f"[DTMF pressed: {digits}]"

    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    resp = VoiceResponse()

    if not agent or not speech_result:
        resp.say("I couldn't process that. Goodbye.", voice="Polly.Joanna")
        resp.hangup()
        return Response(content=str(resp), media_type="application/xml")
    # ── Supervisor whisper hint + pre-call CRM context ─────────────────────
    whisper_hint: str | None = None
    caller_crm_context: str | None = None
    if call_sid:
        try:
            import redis.asyncio as _aioredis
            r = _aioredis.Redis(
                host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                db=2, decode_responses=True,
            )
            try:
                hint_raw = await r.get(f"whisper_hint:{call_sid}")
                if hint_raw:
                    whisper_hint = hint_raw
                    await r.delete(f"whisper_hint:{call_sid}")  # consume once
                ctx_raw = await r.get(f"caller_context:{call_sid}")
                if ctx_raw:
                    caller_crm_context = ctx_raw
            finally:
                await r.aclose()
        except Exception:
            pass

    # Build effective query — prepend supervisor hint and/or caller CRM context
    effective_query = speech_result
    if whisper_hint:
        effective_query = f"[SUPERVISOR HINT — use this to guide your next response, do not read it aloud: {whisper_hint}]\n{effective_query}"
    if caller_crm_context:
        effective_query = f"[CALLER CONTEXT from CRM]: {caller_crm_context}\n[CALLER SAID]: {effective_query}"
    # Run RAG pipeline
    from app.services.rag_service import process_query
    from app.services.voice_tools import get_tools_for_agent, TOOL_REGISTRY, voice_tool_executor

    # Build per-agent tool specs from integrations config
    agent_integrations: dict = agent.integrations or {}
    tools_spec = get_tools_for_agent(agent_integrations)

    call_start = datetime.now(timezone.utc)
    answer = "I encountered an error processing your request."

    async def _rag_with_tools() -> str:
        """Run the full RAG + optional tool-use pipeline. Exceptions propagate to caller."""
        rag_result = await process_query(
            db, agent.tenantId, agent_id, effective_query, f"call-{call_sid}",
            tools=tools_spec if tools_spec else None,
        )
        if rag_result.get("tool_call"):
            tc = rag_result["tool_call"]
            tool_name = tc.get("tool_name", "")
            tool_args = tc.get("tool_arguments", {})
            logger.info("[voice_tools] mid-call tool=%s args=%s", tool_name, tool_args)
            tool_def = TOOL_REGISTRY.get(tool_name)
            tool_result: dict = {"error": f"Unknown tool: {tool_name}"}
            if tool_def:
                tool_result = await voice_tool_executor.execute(tool_def, tool_args, agent_integrations)
            import json as _json
            tool_result_str = _json.dumps(tool_result, default=str)
            follow_up = await process_query(
                db, agent.tenantId, agent_id,
                f"[Tool '{tool_name}' returned]: {tool_result_str}\nNow answer the caller naturally based on this result.",
                f"call-{call_sid}",
            )
            return follow_up.get("response") or "Done."
        return rag_result.get("response") or "I'm not sure how to answer that."

    try:
        # 6-second hard timeout — if LLM is slow the caller hears dead air.
        # On timeout we return a filler phrase and re-Gather so the conversation continues.
        answer = await asyncio.wait_for(_rag_with_tools(), timeout=6.0)
    except asyncio.TimeoutError:
        logger.warning(
            "[gather] LLM timeout >6s for agent=%s call=%s — returning filler",
            agent_id, call_sid,
        )
        answer = "I'm still looking that up — give me just one moment."
    except Exception:
        logger.exception("RAG pipeline failed during voice call")

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
            callSid=call_sid or None,
            callDirection="inbound",
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        log_id = log.id
        background_tasks.add_task(analyze_call, log_id, agent.tenantId)

        # Fire usage billing in background (managed-plan tenants billed per minute)
        from app.services.billing_service import log_call_usage
        background_tasks.add_task(
            log_call_usage,
            agent.tenantId,
            log_id,
            duration,
            None,   # providers_used=None → billing_service uses defaults
        )
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
        input="dtmf speech",
        action=f"/api/voice/gather/{agent_id}",
        method="POST",
        speech_timeout="auto",
        language="en-US",
        num_digits=1,
    )
    gather.say(_sanitize_for_twiml(answer), voice="Polly.Joanna")
    resp.append(gather)
    resp.say("Thank you for calling. Goodbye.", voice="Polly.Joanna")
    resp.hangup()

    return Response(content=str(resp), media_type="application/xml")


# ── Post-call delivery helper ────────────────────────────────────────────────

async def _generate_coaching_cards(
    call_log_id: str,
    analysis: dict,
    tenant_id: str,
    agent_id: str,
) -> None:
    """
    Generate CoachingCard rows from post-call analysis.
    Produces up to 3 specific, actionable coaching cards with suggested prompt deltas.
    Goal scoring, persona adherence, sentiment trajectory, and hallucination risk
    are all factored into the card's observation and impact score.
    """
    async with AsyncSessionLocal() as db:
        try:
            coaching_insights: list = analysis.get("coachingInsights", [])
            quality_score: int = analysis.get("qualityScore", 7)
            goal_achieved: bool | None = analysis.get("goalAchieved", None)
            hallucination_risk: str = analysis.get("hallucinationRisk", "low")
            missed: list = analysis.get("missedOpportunities", [])
            sentiment: str = analysis.get("sentiment", "neutral")

            if not coaching_insights and not missed:
                return  # Nothing actionable

            # Merge insights and missed opportunities, deduplicate
            all_insights = list(coaching_insights) + [f"Missed opportunity: {m}" for m in missed]
            all_insights = all_insights[:3]  # cap at 3 cards

            # Compute base impact score: inverse of quality (1=perfect→low impact, 10=terrible→high)
            base_impact = max(1, 11 - quality_score)
            # Boost for hallucination risk
            if hallucination_risk == "high":
                base_impact = min(10, base_impact + 3)
            elif hallucination_risk == "medium":
                base_impact = min(10, base_impact + 1)
            # Boost if goal not achieved
            if goal_achieved is False:
                base_impact = min(10, base_impact + 2)

            cards_created = 0
            for i, insight in enumerate(all_insights):
                # Craft a concrete prompt delta from the insight
                if "hallucin" in insight.lower() or hallucination_risk != "low":
                    prompt_delta = (
                        f"\n\n**ACCURACY RULE (added after coaching review)**: "
                        f"Always say 'I'm not certain, but...' when you lack confidence. "
                        f"Never fabricate specific facts, prices, or dates. "
                        f"Insight that triggered this: {insight}"
                    )
                elif "goal" in insight.lower() or goal_achieved is False:
                    prompt_delta = (
                        f"\n\n**GOAL COMPLETION RULE (added after coaching review)**: "
                        f"Actively drive conversations toward the goal. "
                        f"Before ending each call, confirm whether the caller's need was resolved. "
                        f"Insight: {insight}"
                    )
                else:
                    prompt_delta = (
                        f"\n\n**IMPROVEMENT (added after coaching review)**: {insight}"
                    )

                # Observation includes goal scoring and sentiment context
                observation = insight
                if i == 0 and goal_achieved is not None:
                    observation = (
                        f"[Goal {'ACHIEVED' if goal_achieved else 'NOT ACHIEVED'}, "
                        f"sentiment: {sentiment}, quality: {quality_score}/10] {insight}"
                    )

                card = CoachingCard(
                    id=str(uuid.uuid4()),
                    tenantId=tenant_id,
                    agentId=agent_id,
                    callLogId=call_log_id,
                    status="pending",
                    observation=observation,
                    suggestedPromptDelta=prompt_delta,
                    impactScore=base_impact,
                )
                db.add(card)
                cards_created += 1

            await db.commit()
            logger.info(
                "[coaching] generated %d coaching cards for call %s (quality=%d, goal=%s, hallucination=%s)",
                cards_created, call_log_id, quality_score, goal_achieved, hallucination_risk,
            )
        except Exception:
            logger.exception("[coaching] failed to generate coaching cards for call %s", call_log_id)


async def _run_post_call_delivery(
    *,
    tenant_id: str,
    agent_id: str,
    call_log_id: str,
    transcript: str,
    analysis: dict,
    groq_key: Optional[str],
    caller_phone: str = "",
    call_duration: int = 0,
    call_sid: str = "",
    recording_url: str = "",
) -> None:
    """Fire-and-forget: lead extraction + CRM/Slack/webhook delivery."""
    try:
        from app.services.post_call_delivery import deliver_post_call
        await deliver_post_call(
            tenant_id=tenant_id,
            agent_id=agent_id,
            call_log_id=call_log_id,
            transcript=transcript,
            analysis=analysis,
            groq_key=groq_key,
            caller_phone=caller_phone,
            call_duration=call_duration,
            call_sid=call_sid,
            recording_url=recording_url,
        )
    except Exception:
        logger.exception("[post_call] delivery pipeline failed for call %s", call_log_id)


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
- "coachingInsights": array of specific improvement suggestions for the agent
- "goalAchieved": boolean — did the agent achieve its likely goal?
- "missedOpportunities": array of moments the agent could have done better
- "hallucinationRisk": "low" | "medium" | "high" — did any agent response seem fabricated?

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

                    # ── Generate AI Coaching Cards ────────────────────────────
                    asyncio.create_task(
                        _generate_coaching_cards(call_log_id, analysis, log.tenantId, log.agentId)
                    )

                    # ── AI Call Coach + CRM delivery ─────────────────────────
                    asyncio.create_task(
                        _run_post_call_delivery(
                            tenant_id=log.tenantId,
                            agent_id=log.agentId,
                            call_log_id=call_log_id,
                            transcript=transcript,
                            analysis=analysis,
                            groq_key=groq_key,
                            caller_phone=log.callerPhone or "",
                            call_duration=log.durationSeconds or 0,
                            call_sid=log.callSid or "",
                        )
                    )
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
