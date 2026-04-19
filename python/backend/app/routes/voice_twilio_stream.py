"""
Twilio Media Streams voice pipeline.

POST /api/voice/inbound/{agent_id}  — Returns TwiML <Connect><Stream> to start media stream
POST /api/voice/status/{agent_id}   — Twilio status callback
WS   /api/voice/media-stream/{agent_id}  — Full-duplex audio: μ-law 8kHz ↔ PCM 16kHz
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import struct
from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydub import AudioSegment
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Agent, CallLog, Tenant
from app.services.credentials import decrypt_safe
from app.services.stt_service import stt_service
from app.services.tts_router import TTSRouter

logger = logging.getLogger("voiceflow.twilio_stream")
router = APIRouter()
_tts = TTSRouter()

# ── VAD / interruption constants ─────────────────────────────────────────────

_SILENCE_FRAMES_THRESHOLD = 24      # ~480 ms at 8kHz, 20ms frames
_INTERRUPT_RMS_THRESHOLD = 300.0    # energy threshold to detect user speaking over agent
_FRAME_BYTES = 160                  # 20ms of 8kHz μ-law = 160 bytes


# ── Redis helper ─────────────────────────────────────────────────────────────

def _redis_client() -> aioredis.Redis:
    return aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=2,
        decode_responses=False,
    )


# ── Audio conversion (pydub, never audioop) ──────────────────────────────────

def _mulaw_to_pcm16k(mulaw_bytes: bytes) -> bytes:
    """Convert Twilio's μ-law 8kHz mono bytes → PCM 16-bit 16kHz mono bytes."""
    seg = AudioSegment(
        data=mulaw_bytes,
        sample_width=1,
        frame_rate=8000,
        channels=1,
    ).set_sample_width(2).set_frame_rate(16000)
    return seg.raw_data


def _pcm_rms(pcm_bytes: bytes) -> float:
    n = len(pcm_bytes) // 2
    if n == 0:
        return 0.0
    samples = struct.unpack(f"<{n}h", pcm_bytes)
    return (sum(s * s for s in samples) / n) ** 0.5


# ── Tenant Groq key helper ────────────────────────────────────────────────────

async def _groq_key_for_tenant(tenant_id: str) -> str | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if tenant and tenant.settings:
            enc = tenant.settings.get("groqApiKey")
            if enc:
                val = decrypt_safe(enc)
                if val.startswith("gsk_"):
                    return val
    return settings.GROQ_API_KEY


# ── TwiML inbound endpoint ────────────────────────────────────────────────────

async def handle_inbound_call(agent: Agent, request: Request) -> Response:
    """Return TwiML <Connect><Stream> for the given agent."""
    from twilio.twiml.voice_response import VoiceResponse, Connect, Stream

    proto = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("host", "localhost")
    ws_url = f"wss://{host}/api/voice/media-stream/{agent.id}"

    resp = VoiceResponse()
    connect = Connect()
    stream = Stream(url=ws_url)
    stream.parameter(name="agentId", value=agent.id)
    connect.append(stream)
    resp.append(connect)

    return Response(content=str(resp), media_type="application/xml")


