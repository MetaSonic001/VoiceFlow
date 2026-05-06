"""
Speaker Verification — voice biometric caller identification.

Uses resemblyzer (lightweight ~10MB ECAPA-TDNN encoder, CPU-only) to:
  1. Enroll a voiceprint from a call recording sample
  2. Verify a caller against stored voiceprints to identify returning callers

Gracefully degrades: if resemblyzer is not installed, enrollment and
verification still succeed but return confidence=0.0 and no match.

Usage:
    from app.services.speaker_verification import speaker_verifier

    # Enroll
    vp_id = await speaker_verifier.enroll(
        phone_number="+919876543210",
        pcm_bytes=raw_pcm_16khz,
        tenant_id=tenant.id,
        contact_id=contact.id,
    )

    # Verify
    contact_id, confidence = await speaker_verifier.verify(
        phone_number="+919876543210",
        pcm_bytes=first_3sec_pcm,
        tenant_id=tenant.id,
    )
    if confidence > 0.75:
        greeting = f"Welcome back, {contact.name}!"
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

import numpy as np

logger = logging.getLogger("voiceflow.speaker_verification")

# Attempt to import resemblyzer; graceful fallback if not installed
try:
    from resemblyzer import VoiceEncoder, preprocess_wav
    _encoder = VoiceEncoder()
    _RESEMBLYZER_AVAILABLE = True
    logger.info("[speaker_verification] resemblyzer loaded OK")
except ImportError:
    _RESEMBLYZER_AVAILABLE = False
    logger.warning(
        "[speaker_verification] resemblyzer not installed — "
        "run: pip install resemblyzer. Speaker verification disabled."
    )

_COSINE_THRESHOLD = 0.75   # minimum similarity to consider a match


def _pcm_to_wav_array(pcm_bytes: bytes, sample_rate: int = 16000) -> np.ndarray:
    """Convert raw PCM 16-bit LE bytes to float32 numpy array in [-1, 1]."""
    arr = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    return arr


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two embedding vectors."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def _embed(pcm_bytes: bytes, sample_rate: int = 16000) -> Optional[list[float]]:
    """
    Return speaker embedding from PCM bytes.
    Returns None if resemblyzer is unavailable or the audio is too short.
    """
    if not _RESEMBLYZER_AVAILABLE:
        return None
    try:
        wav = _pcm_to_wav_array(pcm_bytes, sample_rate)
        if len(wav) < sample_rate * 1:  # need at least 1 second
            logger.debug("[speaker_verification] audio too short for embedding")
            return None
        # resemblyzer expects a numpy float64 array at its native rate (16kHz)
        wav64 = wav.astype(np.float64)
        processed = preprocess_wav(wav64, source_sr=sample_rate)
        embedding = _encoder.embed_utterance(processed)
        return embedding.tolist()
    except Exception as exc:
        logger.warning("[speaker_verification] embed failed: %s", exc)
        return None


class SpeakerVerifier:
    """
    Manage voiceprint enrollment and verification using PostgreSQL storage.

    Voiceprints are stored in the `VoicePrint` table (app/models.py).
    """

    # ── Enroll ────────────────────────────────────────────────────────────────

    async def enroll(
        self,
        phone_number: str,
        pcm_bytes: bytes,
        tenant_id: str,
        contact_id: Optional[str] = None,
        sample_rate: int = 16000,
    ) -> Optional[str]:
        """
        Enroll a speaker from audio samples.

        Parameters
        ----------
        phone_number:  E.164 number (used as a soft anchor for fast lookup)
        pcm_bytes:     Raw PCM 16-bit audio (at least 3s recommended)
        tenant_id:     Current tenant
        contact_id:    Optional Contact.id to link the voiceprint to
        sample_rate:   PCM sample rate in Hz (default 16000)

        Returns the voiceprint_id if successful, None otherwise.
        """
        embedding = _embed(pcm_bytes, sample_rate)
        if embedding is None:
            logger.info("[speaker_verification] enrollment skipped (no embedding)")
            return None

        voiceprint_id = str(uuid.uuid4())
        try:
            from app.database import AsyncSessionLocal
            from app.models import VoicePrint
            async with AsyncSessionLocal() as db:
                vp = VoicePrint(
                    id=voiceprint_id,
                    tenantId=tenant_id,
                    contactId=contact_id,
                    phoneNumber=phone_number,
                    embedding=embedding,
                )
                db.add(vp)
                await db.commit()
        except Exception as exc:
            logger.error("[speaker_verification] enroll DB error: %s", exc)
            return None

        logger.info(
            "[speaker_verification] enrolled phone=%s contact=%s vp=%s",
            phone_number, contact_id, voiceprint_id,
        )
        return voiceprint_id

    # ── Verify ────────────────────────────────────────────────────────────────

    async def verify(
        self,
        phone_number: str,
        pcm_bytes: bytes,
        tenant_id: str,
        sample_rate: int = 16000,
    ) -> tuple[Optional[str], float]:
        """
        Verify a caller against stored voiceprints for this tenant.

        Returns (contact_id_or_voiceprint_id, confidence_score).
        Returns (None, 0.0) if no match or resemblyzer unavailable.
        """
        embedding = _embed(pcm_bytes, sample_rate)
        if embedding is None:
            return None, 0.0

        try:
            from app.database import AsyncSessionLocal
            from app.models import VoicePrint
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(VoicePrint).where(VoicePrint.tenantId == tenant_id)
                )
                voiceprints = result.scalars().all()
        except Exception as exc:
            logger.error("[speaker_verification] verify DB error: %s", exc)
            return None, 0.0

        if not voiceprints:
            return None, 0.0

        # Priority order: phone-number matches first (faster), then global
        phone_vps = [vp for vp in voiceprints if vp.phoneNumber == phone_number]
        other_vps = [vp for vp in voiceprints if vp.phoneNumber != phone_number]

        best_id: Optional[str] = None
        best_score: float = 0.0

        for vp in (phone_vps + other_vps):
            if not vp.embedding:
                continue
            score = _cosine_sim(embedding, vp.embedding)
            if score > best_score:
                best_score = score
                best_id = vp.contactId or vp.id

        if best_score >= _COSINE_THRESHOLD:
            logger.info(
                "[speaker_verification] MATCH phone=%s contact/vp=%s score=%.3f",
                phone_number, best_id, best_score,
            )
            return best_id, best_score

        logger.debug(
            "[speaker_verification] no match phone=%s best_score=%.3f threshold=%.2f",
            phone_number, best_score, _COSINE_THRESHOLD,
        )
        return None, best_score

    # ── Delete ────────────────────────────────────────────────────────────────

    async def delete_voiceprint(self, voiceprint_id: str, tenant_id: str) -> bool:
        """Remove a stored voiceprint."""
        try:
            from app.database import AsyncSessionLocal
            from app.models import VoicePrint
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(VoicePrint).where(
                        VoicePrint.id == voiceprint_id,
                        VoicePrint.tenantId == tenant_id,
                    )
                )
                vp = result.scalar_one_or_none()
                if not vp:
                    return False
                await db.delete(vp)
                await db.commit()
            return True
        except Exception as exc:
            logger.error("[speaker_verification] delete error: %s", exc)
            return False

    # ── List ──────────────────────────────────────────────────────────────────

    async def list_voiceprints(self, tenant_id: str) -> list[dict]:
        """List all stored voiceprints for a tenant."""
        try:
            from app.database import AsyncSessionLocal
            from app.models import VoicePrint
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(VoicePrint).where(VoicePrint.tenantId == tenant_id)
                )
                vps = result.scalars().all()
                return [
                    {
                        "id": vp.id,
                        "contact_id": vp.contactId,
                        "phone_number": vp.phoneNumber,
                        "created_at": vp.createdAt.isoformat() if vp.createdAt else None,
                    }
                    for vp in vps
                ]
        except Exception as exc:
            logger.error("[speaker_verification] list error: %s", exc)
            return []


# Module singleton
speaker_verifier = SpeakerVerifier()
