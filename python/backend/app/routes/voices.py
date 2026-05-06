"""
/api/voices routes — voice library catalog, previews, and clone management.

Endpoints
---------
GET  /catalog          — full voice library (filterable)
POST /preview          — generate & cache a 5-second voice preview
GET  /clones           — list tenant's cloned voices
POST /clones           — upload a reference audio to create a clone
GET  /clones/{id}/preview  — stream back the reference audio as preview
DELETE /clones/{id}    — delete a clone
"""
from __future__ import annotations

import base64
import hashlib
import io
import logging
import os
import time
import uuid
from pathlib import Path

import edge_tts
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.config import settings
from app.database import get_db
from app.models import ClonedVoice
from app.services.voice_catalog import (
    VOICE_CATEGORIES,
    filter_catalog,
    get_full_catalog,
    get_voice_by_id,
    unique_languages,
)

router = APIRouter()
logger = logging.getLogger("voiceflow.voices")

PREVIEW_TEXT = (
    "Hello! I'm your AI voice assistant, here to help make every conversation "
    "seamless and natural. How can I assist you today?"
)

# Local preview audio cache (disk-based, no MinIO needed)
_PREVIEW_CACHE_DIR = Path(os.getenv("VOICE_PREVIEW_CACHE_DIR", "/tmp/voiceflow_voice_previews"))
_PREVIEW_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Clone reference audio storage (local; MinIO used if configured)
_CLONE_DIR = Path(os.getenv("VOICE_CLONE_DIR", "/tmp/voiceflow_clones"))
_CLONE_DIR.mkdir(parents=True, exist_ok=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _preview_cache_path(voice_id: str, ext: str) -> Path:
    key = hashlib.md5(voice_id.encode()).hexdigest()
    return _PREVIEW_CACHE_DIR / f"{key}.{ext}"


async def _generate_edge_preview(neural_name: str) -> bytes:
    """Generate MP3 preview bytes via edge-tts."""
    communicate = edge_tts.Communicate(PREVIEW_TEXT, neural_name)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()


async def _store_clone_audio(tenant_id: str, clone_id: str, data: bytes, ext: str) -> str:
    """
    Save reference audio to MinIO (if configured) or local disk.
    Returns the retrieval key.
    """
    key = f"clones/{tenant_id}/{clone_id}/reference.{ext}"

    if settings.MINIO_ENDPOINT:
        try:
            from minio import Minio  # lazy import — minio is optional dependency
            client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY or "",
                secret_key=settings.MINIO_SECRET_KEY or "",
                secure=False,
            )
            bucket = "voiceflow-voices"
            try:
                client.make_bucket(bucket)
            except Exception:
                pass
            client.put_object(
                bucket, key, io.BytesIO(data), len(data),
                content_type=f"audio/{ext}",
            )
            return f"minio:{bucket}/{key}"
        except Exception as exc:
            logger.warning("[voice_clone] MinIO upload failed (%s), falling back to local disk", exc)

    # Local fallback
    local_path = _CLONE_DIR / tenant_id / clone_id
    local_path.mkdir(parents=True, exist_ok=True)
    (local_path / f"reference.{ext}").write_bytes(data)
    return f"local:{key}"


async def _load_clone_audio(storage_key: str) -> bytes | None:
    """Retrieve reference audio bytes from storage key."""
    if storage_key.startswith("minio:"):
        try:
            from minio import Minio
            _, path = storage_key.split(":", 1)
            bucket, obj_key = path.split("/", 1)
            client = Minio(
                settings.MINIO_ENDPOINT or "",
                access_key=settings.MINIO_ACCESS_KEY or "",
                secret_key=settings.MINIO_SECRET_KEY or "",
                secure=False,
            )
            resp = client.get_object(bucket, obj_key)
            return resp.read()
        except Exception as exc:
            logger.warning("[voice_clone] MinIO read failed: %s", exc)
            return None

    # local key: "local:clones/{tenant_id}/{clone_id}/reference.{ext}"
    _, path = storage_key.split(":", 1)
    # path = clones/{tenant_id}/{clone_id}/reference.{ext}
    parts = path.split("/")  # ['clones', tenant_id, clone_id, 'reference.ext']
    if len(parts) >= 4:
        tenant_id, clone_id = parts[1], parts[2]
        filename = parts[3]
        local_path = _CLONE_DIR / tenant_id / clone_id / filename
        if local_path.exists():
            return local_path.read_bytes()
    return None


