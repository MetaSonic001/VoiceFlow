"""
Exotel voice integration.

Exotel is India's leading cloud telephony platform with DLT (Distributed
Ledger Technology) regulatory compliance for the TRAI framework.

Endpoints:
  POST /api/voice/exotel/inbound/{agent_id}   — Exotel webhook (call connected)
  WS   /api/voice/exotel/stream/{agent_id}    — Real-time audio stream
  POST /api/voice/exotel/status/{agent_id}    — Call status callback

Exotel Passthru API guide:
  https://developer.exotel.com/api/
  https://developer.exotel.com/api/passthru

DLT Compliance:
  All outbound calls require a pre-approved DLT Template ID registered with
  TRAI via your telecom operator. Set EXOTEL_DLT_TEMPLATE_ID in environment
  or pass it per-agent in llmPreferences.exotelDltTemplateId.

Audio format:
  Exotel streams PCM 8kHz 16-bit mono over WebSocket.
  Same pipeline as Twilio Media Streams — reuses TTSRouter and STT service.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import struct
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Agent, CallLog, Tenant
from app.services.credentials import decrypt_safe
from app.services.semantic_vad import get_min_silence_ms
from app.services.stt_service import stt_service
from app.services.tts_router import TTSRouter
from app.services.voice_turn_merge import clear_turn_merge, integrate_user_text
from app.routes.voice_twilio_stream import _groq_key_for_tenant

logger = logging.getLogger("voiceflow.exotel")
router = APIRouter()
_tts = TTSRouter()

# Exotel audio: PCM 8kHz 16-bit mono (same frame size as Twilio μ-law)
_FRAME_BYTES = 320          # 20ms × 8000Hz × 2 bytes/sample
_SENSITIVITY_FRAMES = {"high": 12, "medium": 24, "low": 40}
_DEFAULT_SIL_FRAMES = 24
_INTERRUPT_RMS_THRESHOLD = 520.0   # 8k PCM RMS — responsive barge-in vs noise floor
_SILENCE_RMS_8K = 80.0


def _validate_exotel_webhook(request: Request, form_data: dict) -> bool:
    """
    Validate an inbound Exotel webhook request.

    Exotel does not sign webhooks like Twilio. Instead, we support an optional
    pre-shared secret: set EXOTEL_WEBHOOK_SECRET in the environment.  Exotel
    should then be configured to append ?token=<secret> to its callback URLs.
    If the env var is not set, all requests are allowed (suitable for dev).
    """
    secret = settings.EXOTEL_WEBHOOK_SECRET if hasattr(settings, "EXOTEL_WEBHOOK_SECRET") else None
    if not secret:
        import os as _os
        secret = _os.getenv("EXOTEL_WEBHOOK_SECRET")
    if not secret:
        return True
    # Accept token either as a query param or in the form body
    provided = (
        request.query_params.get("token")
        or form_data.get("token")
        or ""
    )
    return hmac.compare_digest(provided, secret)


# ── Credentials helper ───────────────────────────────────────────────────────

async def _exotel_creds(tenant_id: str) -> tuple[str | None, str | None, str | None]:
    """Return (exotel_sid, api_key, api_token) from tenant settings."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if tenant and tenant.settings:
            s = tenant.settings
            sid = s.get("exotelSid")
            api_key = s.get("exotelApiKey")
            api_token_enc = s.get("exotelApiToken")
            if sid and api_key and api_token_enc:
                return sid, api_key, decrypt_safe(api_token_enc)
    return None, None, None


# ── Audio helpers ────────────────────────────────────────────────────────────

def _pcm_rms(pcm_bytes: bytes) -> float:
    n = len(pcm_bytes) // 2
    if n == 0:
        return 0.0
    samples = struct.unpack(f"<{n}h", pcm_bytes[:n * 2])
    return (sum(s * s for s in samples) / n) ** 0.5


