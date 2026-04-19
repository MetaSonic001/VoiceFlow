"""
WhatsApp inbound handler — Twilio WhatsApp webhooks.

POST /api/whatsapp/inbound/{agent_id}
  • Text messages  → RAG → reply via Twilio Messaging API
  • Voice notes    → download media → STT → RAG → reply as text

Conversation history is stored in Redis under key:
  whatsapp:{tenant_id}:{agent_id}:{session_id}  (TTL 24h)
"""
from __future__ import annotations

import base64
import io
import json
import logging
from datetime import datetime, timezone

import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter, Request
from fastapi.responses import Response
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Agent, Tenant
from app.services.credentials import decrypt_safe

logger = logging.getLogger("voiceflow.whatsapp")
router = APIRouter()

_CONV_TTL = 86400  # 24 hours


# ── Redis helper ──────────────────────────────────────────────────────────────

def _redis() -> aioredis.Redis:
    return aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=4,
        decode_responses=True,
    )


# ── Conversation history helpers ──────────────────────────────────────────────

async def _load_history(tenant_id: str, agent_id: str, session_id: str) -> list[dict]:
    r = _redis()
    try:
        raw = await r.get(f"whatsapp:{tenant_id}:{agent_id}:{session_id}")
        if raw:
            return json.loads(raw)
    except Exception:
        logger.warning("[whatsapp] failed to load conversation history")
    finally:
        await r.aclose()
    return []


async def _save_history(
    tenant_id: str,
    agent_id: str,
    session_id: str,
    history: list[dict],
) -> None:
    r = _redis()
    try:
        await r.setex(
            f"whatsapp:{tenant_id}:{agent_id}:{session_id}",
            _CONV_TTL,
            json.dumps(history),
        )
    except Exception:
        logger.warning("[whatsapp] failed to save conversation history")
    finally:
        await r.aclose()


# ── Twilio Messaging API helper ───────────────────────────────────────────────

async def _send_whatsapp_reply(
    to: str,
    from_number: str,
    body: str,
    twilio_sid: str,
    twilio_token: str,
) -> None:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json",
                auth=(twilio_sid, twilio_token),
                data={
                    "To": to,
                    "From": from_number,
                    "Body": body,
                },
            )
        if resp.status_code not in (200, 201):
            logger.warning("[whatsapp] reply failed status=%s", resp.status_code)
    except Exception:
        logger.exception("[whatsapp] error sending reply to %s", to)


async def _resolve_twilio_creds(tenant_id: str) -> tuple[str | None, str | None]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()

    if tenant and tenant.settings:
        sid = tenant.settings.get("twilioAccountSid")
        token_enc = tenant.settings.get("twilioAuthToken")
        if sid and token_enc:
            return sid, decrypt_safe(token_enc)
    return settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN


# ── Inbound webhook ───────────────────────────────────────────────────────────

@router.post("/inbound/{agent_id}")
async def handle_whatsapp(agent_id: str, request: Request):
    """
    Twilio WhatsApp inbound webhook.

    Handles:
      - Text messages: run through RAG, reply as text
      - Voice notes (audio/ogg, audio/mpeg, etc.): download → STT → RAG → text reply
    """
    form = await request.form()
    from_number: str = form.get("From", "")
    to_number: str = form.get("To", "")
    body_text: str = form.get("Body", "").strip()
    num_media: int = int(form.get("NumMedia", "0"))
    media_url: str = form.get("MediaUrl0", "")
    media_type: str = form.get("MediaContentType0", "").lower()
    message_sid: str = form.get("MessageSid", "")

    # Load agent
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()

    if not agent:
        logger.warning("[whatsapp] agent not found: %s", agent_id)
        return Response(status_code=204)

    tenant_id = agent.tenantId
    # Use sender phone as session identifier
    session_id = from_number.replace("whatsapp:", "").replace("+", "").replace("-", "")

    # Resolve Twilio credentials for sending replies
    twilio_sid, twilio_token = await _resolve_twilio_creds(tenant_id)

    user_query: str = ""

    if body_text:
        # ── Text message ──────────────────────────────────────────────────────
        user_query = body_text

    elif num_media > 0 and media_url and _is_audio_media(media_type):
        # ── Voice note ────────────────────────────────────────────────────────
        user_query = await _transcribe_voice_note(
            media_url=media_url,
            media_type=media_type,
            agent=agent,
            twilio_sid=twilio_sid,
            twilio_token=twilio_token,
        )
        if not user_query:
            logger.info("[whatsapp] empty transcription for voice note from %s", from_number)
            return Response(status_code=204)
    else:
        # Unsupported media type
        logger.info("[whatsapp] unsupported message type from %s media_type=%s", from_number, media_type)
        return Response(status_code=204)

    # ── RAG pipeline ──────────────────────────────────────────────────────────
    history = await _load_history(tenant_id, agent_id, session_id)

    from app.services.rag_service import process_query

    try:
        async with AsyncSessionLocal() as db:
            rag_result = await process_query(
                db, tenant_id, agent_id, user_query, f"whatsapp-{session_id}"
            )
        reply = rag_result.get("response", "I'm not sure how to help with that.")
    except Exception:
        logger.exception("[whatsapp] RAG failed agent=%s", agent_id)
        reply = "I encountered an error. Please try again."

    # ── Persist conversation ──────────────────────────────────────────────────
    history.append({"role": "user", "content": user_query})
    history.append({"role": "assistant", "content": reply})
    await _save_history(tenant_id, agent_id, session_id, history)

    # ── Send reply ────────────────────────────────────────────────────────────
    if twilio_sid and twilio_token:
        await _send_whatsapp_reply(
            to=from_number,
            from_number=to_number,
            body=reply,
            twilio_sid=twilio_sid,
            twilio_token=twilio_token,
        )
    else:
        logger.warning("[whatsapp] no Twilio creds — cannot send reply")

    return Response(status_code=204)