def _validate_audio_upload(data: bytes, filename: str) -> tuple[str, str]:
    """
    Validate uploaded audio. Returns (ext, error_message).
    error_message is empty string if valid.
    """
    ext = (filename.rsplit(".", 1)[-1] or "bin").lower()
    allowed = {"mp3", "wav", "webm", "ogg", "m4a", "aac"}
    if ext not in allowed:
        return ext, f"Unsupported format '{ext}'. Allowed: {', '.join(sorted(allowed))}"
    if len(data) > 50 * 1024 * 1024:
        return ext, "File too large. Maximum size is 50 MB."
    if len(data) < 5000:
        return ext, "Audio file too short. Please upload at least 6 seconds of clear speech."
    return ext, ""


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/catalog")
async def voice_catalog(
    language: str | None = None,
    gender: str | None = None,
    provider: str | None = None,
    category: str | None = None,
    search: str | None = None,
):
    """
    Return the full voice catalog with optional filters.
    All 150+ library voices are pre-defined; no API calls are made here.
    """
    all_voices = get_full_catalog()
    filtered = filter_catalog(
        all_voices,
        language=language or None,
        gender=gender or None,
        provider=provider or None,
        category=category or None,
        search=search or None,
    )
    return {
        "voices": filtered,
        "total": len(filtered),
        "categories": VOICE_CATEGORIES,
        "languages": unique_languages(all_voices),
        "providers": [
            {"id": "edge",   "name": "Edge TTS (Free)", "count": sum(1 for v in all_voices if v["provider"] == "edge")},
            {"id": "sarvam", "name": "Sarvam AI (Indian)", "count": sum(1 for v in all_voices if v["provider"] == "sarvam"),
             "requires_key": "SARVAM_API_KEY", "configured": bool(getattr(settings, "SARVAM_API_KEY", None))},
            {"id": "kokoro", "name": "Kokoro (Local CPU)", "count": sum(1 for v in all_voices if v["provider"] == "kokoro")},
            {"id": "piper",  "name": "Piper (Local CPU)",  "count": sum(1 for v in all_voices if v["provider"] == "piper")},
        ],
        "sarvam_configured": bool(getattr(settings, "SARVAM_API_KEY", None)),
    }