def _pcm8k_to_16k(pcm_8k: bytes) -> bytes:
    """Upsample 8kHz 16-bit mono PCM to 16kHz by linear interpolation."""
    n = len(pcm_8k) // 2
    if n == 0:
        return b""
    samples = struct.unpack(f"<{n}h", pcm_8k[:n * 2])
    out = []
    for i in range(n - 1):
        out.append(samples[i])
        out.append((samples[i] + samples[i + 1]) // 2)
    out.append(samples[-1])
    out.append(samples[-1])
    return struct.pack(f"<{len(out)}h", *out)


def _wav16k_to_pcm8k(wav_bytes: bytes) -> bytes:
    """Convert WAV to 8kHz 16-bit mono PCM for Exotel (downsample from TTSRouter output)."""
    import io
    from pydub import AudioSegment
    seg = AudioSegment.from_file(io.BytesIO(wav_bytes), format="wav")
    seg = seg.set_channels(1).set_frame_rate(8000).set_sample_width(2)
    return seg.raw_data


# ── Inbound webhook ───────────────────────────────────────────────────────────

@router.post("/inbound/{agent_id}")
async def exotel_inbound(agent_id: str, request: Request):
    """
    Exotel inbound webhook — Exotel calls this URL when a call is connected.

    Returns Exotel Passthru XML to connect to the WebSocket audio stream.
    Exotel Passthru docs: https://developer.exotel.com/api/passthru
    """
    form = await request.form()
    if not _validate_exotel_webhook(request, dict(form)):
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>',
            media_type="application/xml",
            status_code=403,
        )
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()

    if not agent:
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>Agent not found.</Say><Hangup/></Response>',
            media_type="application/xml",
            status_code=404,
        )

    proto = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("host", "localhost")
    ws_url = f"wss://{host}/api/voice/exotel/stream/{agent_id}"

    # Exotel Passthru XML — connects the call to our WebSocket
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{ws_url}">
      <Parameter name="agentId" value="{agent_id}"/>
    </Stream>
  </Connect>
</Response>"""

    logger.info("[exotel] inbound call to agent=%s", agent_id)
    return Response(content=xml, media_type="application/xml")


@router.post("/outbound/{agent_id}")
async def exotel_outbound(agent_id: str, request: Request):
    """
    Exotel AMD/outbound callback — called after dialling a contact.

    Exotel passes `Status` (answered/not-answered/busy) and `DialStatus`.
    """
    form = await request.form()
    status = (form.get("Status") or form.get("CallStatus") or "").lower()
    dial_status = (form.get("DialStatus") or "").lower()
    call_sid = form.get("CallSid", form.get("ExotelCallSid", ""))

    if status in ("not-answered", "busy", "failed") or dial_status in ("not-answered", "busy"):
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>',
            media_type="application/xml",
        )

    # Human answered — connect to stream
    proto = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("host", "localhost")
    ws_url = f"wss://{host}/api/voice/exotel/stream/{agent_id}"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{ws_url}">
      <Parameter name="agentId" value="{agent_id}"/>
      <Parameter name="callSid" value="{call_sid}"/>
    </Stream>
  </Connect>
</Response>"""
    return Response(content=xml, media_type="application/xml")


@router.post("/status/{agent_id}")
async def exotel_status(agent_id: str, request: Request):
    """Exotel status callback — log call status."""
    form = await request.form()
    call_sid = form.get("ExotelCallSid", form.get("CallSid", ""))
    status = form.get("Status", "unknown")
    duration = form.get("Duration", "0")
    logger.info(
        "[exotel] status agent=%s call=%s status=%s duration=%ss",
        agent_id, call_sid, status, duration,
    )
    return Response(content="OK", media_type="text/plain")


# ── WebSocket audio stream ────────────────────────────────────────────────────