# ── Voice note helpers ────────────────────────────────────────────────────────

def _is_audio_media(content_type: str) -> bool:
    return content_type.startswith("audio/")


async def _transcribe_voice_note(
    *,
    media_url: str,
    media_type: str,
    agent,
    twilio_sid: str | None,
    twilio_token: str | None,
) -> str:
    """Download voice note from Twilio, convert to PCM 16kHz, and transcribe."""
    # SSRF protection: reconstruct the URL from validated components so that
    # no user-supplied string is ever passed directly to the HTTP client.
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(media_url)
    trusted_hosts = (
        "api.twilio.com",
        "media.twiliocdn.com",
        "mcs.us1.twilio.com",
    )
    if parsed.scheme != "https" or not any(
        parsed.netloc == h or parsed.netloc.endswith(f".{h}") for h in trusted_hosts
    ):
        logger.warning("[whatsapp] blocked untrusted media URL")
        return ""

    # Reconstruct URL from validated parts to break the taint chain
    safe_url = urlunparse((
        "https",
        parsed.netloc,
        parsed.path,
        "",
        parsed.query,
        "",
    ))

    # Download the media
    try:
        auth = (twilio_sid, twilio_token) if twilio_sid and twilio_token else None
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(safe_url, auth=auth)
        if resp.status_code != 200:
            logger.warning("[whatsapp] media download failed status=%s", resp.status_code)
            return ""
        audio_bytes = resp.content
    except Exception:
        logger.exception("[whatsapp] media download error")
        return ""

    # Convert to PCM 16kHz mono via pydub
    try:
        from pydub import AudioSegment

        fmt = _content_type_to_pydub_format(media_type)
        seg = AudioSegment.from_file(io.BytesIO(audio_bytes), format=fmt)
        pcm_seg = seg.set_channels(1).set_sample_width(2).set_frame_rate(16000)
        pcm_bytes = pcm_seg.raw_data
    except Exception:
        logger.exception("[whatsapp] audio conversion failed media_type=%s", media_type)
        return ""

    # Transcribe
    from app.services.stt_service import stt_service

    prefs: dict = agent.llmPreferences or {}
    stt_engine: str = prefs.get("sttEngine", "faster-whisper")

    try:
        transcript = await stt_service.transcribe_bytes(
            pcm_bytes,
            sample_rate=16000,
            engine=stt_engine,
        )
        return transcript.strip()
    except Exception:
        logger.exception("[whatsapp] transcription failed")
        return ""


def _content_type_to_pydub_format(content_type: str) -> str:
    """Map MIME type to pydub format string."""
    mapping = {
        "audio/ogg": "ogg",
        "audio/mpeg": "mp3",
        "audio/mp4": "mp4",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/amr": "amr",
        "audio/webm": "webm",
    }
    for prefix, fmt in mapping.items():
        if content_type.startswith(prefix):
            return fmt
    return "ogg"  # WhatsApp default
