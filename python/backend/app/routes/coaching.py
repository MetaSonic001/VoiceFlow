"""
Coaching Card routes — AI Call Coach approval workflow.

When analyze_call() produces coaching insights, they are stored as
CoachingCard rows. Tenant admins review, approve, or reject them here.
Approved cards are automatically merged into the agent's systemPrompt.

GET  /api/coaching/                         — list pending coaching cards
GET  /api/coaching/{card_id}                — get card detail
POST /api/coaching/{card_id}/approve        — approve and merge into agent prompt
POST /api/coaching/{card_id}/reject         — reject a card
GET  /api/coaching/agents/{agent_id}/report — full coaching report for an agent
"""
from __future__ import annotations

import re as _re
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import CoachingCard, Agent

logger = logging.getLogger("voiceflow.coaching_routes")
router = APIRouter()

_INJECTION_BLOCKLIST = _re.compile(
    r"(ignore\s+previous|forget\s+(all|everything|prior)|new\s+instructions?|system\s*:\s*|<\s*/?\s*(system|inst|s)|\[INST\]|\[/INST\]|you\s+are\s+now|act\s+as\s+a|disregard|jailbreak|DAN\s+mode)",
    _re.IGNORECASE,
)


def _sanitize_prompt_delta(delta: str | None) -> str | None:
    """Strip prompt-injection patterns from a coaching card delta before appending to systemPrompt."""
    if not delta:
        return delta
    if _INJECTION_BLOCKLIST.search(delta):
        logger.warning("[coaching] blocking prompt delta containing injection pattern")
        return None
    # Limit size to prevent system prompt bloat
    return delta[:2000]


def _card_dict(c: CoachingCard) -> dict:
    return {
        "id": c.id,
        "agentId": c.agentId,
        "callLogId": c.callLogId,
        "status": c.status,
        "observation": c.observation,
        "suggestedPromptDelta": c.suggestedPromptDelta,
        "impactScore": c.impactScore,
        "approvedBy": c.approvedBy,
        "approvedAt": c.approvedAt.isoformat() if c.approvedAt else None,
        "appliedAt": c.appliedAt.isoformat() if c.appliedAt else None,
        "createdAt": c.createdAt.isoformat() if c.createdAt else None,
    }


@router.get("/")
async def list_coaching_cards(
    status: str | None = None,
    agent_id: str | None = None,
    limit: int = 50,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    where = [CoachingCard.tenantId == auth.tenant_id]
    if status:
        where.append(CoachingCard.status == status)
    if agent_id:
        where.append(CoachingCard.agentId == agent_id)
    result = await db.execute(
        select(CoachingCard).where(*where)
        .order_by(CoachingCard.createdAt.desc())
        .limit(limit)
    )
    cards = result.scalars().all()
    return [_card_dict(c) for c in cards]


@router.get("/{card_id}")
async def get_coaching_card(
    card_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CoachingCard).where(CoachingCard.id == card_id, CoachingCard.tenantId == auth.tenant_id)
    )
    card = result.scalar_one_or_none()
    if not card:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return _card_dict(card)


