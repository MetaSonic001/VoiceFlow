"""
/api/voice/ws — WebSocket voice pipeline.
Browser sends audio chunks over WebSocket -> STT -> RAG -> TTS audio back.
"""

import base64
import io
import json
import logging
import wave
from datetime import datetime, timezone

import jwt as pyjwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Agent, CallLog, Tenant
from app.config import settings
from app.services.credentials import decrypt_safe

logger = logging.getLogger("voiceflow.voice_ws")
router = APIRouter()

# Try to load faster-whisper for local STT; fall back to Groq Whisper API
_whisper_model = None
_whisper_available = False

try:
    from faster_whisper import WhisperModel

    _whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
    _whisper_available = True
    logger.info("faster-whisper loaded (local STT enabled)")
except ImportError:
    logger.info("faster-whisper not installed; will use Groq Whisper API for STT")
except Exception as e:
    logger.warning(f"faster-whisper init failed: {e}; will use Groq Whisper API")


async def _transcribe_local(audio_bytes: bytes) -> str:
    """Transcribe using local faster-whisper model."""
    if not _whisper_model:
        return ""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(audio_bytes)
    buf.seek(0)
    segments, _ = _whisper_model.transcribe(buf, language="en")
    return " ".join(seg.text for seg in segments).strip()


async def _transcribe_groq(audio_bytes: bytes, groq_key: str) -> str:
    """Transcribe using Groq's Whisper API endpoint."""
    import httpx

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(audio_bytes)
    buf.seek(0)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {groq_key}"},
            files={"file": ("audio.wav", buf, "audio/wav")},
            data={"model": "whisper-large-v3-turbo", "language": "en"},
        )
        if resp.status_code == 200:
            return resp.json().get("text", "")
        logger.warning(f"Groq Whisper API returned {resp.status_code}")
    return ""


def _validate_ws_token(websocket: WebSocket) -> dict | None:
    token = websocket.query_params.get("token")
    if not token:
        return None
    try:
        return pyjwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None


async def _get_groq_key(tenant_id: str) -> str | None:
    """Resolve Groq API key for a tenant."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if tenant and tenant.settings:
            enc_key = tenant.settings.get("groqApiKey")
            if enc_key:
                decrypted = decrypt_safe(enc_key)
                if decrypted.startswith("gsk_"):
                    return decrypted
    return settings.GROQ_API_KEY


def _engine_from_voice_id(voice_id: str) -> str:
    if voice_id.startswith("kokoro-"):
        return "kokoro"
    if voice_id.startswith("piper-"):
        return "piper"
    if voice_id.startswith("orpheus-"):
        return "orpheus"
    return "edge"


def _cpu_voice_id(voice_id: str, engine: str) -> str:
    if "-" in voice_id:
        return voice_id.split("-", 1)[1]
    if engine == "kokoro":
        return "af_sky"
    if engine == "piper":
        return "en_US-lessac-medium"
    return "af_sky"


@router.websocket("/ws/{agent_id}")
async def voice_websocket(websocket: WebSocket, agent_id: str):
    """WebSocket endpoint for browser-based voice interaction."""
    claims = _validate_ws_token(websocket)
    if not claims:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    # Validate agent
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            await websocket.send_json({"type": "error", "message": "Agent not found"})
            await websocket.close()
            return
        tenant_id = agent.tenantId

    # Enforce tenant match from JWT on every WS connection
    if claims.get("tenantId") != tenant_id:
        await websocket.send_json({"type": "error", "message": "Invalid tenant token"})
        await websocket.close(code=1008)
        return

    groq_key = await _get_groq_key(tenant_id)
    session_id = f"ws-{agent_id}-{int(datetime.now(timezone.utc).timestamp())}"
    audio_buffer = bytearray()

    selected_voice = "en-US-AriaNeural"
    selected_engine = "edge"

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "config":
                vid = msg.get("voiceId", "")
                if not vid:
                    await websocket.send_json({"type": "config_ack", "voice": selected_voice, "engine": selected_engine})
                    continue

                from app.routes.tts import resolve_edge_voice

                selected_engine = _engine_from_voice_id(vid)
                if selected_engine == "edge":
                    selected_voice = resolve_edge_voice(vid)
                else:
                    selected_voice = _cpu_voice_id(vid, selected_engine)

                await websocket.send_json({"type": "config_ack", "voice": selected_voice, "engine": selected_engine})

            elif msg_type == "audio":
                chunk = base64.b64decode(msg.get("data", ""))
                audio_buffer.extend(chunk)

            elif msg_type == "end":
                if not audio_buffer:
                    await websocket.send_json({"type": "error", "message": "No audio received"})
                    continue

                audio_bytes = bytes(audio_buffer)
                audio_buffer.clear()

                # 1. Speech-to-text
                if _whisper_available:
                    transcript = await _transcribe_local(audio_bytes)
                elif groq_key:
                    transcript = await _transcribe_groq(audio_bytes, groq_key)
                else:
                    await websocket.send_json({"type": "error", "message": "No STT engine available"})
                    continue

                if not transcript:
                    await websocket.send_json({"type": "transcript", "text": ""})
                    continue

                await websocket.send_json({"type": "transcript", "text": transcript})

                # 2. RAG pipeline
                from app.services.rag_service import process_query

                async with AsyncSessionLocal() as db:
                    try:
                        rag_result = await process_query(db, tenant_id, agent_id, transcript, session_id)
                        response_text = rag_result.get("response", "I'm not sure.")
                        sources = rag_result.get("sources", [])
                    except Exception:
                        logger.exception("RAG pipeline failed in WebSocket")
                        response_text = "I encountered an error."
                        sources = []

                await websocket.send_json({"type": "response", "text": response_text, "sources": sources})

                # 2b. TTS audio
                try:
                    if selected_engine == "edge":
                        from app.routes.tts import _synthesise_edge

                        result = await _synthesise_edge(response_text, selected_voice)
                    else:
                        from app.routes.tts import _synthesise_cpu_engine

                        result = await _synthesise_cpu_engine(response_text, selected_engine, selected_voice)

                    audio_data_uri = result.get("audioUrl") if isinstance(result, dict) else None
                    if audio_data_uri:
                        await websocket.send_json({"type": "audio", "data": audio_data_uri})
                    else:
                        raise RuntimeError("No audio generated")
                except Exception:
                    logger.warning("TTS failed in WebSocket, client will use browser speech")

                # 3. Persist call log
                async with AsyncSessionLocal() as db:
                    try:
                        now = datetime.now(timezone.utc)
                        log = CallLog(
                            tenantId=tenant_id,
                            agentId=agent_id,
                            startedAt=now,
                            endedAt=now,
                            durationSeconds=0,
                            transcript=json.dumps(
                                [
                                    {"role": "user", "content": transcript},
                                    {"role": "assistant", "content": response_text},
                                ]
                            ),
                        )
                        db.add(log)
                        await db.commit()
                    except Exception:
                        logger.exception("Failed to log WebSocket voice interaction")

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket voice session ended: {session_id}")
    except Exception:
        logger.exception(f"WebSocket voice error: {session_id}")