@router.post("/preview")
async def voice_preview(body: dict):
    """
    Generate a short preview clip for a voice ID.
    Results are cached on disk — repeated requests are instant.
    """
    voice_id: str = body.get("voice_id", "edge-en-US-AriaNeural")
    text: str = body.get("text") or PREVIEW_TEXT

    # ── Cache check ───────────────────────────────────────────────────────────
    for ext in ("mp3", "wav"):
        cached = _preview_cache_path(voice_id, ext)
        if cached.exists():
            b64 = base64.b64encode(cached.read_bytes()).decode()
            return {"audioUrl": f"data:audio/{ext};base64,{b64}", "cached": True, "voiceId": voice_id}

    voice = get_voice_by_id(voice_id)
    if not voice:
        raise HTTPException(status_code=404, detail=f"Voice '{voice_id}' not found in catalog")

    provider = voice["provider"]

    try:
        # ── Edge TTS ──────────────────────────────────────────────────────────
        if provider == "edge":
            neural = voice["neural_name"]
            audio_bytes = await _generate_edge_preview(neural)
            if audio_bytes:
                _preview_cache_path(voice_id, "mp3").write_bytes(audio_bytes)
                b64 = base64.b64encode(audio_bytes).decode()
                return {"audioUrl": f"data:audio/mp3;base64,{b64}", "cached": False, "voiceId": voice_id}
            raise HTTPException(status_code=503, detail="Edge TTS preview generation failed")

        # ── Sarvam AI ─────────────────────────────────────────────────────────
        if provider == "sarvam":
            api_key = getattr(settings, "SARVAM_API_KEY", None)
            if not api_key:
                raise HTTPException(status_code=402, detail="Sarvam API key not configured. Add SARVAM_API_KEY to .env")
            from app.services.tts_router import TTSRouter
            tts = TTSRouter()
            audio_bytes = await tts._synthesize_sarvam(
                text=text,
                voice_id=voice["neural_name"],
                api_key=api_key,
                language_code=voice["language"],
            )
            if audio_bytes:
                _preview_cache_path(voice_id, "wav").write_bytes(audio_bytes)
                b64 = base64.b64encode(audio_bytes).decode()
                return {"audioUrl": f"data:audio/wav;base64,{b64}", "cached": False, "voiceId": voice_id}
            raise HTTPException(status_code=503, detail="Sarvam TTS preview failed")

        # ── Kokoro / Piper (local sidecars) ───────────────────────────────────
        if provider in ("kokoro", "piper"):
            from app.services.tts_router import TTSRouter
            tts = TTSRouter()
            engine = "orpheus" if voice_id.startswith("orpheus-") else provider
            try:
                audio_bytes = await tts.synthesize(
                    text=text,
                    engine=engine,
                    voice_id=voice["neural_name"],
                )
                if audio_bytes:
                    _preview_cache_path(voice_id, "wav").write_bytes(audio_bytes)
                    b64 = base64.b64encode(audio_bytes).decode()
                    return {"audioUrl": f"data:audio/wav;base64,{b64}", "cached": False, "voiceId": voice_id}
            except Exception as exc:
                raise HTTPException(status_code=503, detail=f"Local TTS preview failed: {exc}")

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[voice_preview] unexpected error for %s", voice_id)
        raise HTTPException(status_code=500, detail=str(exc))

    raise HTTPException(status_code=503, detail="Preview generation failed for this voice")


# ── Clone endpoints ───────────────────────────────────────────────────────────

@router.get("/clones")
async def list_clones(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ClonedVoice)
        .where(ClonedVoice.tenantId == auth.tenant_id)
        .order_by(ClonedVoice.createdAt.desc())
    )
    clones = result.scalars().all()
    return {
        "clones": [
            {
                "id":            c.id,
                "name":          c.name,
                "languageCode":  c.languageCode,
                "languageName":  c.languageName,
                "status":        c.status,
                "durationSecs":  c.durationSecs,
                "createdAt":     c.createdAt.isoformat() if c.createdAt else None,
                "voiceId":       f"clone-{c.id}",
            }
            for c in clones
        ]
    }


