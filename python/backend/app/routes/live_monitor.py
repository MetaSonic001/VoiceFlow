"""
Live Call Monitor — real-time supervisor dashboard.

Endpoints
---------
GET  /api/live-monitor/calls                    — list all active calls for tenant
GET  /api/live-monitor/calls/{call_sid}          — get single active call detail
POST /api/live-monitor/calls/{call_sid}/takeover — initiate live transfer to human
POST /api/live-monitor/calls/{call_sid}/end      — force-end a live call
POST /api/live-monitor/calls/{call_sid}/note     — attach a supervisor note to active call
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.config import settings
from app.database import get_db, AsyncSessionLocal
from app.models import Agent, Tenant
from app.services.credentials import decrypt_safe

logger = logging.getLogger("voiceflow.live_monitor")
router = APIRouter()

# ──────────────────────────────────────────────────────────────────────────────
# Redis helpers
# ──────────────────────────────────────────────────────────────────────────────

def _redis() -> aioredis.Redis:
    return aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=2,
        decode_responses=True,
    )


async def _scan_active_calls(r: aioredis.Redis) -> list[dict[str, Any]]:
    """Return all call_state:* entries from Redis as dicts."""
    calls = []
    cursor = 0
    async for key in r.scan_iter("call_state:*"):
        raw = await r.get(key)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        call_sid = key.replace("call_state:", "", 1)
        data["call_sid"] = call_sid
        calls.append(data)
    return calls


async def _get_call_transcript(r: aioredis.Redis, call_sid: str) -> list[dict]:
    """Return recent transcript turns stored as live_transcript:{call_sid}."""
    raw = await r.get(f"live_transcript:{call_sid}")
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


async def _get_extracted_vars(r: aioredis.Redis, call_sid: str) -> dict:
    """Return extracted variables so far for a call, if stored."""
    raw = await r.get(f"extracted_vars:{call_sid}")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


async def _get_call_metadata(r: aioredis.Redis, call_sid: str) -> dict:
    """Return enriched metadata (caller_number, start_time) for a call."""
    raw = await r.get(f"call_meta:{call_sid}")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


# ──────────────────────────────────────────────────────────────────────────────
# Helpers to enrich active calls
# ──────────────────────────────────────────────────────────────────────────────

async def _enrich_call(call: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    """Add agent name and other useful fields to a raw call state dict."""
    agent_id = call.get("agent_id")
    if agent_id:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        call["agent_name"] = agent.name if agent else agent_id
    else:
        call["agent_name"] = "Unknown"

    meta = {}  # filled from call_meta key in calling code
    call.setdefault("caller_number", meta.get("caller_number", "Unknown"))
    call.setdefault("start_time", meta.get("start_time"))
    call.setdefault("sentiment", meta.get("sentiment", "neutral"))
    return call


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/live-monitor/calls
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/calls")
async def list_active_calls(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Return all currently active calls (from Redis) for this tenant."""
    r = _redis()
    try:
        all_calls = await _scan_active_calls(r)
        # Filter to this tenant
        tenant_calls = [c for c in all_calls if c.get("tenant_id") == auth.tenant_id]

        enriched = []
        for call in tenant_calls:
            sid = call["call_sid"]
            meta = await _get_call_metadata(r, sid)
            call.update(meta)
            call = await _enrich_call(call, db)
            call["transcript"] = await _get_call_transcript(r, sid)
            call["extracted_vars"] = await _get_extracted_vars(r, sid)
            # Compute duration
            start = call.get("start_time")
            if isinstance(start, (int, float)):
                call["duration_seconds"] = int(time.time() - start)
            else:
                call["duration_seconds"] = None
            enriched.append(call)

        return {"calls": enriched, "total": len(enriched)}
    finally:
        await r.aclose()


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/live-monitor/calls/{call_sid}
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/calls/{call_sid}")
async def get_active_call(
    call_sid: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get full detail for one active call."""
    r = _redis()
    try:
        raw = await r.get(f"call_state:{call_sid}")
        if not raw:
            raise HTTPException(404, "Call not found or already ended")
        call = json.loads(raw)
        if call.get("tenant_id") != auth.tenant_id:
            raise HTTPException(403, "Access denied")

        call["call_sid"] = call_sid
        meta = await _get_call_metadata(r, call_sid)
        call.update(meta)
        call = await _enrich_call(call, db)
        call["transcript"] = await _get_call_transcript(r, call_sid)
        call["extracted_vars"] = await _get_extracted_vars(r, call_sid)
        start = call.get("start_time")
        if isinstance(start, (int, float)):
            call["duration_seconds"] = int(time.time() - start)
        return call
    finally:
        await r.aclose()


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/live-monitor/calls/{call_sid}/takeover
# ──────────────────────────────────────────────────────────────────────────────

class TakeoverRequest(BaseModel):
    transfer_to: str    # E.164 number to transfer to
    whisper_message: Optional[str] = None  # message whispered to the human agent


@router.post("/calls/{call_sid}/takeover")
async def takeover_call(
    call_sid: str,
    body: TakeoverRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Live takeover: redirect an active Twilio call to a human agent via warm transfer.
    Uses Twilio's Calls API to redirect the call with new TwiML.
    """
    r = _redis()
    try:
        raw = await r.get(f"call_state:{call_sid}")
        if not raw:
            raise HTTPException(404, "Call not found or already ended")
        state = json.loads(raw)
        if state.get("tenant_id") != auth.tenant_id:
            raise HTTPException(403, "Access denied")
    finally:
        await r.aclose()

    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(403, "Tenant not found")

    s = tenant.settings or {}
    sid = s.get("twilioAccountSid")
    token_enc = s.get("twilioAuthToken")
    if not sid or not token_enc:
        raise HTTPException(400, "Twilio credentials not configured")
    token = decrypt_safe(token_enc)

    # Build new TwiML that dials the human
    to = body.transfer_to.strip()
    if not to.startswith("+"):
        raise HTTPException(400, "transfer_to must be E.164 format")

    whisper = body.whisper_message or "You have an incoming call transfer from VoiceFlow AI."
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>{whisper}</Say>
  <Dial>{to}</Dial>
</Response>"""

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls/{call_sid}.json",
                auth=(sid, token),
                data={"Twiml": twiml},
            )
        if resp.status_code not in (200, 201):
            detail = resp.json().get("message", "Twilio error")
            raise HTTPException(400, f"Transfer failed: {detail}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[live_monitor] takeover error call=%s: %s", call_sid, exc)
        raise HTTPException(502, "Failed to transfer call")

    logger.info("[live_monitor] takeover call=%s → %s tenant=%s", call_sid, to, auth.tenant_id)
    return {"success": True, "message": f"Call {call_sid} transferred to {to}"}


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/live-monitor/calls/{call_sid}/end
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/calls/{call_sid}/end")
async def end_call(
    call_sid: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Force-end a Twilio call."""
    r = _redis()
    try:
        raw = await r.get(f"call_state:{call_sid}")
        if not raw:
            raise HTTPException(404, "Call not found or already ended")
        state = json.loads(raw)
        if state.get("tenant_id") != auth.tenant_id:
            raise HTTPException(403, "Access denied")
    finally:
        await r.aclose()

    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(403, "Tenant not found")

    s = tenant.settings or {}
    sid = s.get("twilioAccountSid")
    token_enc = s.get("twilioAuthToken")
    if not sid or not token_enc:
        raise HTTPException(400, "Twilio credentials not configured")
    token = decrypt_safe(token_enc)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls/{call_sid}.json",
                auth=(sid, token),
                data={"Status": "completed"},
            )
        if resp.status_code not in (200, 201):
            raise HTTPException(400, "Failed to end call")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[live_monitor] end call error: %s", exc)
        raise HTTPException(502, "Failed to end call")

    logger.info("[live_monitor] force-ended call=%s tenant=%s", call_sid, auth.tenant_id)
    return {"success": True, "message": f"Call {call_sid} ended"}


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/live-monitor/calls/{call_sid}/note
# ──────────────────────────────────────────────────────────────────────────────