@router.websocket("/stream/{agent_id}")
async def exotel_stream(websocket: WebSocket, agent_id: str):
    """
    Exotel real-time audio stream handler.

    Exotel sends PCM 8kHz 16-bit audio (same pipeline as Twilio Media Streams
    but without μ-law encoding — raw PCM samples).

    Message format (JSON):
      { "event": "media", "media": { "payload": "<base64-pcm>" } }
      { "event": "start",  "start": { "callSid": "...", "streamSid": "..." } }
      { "event": "stop" }
    """
    await websocket.accept()

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            await websocket.close(code=1008)
            return
        tenant_id = agent.tenantId
        voice_id = "af_sky"
        tts_engine = "kokoro"
        if agent.configuration:
            voice_id = agent.configuration.voiceId or voice_id

        prefs = agent.llmPreferences or {}
        turn_sensitivity = prefs.get("turnDetectionSensitivity", "medium")
        base_silence_frames = _SENSITIVITY_FRAMES.get(turn_sensitivity, _DEFAULT_SIL_FRAMES)
        te = prefs.get("ttsEngine")
        if isinstance(te, str) and te.strip():
            tts_engine = te.strip()

    call_started = datetime.now(timezone.utc)
    call_sid = ""
    stream_sid = ""
    pcm_buffer = bytearray()
    silence_frames = 0
    agent_speaking = asyncio.Event()
    full_transcript: list[dict] = []
    pending_tasks: set[asyncio.Task] = set()
    vad_context: dict[str, str] = {"last_user": ""}

    def _track(coro):
        t = asyncio.create_task(coro)
        pending_tasks.add(t)
        t.add_done_callback(pending_tasks.discard)

    try:
        async for raw in _ws_iter(websocket):
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            event = msg.get("event", "")

            if event == "connected":
                logger.info("[exotel] connected agent=%s", agent_id)

            elif event == "start":
                start_data = msg.get("start", {})
                stream_sid = start_data.get("streamSid", "")
                call_sid = start_data.get("callSid", start_data.get("customParameters", {}).get("callSid", ""))
                logger.info("[exotel] start agent=%s call=%s", agent_id, call_sid)

            elif event == "media":
                payload_b64 = msg.get("media", {}).get("payload", "")
                if not payload_b64:
                    continue

                pcm_8k = base64.b64decode(payload_b64)
                pcm_16k = _pcm8k_to_16k(pcm_8k)
                rms = _pcm_rms(pcm_8k)

                if agent_speaking.is_set() and rms > _INTERRUPT_RMS_THRESHOLD:
                    agent_speaking.clear()
                    pcm_buffer.clear()
                    silence_frames = 0
                    clear_turn_merge(call_sid)
                    continue

                pcm_buffer.extend(pcm_16k)

                vad_tail_ms = get_min_silence_ms(vad_context["last_user"])
                vad_frames = max(12, vad_tail_ms // 20)
                effective_silence_frames = max(base_silence_frames, vad_frames)

                if rms < _SILENCE_RMS_8K:
                    silence_frames += 1
                else:
                    silence_frames = 0

                if silence_frames >= effective_silence_frames and len(pcm_buffer) > 0:
                    utterance = bytes(pcm_buffer)
                    pcm_buffer.clear()
                    silence_frames = 0
                    _track(_handle_utterance(
                        websocket=websocket,
                        utterance=utterance,
                        agent_id=agent_id,
                        tenant_id=tenant_id,
                        call_sid=call_sid,
                        voice_id=voice_id,
                        tts_engine=tts_engine,
                        groq_key=groq_key,
                        full_transcript=full_transcript,
                        agent_speaking=agent_speaking,
                        vad_context=vad_context,
                    ))

            elif event == "stop":
                break

    except WebSocketDisconnect:
        logger.info("[exotel] WebSocket disconnected agent=%s", agent_id)
    except Exception:
        logger.exception("[exotel] error agent=%s", agent_id)
    finally:
        for task in list(pending_tasks):
            task.cancel()
        if pending_tasks:
            await asyncio.gather(*pending_tasks, return_exceptions=True)
        clear_turn_merge(call_sid)
        await _save_call_log(
            tenant_id=tenant_id,
            agent_id=agent_id,
            call_sid=call_sid,
            started_at=call_started,
            transcript=full_transcript,
        )


async def _ws_iter(websocket: WebSocket):
    while True:
        try:
            yield await websocket.receive_text()
        except WebSocketDisconnect:
            return


async def _handle_utterance(
    *,
    websocket: WebSocket,
    utterance: bytes,
    agent_id: str,
    tenant_id: str,
    call_sid: str,
    voice_id: str,
    tts_engine: str,
    groq_key: str | None,
    full_transcript: list[dict],
    agent_speaking: asyncio.Event,
    vad_context: dict[str, str],
) -> None:
    """STT → merge incomplete turns → RAG → TTS."""
    transcript = await stt_service.transcribe_bytes(
        utterance,
        sample_rate=16000,
        engine="faster-whisper",
        groq_api_key=groq_key,
        call_sid=call_sid or None,
    )
    if not transcript:
        return

    mk = call_sid or f"exo-{agent_id}"

    async def _flush(merged: str) -> None:
        vad_context["last_user"] = merged[:280]
        await _exotel_run_agent_turn(
            websocket=websocket,
            transcript=merged,
            agent_id=agent_id,
            tenant_id=tenant_id,
            call_sid=call_sid,
            voice_id=voice_id,
            tts_engine=tts_engine,
            full_transcript=full_transcript,
            agent_speaking=agent_speaking,
        )

    await integrate_user_text(mk, transcript, on_complete=_flush)


async def _exotel_run_agent_turn(
    *,
    websocket: WebSocket,
    transcript: str,
    agent_id: str,
    tenant_id: str,
    call_sid: str,
    voice_id: str,
    tts_engine: str,
    full_transcript: list[dict],
    agent_speaking: asyncio.Event,
) -> None:
    """Append caller turn and stream assistant audio to Exotel."""
    full_transcript.append({"role": "user", "content": transcript})

    from app.services.human_escalation_service import voice_escalation_ctx
    from app.services.rag_service import process_query_streaming

    session_id = f"exotel-{call_sid or uuid.uuid4().hex[:8]}"
    response_parts: list[str] = []

    voice_ctx = {
        "call_sid": call_sid or "",
        "caller_phone": "",
        "provider": "exotel",
        "tenant_id": tenant_id,
        "agent_id": agent_id,
    }
    _ev_ctx_tok = voice_escalation_ctx.set(voice_ctx)

    async def _tokens():
        async with AsyncSessionLocal() as db:
            async for token in process_query_streaming(
                db,
                tenant_id,
                agent_id,
                transcript,
                session_id,
                voice_escalation_context=voice_ctx,
            ):
                if isinstance(token, str):
                    response_parts.append(token)
                    yield token

    agent_speaking.set()
    try:
        async for wav_chunk in _tts.synthesize_streaming(
            text_stream=_tokens(), engine=tts_engine, voice_id=voice_id,
        ):
            pcm_8k = _wav16k_to_pcm8k(wav_chunk)
            for i in range(0, len(pcm_8k), _FRAME_BYTES):
                if not agent_speaking.is_set():
                    break
                frame = pcm_8k[i: i + _FRAME_BYTES]
                payload_b64 = base64.b64encode(frame).decode()
                await websocket.send_text(json.dumps({
                    "event": "media",
                    "media": {"payload": payload_b64},
                }))
                await asyncio.sleep(0.02)
            if not agent_speaking.is_set():
                break
    except Exception:
        logger.exception("[exotel] TTS pipeline failed call=%s", call_sid)
    finally:
        agent_speaking.clear()
        voice_escalation_ctx.reset(_ev_ctx_tok)

    full_response = "".join(response_parts)
    if full_response:
        full_transcript.append({"role": "assistant", "content": full_response})


async def _save_call_log(
    *, tenant_id: str, agent_id: str, call_sid: str,
    started_at: datetime, transcript: list[dict],
) -> None:
    import json as _json
    ended_at = datetime.now(timezone.utc)
    duration = int((ended_at - started_at).total_seconds())
    try:
        async with AsyncSessionLocal() as db:
            log = CallLog(
                tenantId=tenant_id,
                agentId=agent_id,
                callSid=call_sid or None,
                callDirection="inbound",
                startedAt=started_at,
                endedAt=ended_at,
                durationSeconds=duration,
                transcript=_json.dumps(transcript),
            )
            db.add(log)
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if agent:
                agent.totalCalls = (agent.totalCalls or 0) + 1
            await db.commit()
    except Exception:
        logger.exception("[exotel] failed to save call log call=%s", call_sid)


# ── Outbound call via Exotel REST API ─────────────────────────────────────────

async def initiate_exotel_call(
    *,
    to_number: str,
    from_number: str,
    agent_id: str,
    tenant_id: str,
    base_url: str,
) -> str | None:
    """
    Place an outbound call via Exotel API.

    Exotel Calls API: POST https://api.exotel.com/v1/Accounts/{sid}/Calls/connect.json
    Returns the ExotelCallSid or None on failure.
    """
    import httpx
    sid, api_key, api_token = await _exotel_creds(tenant_id)
    if not sid or not api_key or not api_token:
        logger.warning("[exotel] credentials not configured for tenant=%s", tenant_id)
        return None

    callback_url = f"{base_url}/api/voice/exotel/inbound/{agent_id}"
    status_callback_url = f"{base_url}/api/voice/exotel/status/{agent_id}"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"https://api.exotel.com/v1/Accounts/{sid}/Calls/connect.json",
                auth=(api_key, api_token),
                data={
                    "From": from_number,
                    "To": to_number,
                    "CallerId": from_number,
                    "Url": callback_url,
                    "StatusCallback": status_callback_url,
                    "StatusCallbackEvents[]": "terminal",
                },
            )
        if resp.status_code in (200, 201):
            data = resp.json()
            call_data = data.get("Call", data)
            call_sid = call_data.get("Sid", call_data.get("ExotelCallSid", ""))
            logger.info("[exotel] outbound call initiated to=%s sid=%s", to_number, call_sid)
            return call_sid
        logger.warning("[exotel] outbound call failed: %s %s", resp.status_code, resp.text[:200])
    except Exception:
        logger.exception("[exotel] outbound call API error")
    return None