@router.post("/inbound/{agent_id}")
async def voice_inbound(agent_id: str, request: Request):
    """Twilio inbound webhook — returns Media Stream TwiML."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()

    if not agent:
        from twilio.twiml.voice_response import VoiceResponse

        resp = VoiceResponse()
        resp.say("Agent not found.")
        resp.hangup()
        return Response(content=str(resp), media_type="application/xml")

    return await handle_inbound_call(agent, request)


@router.post("/status/{agent_id}")
async def voice_status(agent_id: str, request: Request):
    """Twilio status callback — log call status."""
    form = await request.form()
    call_sid = form.get("CallSid", "")
    call_status = form.get("CallStatus", "unknown")
    duration = form.get("CallDuration", "0")
    logger.info(
        "[twilio_stream] status agent=%s call=%s status=%s duration=%ss",
        agent_id,
        call_sid,
        call_status,
        duration,
    )
    return Response(content="OK", media_type="text/plain")


# ── WebSocket media stream ────────────────────────────────────────────────────

@router.websocket("/media-stream/{agent_id}")
async def media_stream_ws(websocket: WebSocket, agent_id: str):
    """
    Twilio Media Stream WebSocket handler.

    Handles events: connected | start | media | stop
    VAD: energy-based, 24 silence-frames threshold.
    Interruption: if caller RMS > threshold while agent is speaking, clear the queue.
    """
    await websocket.accept()

    # Resolve agent & tenant
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

    groq_key = await _groq_key_for_tenant(tenant_id)

    redis = _redis_client()
    call_started = datetime.now(timezone.utc)
    stream_sid: str = ""
    call_sid: str = ""
    caller_phone: str = ""

    # Session-level buffers and state
    pcm_buffer = bytearray()
    silence_frames = 0
    # asyncio.Event: set while agent audio is being streamed to Twilio
    agent_speaking_event = asyncio.Event()
    full_transcript: list[dict] = []

    # Track background tasks so we can log/cancel on shutdown
    pending_tasks: set[asyncio.Task] = set()

    def _track_task(coro) -> None:
        task = asyncio.create_task(coro)
        pending_tasks.add(task)
        task.add_done_callback(pending_tasks.discard)

    try:
        async for raw in _ws_iter(websocket):
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            event = msg.get("event", "")

            if event == "connected":
                logger.info("[twilio_stream] connected agent=%s", agent_id)

            elif event == "start":
                start_data = msg.get("start", {})
                stream_sid = start_data.get("streamSid", "")
                call_sid = start_data.get("callSid", "")
                # Twilio puts call metadata at top-level of start, customParameters holds app-defined extras
                caller_phone = (
                    start_data.get("from", "")
                    or start_data.get("customParameters", {}).get("From", "")
                )
                logger.info(
                    "[twilio_stream] start agent=%s stream=%s call=%s",
                    agent_id, stream_sid, call_sid,
                )
                # Store session in Redis (expire in 1 hour)
                session_data = json.dumps({
                    "agentId": agent_id,
                    "tenantId": tenant_id,
                    "streamSid": stream_sid,
                    "callSid": call_sid,
                }).encode()
                await redis.setex(f"stream:{stream_sid}", 3600, session_data)

            elif event == "media":
                payload_b64 = msg.get("media", {}).get("payload", "")
                if not payload_b64:
                    continue

                mulaw_chunk = base64.b64decode(payload_b64)
                pcm_chunk = _mulaw_to_pcm16k(mulaw_chunk)
                rms = _pcm_rms(pcm_chunk)

                # Interruption detection while agent is speaking
                if agent_speaking_event.is_set() and rms > _INTERRUPT_RMS_THRESHOLD:
                    logger.debug("[twilio_stream] interruption detected rms=%.1f", rms)
                    agent_speaking_event.clear()
                    if stream_sid:
                        await _send_clear(websocket, stream_sid)
                    pcm_buffer.clear()
                    silence_frames = 0
                    continue

                pcm_buffer.extend(pcm_chunk)

                if rms < 50.0:
                    silence_frames += 1
                else:
                    silence_frames = 0

                if silence_frames >= _SILENCE_FRAMES_THRESHOLD and len(pcm_buffer) > 0:
                    utterance = bytes(pcm_buffer)
                    pcm_buffer.clear()
                    silence_frames = 0

                    # Background pipeline: STT → RAG → TTS → send
                    _track_task(
                        _handle_utterance(
                            websocket=websocket,
                            utterance=utterance,
                            agent_id=agent_id,
                            tenant_id=tenant_id,
                            stream_sid=stream_sid,
                            call_sid=call_sid,
                            voice_id=voice_id,
                            tts_engine=tts_engine,
                            groq_key=groq_key,
                            full_transcript=full_transcript,
                            agent_speaking_event=agent_speaking_event,
                        )
                    )

            elif event == "stop":
                logger.info("[twilio_stream] stop agent=%s stream=%s", agent_id, stream_sid)
                break

    except WebSocketDisconnect:
        logger.info("[twilio_stream] WebSocket disconnected agent=%s", agent_id)
    except Exception:
        logger.exception("[twilio_stream] error agent=%s", agent_id)
    finally:
        # Cancel any pending utterance tasks
        for task in list(pending_tasks):
            task.cancel()
        if pending_tasks:
            await asyncio.gather(*pending_tasks, return_exceptions=True)

        # Persist call log
        await _save_call_log(
            tenant_id=tenant_id,
            agent_id=agent_id,
            call_sid=call_sid,
            caller_phone=caller_phone,
            started_at=call_started,
            transcript=full_transcript,
        )
        if stream_sid:
            await redis.delete(f"stream:{stream_sid}")
        await redis.aclose()


async def _ws_iter(websocket: WebSocket):
    """Yield raw text frames from the WebSocket until disconnect."""
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
    stream_sid: str,
    call_sid: str,
    voice_id: str,
    tts_engine: str,
    groq_key: str | None,
    full_transcript: list[dict],
    agent_speaking_event: asyncio.Event,
) -> None:
    """STT → RAG → TTS → Twilio for a single utterance."""
    # 1. STT
    transcript = await stt_service.transcribe_bytes(
        utterance,
        sample_rate=16000,
        engine="faster-whisper",
        groq_api_key=groq_key,
    )
    if not transcript:
        return

    full_transcript.append({"role": "user", "content": transcript})
    logger.info("[twilio_stream] transcript call=%s: %s", call_sid, transcript)

    # 2. RAG
    from app.services.rag_service import process_query

    session_id = f"twilio-{call_sid}"
    try:
        async with AsyncSessionLocal() as db:
            rag_result = await process_query(db, tenant_id, agent_id, transcript, session_id)
        response_text = rag_result.get("response", "I'm not sure how to help with that.")
    except Exception:
        logger.exception("[twilio_stream] RAG failed call=%s", call_sid)
        response_text = "I encountered an error. Please try again."

    full_transcript.append({"role": "assistant", "content": response_text})

    # 3. TTS → μ-law
    try:
        mulaw_bytes = await _tts.synthesize_mulaw(
            text=response_text,
            engine=tts_engine,
            voice_id=voice_id,
        )
    except Exception:
        logger.exception("[twilio_stream] TTS failed call=%s", call_sid)
        return

    # 4. Stream μ-law back in 20ms chunks
    agent_speaking_event.set()
    try:
        await _stream_mulaw_to_twilio(websocket, stream_sid, mulaw_bytes, agent_speaking_event)
    finally:
        agent_speaking_event.clear()


async def _stream_mulaw_to_twilio(
    websocket: WebSocket,
    stream_sid: str,
    mulaw_bytes: bytes,
    agent_speaking_event: asyncio.Event,
) -> None:
    """Send μ-law audio to Twilio in 160-byte chunks (20ms at 8kHz)."""
    for i in range(0, len(mulaw_bytes), _FRAME_BYTES):
        # Stop if interrupted
        if not agent_speaking_event.is_set():
            break
        chunk = mulaw_bytes[i : i + _FRAME_BYTES]
        payload_b64 = base64.b64encode(chunk).decode()
        await websocket.send_text(json.dumps({
            "event": "media",
            "streamSid": stream_sid,
            "media": {"payload": payload_b64},
        }))
        await asyncio.sleep(0.02)  # maintain 20ms pacing


async def _send_clear(websocket: WebSocket, stream_sid: str) -> None:
    """Send Twilio clear event to flush audio buffer."""
    try:
        await websocket.send_text(json.dumps({
            "event": "clear",
            "streamSid": stream_sid,
        }))
    except Exception:
        pass


async def _save_call_log(
    *,
    tenant_id: str,
    agent_id: str,
    call_sid: str,
    caller_phone: str,
    started_at: datetime,
    transcript: list[dict],
) -> None:
    """Persist call log and increment agent.totalCalls."""
    ended_at = datetime.now(timezone.utc)
    duration = int((ended_at - started_at).total_seconds())
    try:
        async with AsyncSessionLocal() as db:
            log = CallLog(
                tenantId=tenant_id,
                agentId=agent_id,
                callerPhone=caller_phone or None,
                startedAt=started_at,
                endedAt=ended_at,
                durationSeconds=duration,
                transcript=json.dumps(transcript),
            )
            db.add(log)

            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if agent:
                agent.totalCalls = (agent.totalCalls or 0) + 1

            await db.commit()
        logger.info("[twilio_stream] call log saved call=%s duration=%ds", call_sid, duration)
    except Exception:
        logger.exception("[twilio_stream] failed to save call log call=%s", call_sid)
