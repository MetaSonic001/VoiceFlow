"""
/api/voice/live — Gemini Live-style WebSocket voice pipeline.

Browser sends continuous PCM 16-bit 16kHz mono audio as base64 frames.
Server performs VAD → STT → streaming RAG → streaming TTS → audio chunks back.

Supports barge-in: if user speaks while agent is responding, agent stops.

Protocol (client → server):
  {"type": "audio", "data": "<base64 PCM>"}   — continuous mic audio
  {"type": "config", "voiceId": "..."}         — change TTS voice
  {"type": "interrupt"}                        — explicit barge-in request
  {"type": "ping"}

Protocol (server → client):
  {"type": "state", "state": "listening|thinking|speaking"}
  {"type": "transcript", "text": "..."}        — user's speech (final STT)
  {"type": "partial_transcript", "text": "..."} — interim STT while listening (Vosk preview)
  {"type": "response", "text": "..."}          — full agent response (for display)
  {"type": "audio", "data": "<base64 WAV>"}    — audio chunk to play
  {"type": "audio_end"}                        — all audio for this turn sent
  {"type": "pong"}
  {"type": "error", "message": "..."}
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import struct
import time
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Agent, CallLog, Tenant
from app.services.credentials import decrypt_safe
from app.services.semantic_vad import get_min_silence_ms
from app.services.stt_service import stt_service
from app.services.tts_router import TTSRouter
from app.services.voice_turn_merge import clear_turn_merge, integrate_user_text

logger = logging.getLogger("voiceflow.voice_live")
router = APIRouter()
_tts = TTSRouter()

# ── VAD Constants ─────────────────────────────────────────────────────────────
_SILENCE_RMS_THRESHOLD = 50.0       # Below this = silence
_INTERRUPT_RMS_THRESHOLD = 220.0    # browser mic — responsive barge-in
_SENSITIVITY_FRAMES = {"high": 12, "medium": 24, "low": 40}
_DEFAULT_SIL_FRAMES = 24             # ~480ms end-of-utterance at 20ms/frame
_FRAME_SAMPLES = 320                # 20ms at 16kHz = 320 samples = 640 bytes


def _pcm_rms(pcm_bytes: bytes) -> float:
    """Compute RMS energy of 16-bit PCM samples."""
    n = len(pcm_bytes) // 2
    if n == 0:
        return 0.0
    samples = struct.unpack(f"<{n}h", pcm_bytes)
    return (sum(s * s for s in samples) / n) ** 0.5


def _validate_ws_token(websocket: WebSocket) -> dict | None:
    """Validate JWT from query params. Returns claims or None."""
    import jwt
    token = websocket.query_params.get("token")
    if not token:
        return None
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        logger.warning("[voice_live] token expired")
        return None
    except Exception:
        return None


async def _get_groq_key(tenant_id: str) -> str | None:
    """Resolve Groq API key for tenant or fall back to env."""
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


@router.websocket("/live/{agent_id}")
async def voice_live_ws(websocket: WebSocket, agent_id: str):
    """
    Gemini Live-style full-duplex voice WebSocket.

    Client streams PCM audio continuously. Server detects speech, processes it
    through the RAG pipeline, and streams audio responses back with barge-in.
    """
    await websocket.accept()

    # Auth
    claims = _validate_ws_token(websocket)
    if not claims:
        await websocket.send_json({"type": "error", "message": "Unauthorized"})
        await websocket.close(code=1008)
        return

    # Resolve agent
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            await websocket.send_json({"type": "error", "message": "Agent not found"})
            await websocket.close()
            return
        tenant_id = agent.tenantId

    if claims.get("tenantId") != tenant_id:
        await websocket.send_json({"type": "error", "message": "Invalid tenant"})
        await websocket.close(code=1008)
        return

    groq_key = await _get_groq_key(tenant_id)
    session_id = f"live-{agent_id}-{int(datetime.now(timezone.utc).timestamp())}"
    call_started = datetime.now(timezone.utc)

    # State
    voice_id = "af_sky"
    tts_engine = "kokoro"
    if agent.configuration and agent.configuration.voiceId:
        voice_id = agent.configuration.voiceId
    prefs = agent.llmPreferences or {}
    tts_engine = prefs.get("ttsEngine", "kokoro")
    turn_sensitivity = prefs.get("turnDetectionSensitivity", "medium")
    base_silence_frames = _SENSITIVITY_FRAMES.get(turn_sensitivity, _DEFAULT_SIL_FRAMES)
    streaming_preview = bool(prefs.get("streamingSttPreview", True))
    vosk_rec = stt_service.create_vosk_recognizer() if streaming_preview else None
    last_partial_sent = ""
    _partial_send_at = 0.0
    _PARTIAL_SEND_INTERVAL = 0.1  # seconds — limit WS spam while keeping UI responsive

    pcm_buffer = bytearray()
    silence_frames = 0
    is_speaking = False  # True when agent audio is being sent
    interrupted = asyncio.Event()
    full_transcript: list[dict] = []
    vad_context: dict[str, str] = {"last_user": ""}

    # Background task for processing utterances
    processing_task: asyncio.Task | None = None

    async def _deliver_live_turn(merged: str) -> None:
        """Notify UI, run streaming RAG + TTS for one logical user turn."""
        nonlocal is_speaking
        vad_context["last_user"] = merged[:280]

        try:
            await websocket.send_json({"type": "transcript", "text": merged})
            full_transcript.append({"role": "user", "content": merged})

            await websocket.send_json({"type": "state", "state": "thinking"})

            from app.services.rag_service import process_query_streaming

            response_parts: list[str] = []

            async def _token_gen():
                async with AsyncSessionLocal() as db:
                    async for token in process_query_streaming(
                        db, tenant_id, agent_id, merged, session_id
                    ):
                        if isinstance(token, str):
                            response_parts.append(token)
                            yield token

            is_speaking = True
            interrupted.clear()
            await websocket.send_json({"type": "state", "state": "speaking"})

            async for audio_chunk in _tts.synthesize_streaming(
                text_stream=_token_gen(),
                engine=tts_engine,
                voice_id=voice_id,
            ):
                if interrupted.is_set():
                    break
                audio_b64 = base64.b64encode(audio_chunk).decode()
                await websocket.send_json({"type": "audio", "data": audio_b64})

            full_response = "".join(response_parts)
            if full_response:
                await websocket.send_json({"type": "response", "text": full_response})
                full_transcript.append({"role": "assistant", "content": full_response})

            await websocket.send_json({"type": "audio_end"})

        except Exception:
            logger.exception("[voice_live] pipeline error session=%s", session_id)
            try:
                await websocket.send_json({"type": "error", "message": "Processing error"})
            except Exception:
                pass
        finally:
            is_speaking = False
            try:
                await websocket.send_json({"type": "state", "state": "listening"})
            except Exception:
                pass

    async def _process_and_respond(utterance: bytes):
        """STT → merge incomplete phrases → deliver."""
        try:
            transcript = await stt_service.transcribe_bytes(
                utterance,
                sample_rate=16000,
                engine="faster-whisper",
                groq_api_key=groq_key,
                call_sid=session_id,
            )
            if not transcript:
                await websocket.send_json({"type": "state", "state": "listening"})
                return

            await integrate_user_text(session_id, transcript, on_complete=_deliver_live_turn)
        except Exception:
            logger.exception("[voice_live] pipeline error session=%s", session_id)
            try:
                await websocket.send_json({"type": "error", "message": "Processing error"})
            except Exception:
                pass

    try:
        await websocket.send_json({"type": "state", "state": "listening"})

        async for raw in _ws_iter(websocket):
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "audio":
                pcm_data = base64.b64decode(msg.get("data", ""))
                if not pcm_data:
                    continue

                rms = _pcm_rms(pcm_data)

                # Barge-in detection
                if is_speaking and rms > _INTERRUPT_RMS_THRESHOLD:
                    logger.debug("[voice_live] barge-in detected rms=%.1f", rms)
                    interrupted.set()
                    is_speaking = False
                    if processing_task and not processing_task.done():
                        processing_task.cancel()
                    pcm_buffer.clear()
                    silence_frames = 0
                    clear_turn_merge(session_id)
                    if vosk_rec:
                        await stt_service.finalize_vosk_recognizer(vosk_rec)
                        vosk_rec = (
                            stt_service.create_vosk_recognizer()
                            if streaming_preview
                            else None
                        )
                    last_partial_sent = ""
                    _partial_send_at = 0.0
                    await websocket.send_json({"type": "state", "state": "listening"})
                    continue

                # Skip buffering audio while agent is speaking
                if is_speaking:
                    continue

                # VAD: accumulate audio
                pcm_buffer.extend(pcm_data)

                if vosk_rec and pcm_data:
                    try:
                        partial = await stt_service.transcribe_stream_chunk(
                            pcm_data, sample_rate=16000, recognizer=vosk_rec
                        )
                        if partial:
                            p = partial.strip()
                            if p and p != last_partial_sent:
                                now = time.monotonic()
                                significant_growth = len(p) >= len(last_partial_sent) + 6
                                if (
                                    now - _partial_send_at >= _PARTIAL_SEND_INTERVAL
                                    or significant_growth
                                ):
                                    last_partial_sent = p
                                    _partial_send_at = now
                                    await websocket.send_json(
                                        {"type": "partial_transcript", "text": p}
                                    )
                    except Exception:
                        logger.debug("[voice_live] vosk partial failed", exc_info=True)

                vad_tail_ms = get_min_silence_ms(vad_context["last_user"])
                vad_frames = max(12, vad_tail_ms // 20)
                effective_silence_frames = max(base_silence_frames, vad_frames)

                if rms < _SILENCE_RMS_THRESHOLD:
                    silence_frames += 1
                else:
                    silence_frames = 0

                # End-of-utterance: silence threshold reached with buffered audio
                if silence_frames >= effective_silence_frames and len(pcm_buffer) > 640:
                    if vosk_rec:
                        await stt_service.finalize_vosk_recognizer(vosk_rec)
                        vosk_rec = (
                            stt_service.create_vosk_recognizer()
                            if streaming_preview
                            else None
                        )
                    last_partial_sent = ""
                    _partial_send_at = 0.0

                    utterance = bytes(pcm_buffer)
                    pcm_buffer.clear()
                    silence_frames = 0

                    # Cancel any pending processing
                    if processing_task and not processing_task.done():
                        processing_task.cancel()

                    processing_task = asyncio.create_task(
                        _process_and_respond(utterance)
                    )

            elif msg_type == "config":
                new_voice = msg.get("voiceId", "")
                if new_voice:
                    # Determine engine from voice ID prefix
                    if new_voice.startswith("kokoro-") or new_voice.startswith("af_") or new_voice.startswith("am_"):
                        tts_engine = "kokoro"
                        voice_id = new_voice.replace("kokoro-", "")
                    elif new_voice.startswith("piper-"):
                        tts_engine = "piper"
                        voice_id = new_voice.replace("piper-", "")
                    else:
                        tts_engine = "kokoro"
                        voice_id = new_voice
                await websocket.send_json({"type": "config_ack", "voice": voice_id, "engine": tts_engine})

            elif msg_type == "interrupt":
                if is_speaking:
                    interrupted.set()
                    is_speaking = False
                    clear_turn_merge(session_id)
                    if vosk_rec:
                        await stt_service.finalize_vosk_recognizer(vosk_rec)
                        vosk_rec = (
                            stt_service.create_vosk_recognizer()
                            if streaming_preview
                            else None
                        )
                    last_partial_sent = ""
                    _partial_send_at = 0.0
                    await websocket.send_json({"type": "state", "state": "listening"})

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info("[voice_live] disconnected session=%s", session_id)
    except Exception:
        logger.exception("[voice_live] error session=%s", session_id)
    finally:
        if processing_task and not processing_task.done():
            processing_task.cancel()
        clear_turn_merge(session_id)

        # Persist call log with post-call analytics
        if full_transcript:
            await _save_live_call_log(
                tenant_id=tenant_id,
                agent_id=agent_id,
                started_at=call_started,
                transcript=full_transcript,
                session_id=session_id,
            )


async def _ws_iter(websocket: WebSocket):
    """Yield raw text frames from WebSocket."""
    while True:
        try:
            yield await websocket.receive_text()
        except WebSocketDisconnect:
            return


async def _save_live_call_log(
    *,
    tenant_id: str,
    agent_id: str,
    started_at: datetime,
    transcript: list[dict],
    session_id: str | None = None,
) -> None:
    """Persist call log and trigger post-call analytics."""
    ended_at = datetime.now(timezone.utc)
    duration = int((ended_at - started_at).total_seconds())
    try:
        async with AsyncSessionLocal() as db:
            analysis = {"conversation_session_id": session_id} if session_id else None
            log = CallLog(
                tenantId=tenant_id,
                agentId=agent_id,
                startedAt=started_at,
                endedAt=ended_at,
                durationSeconds=duration,
                transcript=json.dumps(transcript),
                analysis=analysis,
            )
            db.add(log)

            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if agent:
                agent.totalCalls = (agent.totalCalls or 0) + 1

            await db.commit()
            await db.refresh(log)
            log_id = log.id

        logger.info("[voice_live] call log saved duration=%ds", duration)

        # Trigger post-call analysis
        if log_id and tenant_id:
            from app.routes.voice_twilio_gather import analyze_call
            asyncio.create_task(analyze_call(log_id, tenant_id))

        # Fire usage billing (managed-plan tenants billed per minute)
        if log_id and tenant_id:
            from app.services.billing_service import log_call_usage
            asyncio.create_task(log_call_usage(tenant_id, log_id, duration, None))

    except Exception:
        logger.exception("[voice_live] failed to save call log")