@router.post("/{card_id}/approve")
async def approve_coaching_card(
    card_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Approve a coaching card and automatically merge the suggestedPromptDelta
    into the agent's systemPrompt.  The delta is appended as a new instruction block.
    """
    card_result = await db.execute(
        select(CoachingCard).where(CoachingCard.id == card_id, CoachingCard.tenantId == auth.tenant_id)
    )
    card = card_result.scalar_one_or_none()
    if not card:
        return JSONResponse({"error": "Not found"}, status_code=404)
    if card.status != "pending":
        return JSONResponse({"error": f"Card is already {card.status}"}, status_code=400)

    # Merge the prompt delta into the agent's system prompt
    agent_result = await db.execute(
        select(Agent).where(Agent.id == card.agentId, Agent.tenantId == auth.tenant_id)
    )
    agent = agent_result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    if card.suggestedPromptDelta:
        sanitized_delta = _sanitize_prompt_delta(card.suggestedPromptDelta)
        if sanitized_delta:
            current_prompt = agent.systemPrompt or ""
            separator = "\n\n--- Coaching Card Applied ---\n"
            agent.systemPrompt = current_prompt + separator + sanitized_delta
            card.appliedAt = datetime.now(timezone.utc)

    card.status = "approved"
    card.approvedBy = auth.user_id
    card.approvedAt = datetime.now(timezone.utc)
    await db.commit()

    logger.info("[coaching] card %s approved and applied to agent %s", card_id, card.agentId)
    return {
        "status": "approved",
        "applied": bool(card.suggestedPromptDelta),
        "agentId": card.agentId,
    }


@router.post("/{card_id}/reject")
async def reject_coaching_card(
    card_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    card_result = await db.execute(
        select(CoachingCard).where(CoachingCard.id == card_id, CoachingCard.tenantId == auth.tenant_id)
    )
    card = card_result.scalar_one_or_none()
    if not card:
        return JSONResponse({"error": "Not found"}, status_code=404)
    card.status = "rejected"
    card.approvedBy = auth.user_id
    await db.commit()
    return {"status": "rejected"}


@router.get("/agents/{agent_id}/report")
async def get_coaching_report(
    agent_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Full coaching history for an agent with stats."""
    result = await db.execute(
        select(CoachingCard).where(
            CoachingCard.agentId == agent_id,
            CoachingCard.tenantId == auth.tenant_id,
        ).order_by(CoachingCard.createdAt.desc())
    )
    cards = result.scalars().all()
    pending = [c for c in cards if c.status == "pending"]
    approved = [c for c in cards if c.status == "approved"]
    rejected = [c for c in cards if c.status == "rejected"]
    avg_impact = (
        sum(c.impactScore for c in approved if c.impactScore) / len([c for c in approved if c.impactScore])
        if any(c.impactScore for c in approved) else None
    )
    return {
        "agent_id": agent_id,
        "total": len(cards),
        "pending": len(pending),
        "approved": len(approved),
        "rejected": len(rejected),
        "avg_impact_score": round(avg_impact, 3) if avg_impact else None,
        "cards": [_card_dict(c) for c in cards[:20]],  # last 20
    }


@router.post("/from-recording")
async def create_coaching_card_from_recording(
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a coaching card manually from a recording review.

    Human supervisors mark a call as Good/Bad via the Recordings UI and submit a note.
    - "good"  → creates a positive few-shot example (RetrainingExample) for the agent
    - "bad"   → uses Groq to generate a corrective prompt delta, creates a pending CoachingCard

    Body:
    {
      "recording_id": "...",   // or "call_log_id"
      "call_log_id": "...",
      "agent_id": "...",
      "rating": "good" | "bad",
      "note": "Agent gave wrong refund policy"
    }
    """
    from app.models import CallLog, CallRecording, RetrainingExample, Tenant
    from app.services.credentials import decrypt_safe
    from app.config import settings as app_settings
    import uuid, httpx, json as json_mod

    body = await request.json()
    recording_id = body.get("recording_id", "")
    call_log_id = body.get("call_log_id", "") or recording_id
    agent_id = body.get("agent_id", "")
    rating = (body.get("rating") or "").lower()
    note = (body.get("note") or "").strip()[:1000]

    if rating not in ("good", "bad"):
        return JSONResponse({"error": "rating must be 'good' or 'bad'"}, status_code=400)
    if not agent_id:
        return JSONResponse({"error": "agent_id is required"}, status_code=400)

    # Load the call log for transcript
    call_log = None
    if call_log_id:
        log_res = await db.execute(
            select(CallLog).where(CallLog.id == call_log_id, CallLog.tenantId == auth.tenant_id)
        )
        call_log = log_res.scalar_one_or_none()

    transcript_text = ""
    if call_log:
        t = call_log.transcript
        if isinstance(t, str):
            try:
                turns = json_mod.loads(t)
                transcript_text = "\n".join(f"{turn.get('role','?')}: {turn.get('content','')}" for turn in turns[:20])
            except Exception:
                transcript_text = t[:1000]
        elif isinstance(t, list):
            transcript_text = "\n".join(f"{turn.get('role','?')}: {turn.get('content','')}" for turn in t[:20])

    if rating == "good":
        # Create a positive RetrainingExample (few-shot)
        if call_log and transcript_text:
            # Extract best Q&A pair from transcript
            turns = []
            if isinstance(call_log.transcript, list):
                turns = call_log.transcript
            elif isinstance(call_log.transcript, str):
                try:
                    turns = json_mod.loads(call_log.transcript)
                except Exception:
                    pass
            # Find last user→assistant exchange
            user_q, agent_a = "", ""
            for i, turn in enumerate(turns):
                if turn.get("role") == "user":
                    user_q = turn.get("content", "")
                elif turn.get("role") == "assistant" and user_q:
                    agent_a = turn.get("content", "")
            if user_q and agent_a:
                example = RetrainingExample(
                    id=str(uuid.uuid4()),
                    tenantId=auth.tenant_id,
                    agentId=agent_id,
                    callLogId=call_log_id or None,
                    userQuery=user_q[:500],
                    idealResponse=agent_a[:1000],
                    sourceType="recording_review",
                    status="approved",
                    notes=note or "Marked as good example via recording review",
                    approvedAt=datetime.now(timezone.utc),
                )
                db.add(example)
                await db.commit()
                return JSONResponse({
                    "status": "good_example_saved",
                    "retrainingExampleId": example.id,
                    "message": "Saved as a few-shot example for the agent.",
                })

        return JSONResponse({"status": "good_noted", "message": "Noted as a good call."})

    # rating == "bad" — generate a corrective coaching card via LLM
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    groq_key = app_settings.GROQ_API_KEY
    if tenant and tenant.settings:
        enc = tenant.settings.get("groqApiKey")
        if enc:
            dec = decrypt_safe(enc)
            if dec and dec.startswith("gsk_"):
                groq_key = dec

    suggested_delta = note  # fallback: use the note as-is
    observation_text = note

    if groq_key and transcript_text:
        try:
            async with httpx.AsyncClient(timeout=20) as http:
                resp = await http.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={
                        "model": "llama-3.1-8b-instant",
                        "messages": [
                            {"role": "system", "content": "You are an AI call quality expert. Analyze the call and generate a corrective instruction for the agent's prompt."},
                            {"role": "user", "content": (
                                f"The following call was marked as BAD by a supervisor.\n"
                                f"Supervisor note: {note}\n\n"
                                f"TRANSCRIPT (last 20 turns):\n{transcript_text[:2000]}\n\n"
                                f"Generate a SHORT corrective instruction (1-3 sentences) to add to the agent's system prompt "
                                f"to prevent this type of failure in future calls. Be specific and actionable."
                            )},
                        ],
                        "temperature": 0.4,
                        "max_tokens": 300,
                    },
                )
            if resp.status_code == 200:
                suggested_delta = resp.json()["choices"][0]["message"]["content"].strip()
                observation_text = f"Supervisor flagged: {note}" if note else "Flagged via recording review"
        except Exception:
            logger.warning("[coaching] LLM correction generation failed — using note as delta")

    card = CoachingCard(
        id=str(uuid.uuid4()),
        tenantId=auth.tenant_id,
        agentId=agent_id,
        callLogId=call_log_id or None,
        status="pending",
        observation=observation_text,
        suggestedPromptDelta=suggested_delta,
        impactScore=0.6,
    )
    db.add(card)
    await db.commit()

    return JSONResponse({
        "status": "coaching_card_created",
        "coachingCardId": card.id,
        "suggestedDelta": suggested_delta,
        "message": "Coaching card created — awaiting admin review before applying.",
    }, status_code=201)