@router.post("/clones", status_code=201)
async def upload_clone(
    audio: UploadFile = File(...),
    name: str = Form(...),
    language: str = Form("en-IN"),
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a reference audio sample (MP3/WAV/WebM, 6-60 sec recommended).
    The reference audio is stored and serves as the clone preview.
    Full voice synthesis with XTTS-v2 becomes available when the TTS package
    is installed (optional — system gracefully falls back to language-matched
    Edge TTS voice when XTTS is unavailable).
    """
    data = await audio.read()
    ext, err = _validate_audio_upload(data, audio.filename or "clip.mp3")
    if err:
        raise HTTPException(status_code=422, detail=err)

    clone_id = str(uuid.uuid4())

    # Optionally estimate duration via pydub (non-fatal if it fails)
    duration_secs: float | None = None
    try:
        from pydub import AudioSegment
        seg = AudioSegment.from_file(io.BytesIO(data))
        duration_secs = len(seg) / 1000.0
        if duration_secs < 6:
            raise HTTPException(
                status_code=422,
                detail=f"Audio is too short ({duration_secs:.1f}s). Minimum 6 seconds required for good quality cloning.",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # pydub failure is non-fatal

    # Language display names (simple mapping)
    _LANG_NAMES = {
        "hi-IN": "Hindi (India)", "ta-IN": "Tamil (India)", "te-IN": "Telugu (India)",
        "bn-IN": "Bengali (India)", "mr-IN": "Marathi (India)", "kn-IN": "Kannada (India)",
        "gu-IN": "Gujarati (India)", "ml-IN": "Malayalam (India)", "pa-IN": "Punjabi (India)",
        "en-IN": "English (India)", "en-US": "English (US)", "en-GB": "English (UK)",
    }
    lang_name = _LANG_NAMES.get(language, language)

    # Store reference audio
    storage_key = await _store_clone_audio(auth.tenant_id, clone_id, data, ext)

    clone = ClonedVoice(
        id=clone_id,
        tenantId=auth.tenant_id,
        userId=auth.user_id or "",
        name=name.strip()[:80],
        languageCode=language,
        languageName=lang_name,
        referenceAudioKey=storage_key,
        durationSecs=duration_secs,
        status="ready",
    )
    db.add(clone)
    await db.commit()
    await db.refresh(clone)

    logger.info("[voice_clone] Created clone %s for tenant %s (%.1fs)", clone_id, auth.tenant_id, duration_secs or 0)

    return {
        "id":            clone.id,
        "name":          clone.name,
        "languageCode":  clone.languageCode,
        "languageName":  clone.languageName,
        "status":        clone.status,
        "durationSecs":  clone.durationSecs,
        "createdAt":     clone.createdAt.isoformat() if clone.createdAt else None,
        "voiceId":       f"clone-{clone.id}",
        "message":       "Voice clone created. Preview plays your recording. Full synthesis uses language-matched Edge TTS voice.",
    }


@router.get("/clones/{clone_id}/preview")
async def clone_preview_audio(
    clone_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Returns the raw reference audio so the browser can play it as voice preview."""
    result = await db.execute(
        select(ClonedVoice).where(
            ClonedVoice.id == clone_id,
            ClonedVoice.tenantId == auth.tenant_id,
        )
    )
    clone = result.scalar_one_or_none()
    if not clone:
        raise HTTPException(status_code=404, detail="Clone not found")

    audio_bytes = await _load_clone_audio(clone.referenceAudioKey)
    if not audio_bytes:
        raise HTTPException(status_code=404, detail="Reference audio not found in storage")

    ext = clone.referenceAudioKey.rsplit(".", 1)[-1] if "." in clone.referenceAudioKey else "mp3"
    mime = {"mp3": "audio/mpeg", "wav": "audio/wav", "webm": "audio/webm", "ogg": "audio/ogg"}.get(ext, "audio/mpeg")
    return Response(content=audio_bytes, media_type=mime)


@router.delete("/clones/{clone_id}")
async def delete_clone(
    clone_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ClonedVoice).where(
            ClonedVoice.id == clone_id,
            ClonedVoice.tenantId == auth.tenant_id,
        )
    )
    clone = result.scalar_one_or_none()
    if not clone:
        raise HTTPException(status_code=404, detail="Clone not found")

    # Best-effort cleanup of stored audio
    try:
        await _load_clone_audio(clone.referenceAudioKey)  # validates key exists
        if clone.referenceAudioKey.startswith("local:"):
            _, path = clone.referenceAudioKey.split(":", 1)
            parts = path.split("/")
            if len(parts) >= 3:
                local_dir = _CLONE_DIR / parts[1] / parts[2]
                import shutil
                if local_dir.exists():
                    shutil.rmtree(local_dir, ignore_errors=True)
    except Exception:
        pass

    await db.delete(clone)
    await db.commit()
    return {"success": True, "id": clone_id}
