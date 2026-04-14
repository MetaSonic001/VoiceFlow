"""
/api/voice/ws — Patent Claim 15: WebSocket voice pipeline.
Browser sends audio chunks over WebSocket -> STT (Whisper) -> RAG pipeline -> TTS (Edge TTS / Chatterbox) -> audio back.
Falls back to Groq Whisper API if local faster-whisper isn't available.
"""
import asyncio
import base64
import io
import json
import logging
import wave
from datetime import datetime, timezone

import edge_tts
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    # Convert raw PCM to WAV in-memory
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
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


@router.websocket("/ws/{agent_id}")
async def voice_websocket(websocket: WebSocket, agent_id: str):
    """
    WebSocket endpoint for browser-based voice interaction.

    Protocol:
    - Client sends JSON: {"type": "audio", "data": "<base64 PCM16 mono 16kHz>"}
    - Client sends JSON: {"type": "end"} to signal end of utterance
    - Server responds JSON: {"type": "transcript", "text": "..."}
    - Server responds JSON: {"type": "response", "text": "...", "sources": [...]}
    - Server responds JSON: {"type": "error", "message": "..."}
    """
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

    groq_key = await _get_groq_key(tenant_id)
    session_id = f"ws-{agent_id}-{int(datetime.now(timezone.utc).timestamp())}"
    audio_buffer = bytearray()
    # Voice config — client can send {"type":"config","voiceId":"preset-davis"}
    selected_voice = "en-US-AriaNeural"
    selected_engine = "edge"  # "edge" | "chatterbox" | "clone"

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "config":
                # Client sends voice preference
                vid = msg.get("voiceId", "")
                from app.routes.tts import resolve_edge_voice, is_chatterbox_voice, is_clone_voice
                if is_clone_voice(vid):
                    selected_voice = vid
                    selected_engine = "clone"
                elif is_chatterbox_voice(vid):
                    selected_voice = vid
                    selected_engine = "chatterbox"
                else:
                    selected_voice = resolve_edge_voice(vid)
                    selected_engine = "edge"
                await websocket.send_json({"type": "config_ack", "voice": selected_voice})

            elif msg_type == "audio":
                # Accumulate audio chunks
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
                        rag_result = await process_query(
                            db, tenant_id, agent_id, transcript, session_id
                        )
                        response_text = rag_result.get("response", "I'm not sure.")
                        sources = rag_result.get("sources", [])
                    except Exception:
                        logger.exception("RAG pipeline failed in WebSocket")
                        response_text = "I encountered an error."
                        sources = []

                await websocket.send_json({
                    "type": "response",
                    "text": response_text,
                    "sources": sources,
                })

                # 2b. Generate TTS audio and send over WebSocket
                try:
                    if selected_engine == "clone":
                        from app.routes.tts import _synthesise_clone
                        result = await _synthesise_clone(response_text, selected_voice)
                        audio_data_uri = result.get("audioUrl") if isinstance(result, dict) else None
                        if audio_data_uri:
                            await websocket.send_json({"type": "audio", "data": audio_data_uri})
                        else:
                            raise RuntimeError("Clone TTS returned no audio")
                    elif selected_engine == "chatterbox":
                        from app.routes.tts import _synthesise_chatterbox
                        result = await _synthesise_chatterbox(response_text, selected_voice)
                        audio_data_uri = result.get("audioUrl") if isinstance(result, dict) else None
                        if audio_data_uri:
                            await websocket.send_json({"type": "audio", "data": audio_data_uri})
                        else:
                            raise RuntimeError("Chatterbox returned no audio")
                    else:
                        try:
                            communicate = edge_tts.Communicate(response_text, selected_voice)
                            audio_buf = io.BytesIO()
                            async for chunk in communicate.stream():
                                if chunk["type"] == "audio":
                                    audio_buf.write(chunk["data"])
                            audio_b64 = base64.b64encode(audio_buf.getvalue()).decode()
                            await websocket.send_json({
                                "type": "audio",
                                "data": f"data:audio/mp3;base64,{audio_b64}",
                            })
                        except Exception:
                            from app.routes.tts import _synthesise_chatterbox
                            result = await _synthesise_chatterbox(response_text, "chatterbox-default")
                            audio_data_uri = result.get("audioUrl") if isinstance(result, dict) else None
                            if audio_data_uri:
                                await websocket.send_json({"type": "audio", "data": audio_data_uri})
                            else:
                                raise RuntimeError("Edge and Chatterbox fallback both failed")
                except Exception:
                    logger.warning("TTS failed in WebSocket, client will use browser speech")

                # 3. Persist as call log
                async with AsyncSessionLocal() as db:
                    try:
                        now = datetime.now(timezone.utc)
                        log = CallLog(
                            tenantId=tenant_id,
                            agentId=agent_id,
                            startedAt=now,
                            endedAt=now,
                            durationSeconds=0,
                            transcript=json.dumps([
                                {"role": "user", "content": transcript},
                                {"role": "assistant", "content": response_text},
                            ]),
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