class NoteRequest(BaseModel):
    note: str


@router.post("/calls/{call_sid}/note")
async def add_supervisor_note(
    call_sid: str,
    body: NoteRequest,
    auth: AuthContext = Depends(get_auth),
):
    """Attach a supervisor note to an active call (stored in Redis)."""
    r = _redis()
    try:
        raw = await r.get(f"call_state:{call_sid}")
        if not raw:
            raise HTTPException(404, "Call not found")
        state = json.loads(raw)
        if state.get("tenant_id") != auth.tenant_id:
            raise HTTPException(403, "Access denied")

        notes_raw = await r.get(f"call_notes:{call_sid}")
        notes = json.loads(notes_raw) if notes_raw else []
        notes.append({
            "note": body.note[:500],
            "ts": time.time(),
            "supervisor": auth.user_id,
        })
        await r.setex(f"call_notes:{call_sid}", 7200, json.dumps(notes))
    finally:
        await r.aclose()

    return {"success": True}


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/live-monitor/calls/{call_sid}/whisper
# ──────────────────────────────────────────────────────────────────────────────

class WhisperRequest(BaseModel):
    hint: str


@router.post("/calls/{call_sid}/whisper")
async def inject_whisper_hint(
    call_sid: str,
    body: WhisperRequest,
    auth: AuthContext = Depends(get_auth),
):
    """
    Supervisor whisper: silently inject a hint into the AI agent's next context
    window so it guides the response without the caller hearing the instruction.

    The hint is stored in Redis with a 90-second TTL and consumed once by the
    voice_twilio_gather handler on the next speech turn.
    """
    r = _redis()
    try:
        raw = await r.get(f"call_state:{call_sid}")
        if not raw:
            raise HTTPException(404, "Call not found or already ended")
        state = json.loads(raw)
        if state.get("tenant_id") != auth.tenant_id:
            raise HTTPException(403, "Access denied")

        hint = body.hint[:500].strip()
        if not hint:
            raise HTTPException(400, "hint must not be empty")

        # TTL of 90s — must be consumed within one voice turn
        await r.setex(f"whisper_hint:{call_sid}", 90, hint)
        logger.info("[whisper] supervisor %s injected hint for call %s", auth.user_id, call_sid)
    finally:
        await r.aclose()

    return {"success": True, "hint": hint, "ttl_seconds": 90}
