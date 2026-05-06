"""
Speaker Verification API — voice biometric voiceprint management.

Endpoints:
  GET    /api/speaker-verification/          ← list all voiceprints for the tenant
  POST   /api/speaker-verification/enroll    ← enroll a voiceprint from uploaded audio
  POST   /api/speaker-verification/verify    ← verify audio against stored voiceprints
  DELETE /api/speaker-verification/{vp_id}   ← delete a single voiceprint

The heavy lifting (embedding, cosine similarity) lives in
app/services/speaker_verification.py — this file is purely the HTTP layer.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db
from app.models import Contact, VoicePrint
from app.services.speaker_verification import speaker_verifier

logger = logging.getLogger("voiceflow.routes.speaker_verification")

router = APIRouter()


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/")
async def list_voiceprints(
    auth: AuthContext = Depends(get_auth),
):
    """Return all enrolled voiceprints for this tenant."""
    vps = await speaker_verifier.list_voiceprints(auth.tenant_id)
    return {"voiceprints": vps, "count": len(vps)}


# ── Enroll ────────────────────────────────────────────────────────────────────

@router.post("/enroll")
async def enroll_voiceprint(
    phone_number: str = Form(..., description="E.164 phone number to enroll"),
    contact_id: str = Form(None, description="Optional Contact.id to link"),
    label: str = Form(None, description="Friendly label (e.g. caller name)"),
    sample_rate: int = Form(16000, description="PCM sample rate (Hz)"),
    audio: UploadFile = File(..., description="Raw PCM 16-bit audio or WAV file"),
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Enroll a speaker voiceprint from an uploaded audio file.

    The audio file should be at least 3 seconds of clear speech.
    Accepts raw PCM 16-bit LE or WAV containers (the WAV header is stripped
    automatically if present).
    """
    # Validate contact_id belongs to this tenant
    if contact_id:
        result = await db.execute(
            select(Contact).where(
                Contact.id == contact_id,
                Contact.tenantId == auth.tenant_id,
            )
        )
        if not result.scalar_one_or_none():
            return JSONResponse({"error": "Contact not found."}, status_code=404)

    raw_bytes = await audio.read()

    # Strip WAV header if present (first 44 bytes for standard PCM WAV)
    pcm_bytes = raw_bytes
    if raw_bytes[:4] == b"RIFF":
        # Walk past RIFF/WAVE/fmt  chunk to find data chunk
        idx = 12
        while idx < len(raw_bytes) - 8:
            chunk_id = raw_bytes[idx:idx+4]
            chunk_size = int.from_bytes(raw_bytes[idx+4:idx+8], "little")
            if chunk_id == b"data":
                pcm_bytes = raw_bytes[idx+8: idx+8+chunk_size]
                break
            idx += 8 + chunk_size

    voiceprint_id = await speaker_verifier.enroll(
        phone_number=phone_number,
        pcm_bytes=pcm_bytes,
        tenant_id=auth.tenant_id,
        contact_id=contact_id,
        sample_rate=sample_rate,
    )

    if voiceprint_id is None:
        return JSONResponse(
            {
                "error": (
                    "Enrollment failed — audio too short or resemblyzer not installed. "
                    "Install with: pip install resemblyzer"
                )
            },
            status_code=422,
        )

    # Optionally persist the label on the VoicePrint record
    if label:
        result = await db.execute(
            select(VoicePrint).where(VoicePrint.id == voiceprint_id)
        )
        vp = result.scalar_one_or_none()
        if vp:
            vp.label = label
            await db.commit()

    return {
        "voiceprint_id": voiceprint_id,
        "phone_number": phone_number,
        "contact_id": contact_id,
        "label": label,
        "message": "Voiceprint enrolled successfully.",
    }


# ── Verify ────────────────────────────────────────────────────────────────────

@router.post("/verify")
async def verify_voiceprint(
    phone_number: str = Form(..., description="Caller E.164 number"),
    sample_rate: int = Form(16000),
    audio: UploadFile = File(..., description="First few seconds of caller audio"),
    auth: AuthContext = Depends(get_auth),
):
    """
    Verify whether the uploaded audio matches any enrolled voiceprint.

    Returns the matching contact_id / voiceprint_id and confidence score.
    Threshold is 0.75; anything below that returns `matched: false`.
    """
    raw_bytes = await audio.read()

    # Strip WAV header if present
    pcm_bytes = raw_bytes
    if raw_bytes[:4] == b"RIFF":
        idx = 12
        while idx < len(raw_bytes) - 8:
            chunk_id = raw_bytes[idx:idx+4]
            chunk_size = int.from_bytes(raw_bytes[idx+4:idx+8], "little")
            if chunk_id == b"data":
                pcm_bytes = raw_bytes[idx+8: idx+8+chunk_size]
                break
            idx += 8 + chunk_size

    matched_id, confidence = await speaker_verifier.verify(
        phone_number=phone_number,
        pcm_bytes=pcm_bytes,
        tenant_id=auth.tenant_id,
        sample_rate=sample_rate,
    )

    return {
        "matched": matched_id is not None,
        "matched_id": matched_id,
        "confidence": round(confidence, 4),
        "threshold": 0.75,
    }


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{voiceprint_id}")
async def delete_voiceprint(
    voiceprint_id: str,
    auth: AuthContext = Depends(get_auth),
):
    """Delete a stored voiceprint by ID."""
    deleted = await speaker_verifier.delete_voiceprint(
        voiceprint_id=voiceprint_id,
        tenant_id=auth.tenant_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Voiceprint not found.")
    return {"deleted": True, "voiceprint_id": voiceprint_id}
