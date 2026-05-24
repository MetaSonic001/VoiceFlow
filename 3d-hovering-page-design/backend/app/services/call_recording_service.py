"""
Call Recording Service — stores audio in MinIO, builds waveform, timestamps transcript.

Features:
  • Record inbound/outbound calls to MinIO (bucket: voiceflow-recordings)
  • Timestamped transcript aligned to audio for click-to-seek UI
  • Waveform data (amplitude samples at 1s intervals) for dashboard waveform player
  • Per-call consent disclosure tracking (required for legal compliance)
  • Presigned download URLs (24h TTL)

MinIO object key: recordings/{tenantId}/{agentId}/{callLogId}.wav

Usage:
  from app.services.call_recording_service import RecordingService
  recording_svc = RecordingService()
  await recording_svc.start_recording(call_log_id, tenant_id, agent_id)
  await recording_svc.append_chunk(call_log_id, pcm_bytes)
  await recording_svc.finish_recording(call_log_id, db, timestamped_transcript)
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
import struct
import wave
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("voiceflow.recording")

# In-memory accumulator for live-call audio chunks.
# Key: call_log_id, Value: list[bytes] (PCM chunks)
_buffers: dict[str, list[bytes]] = {}
_sample_rate: dict[str, int] = {}


class RecordingService:
    """
    Accumulates raw PCM audio chunks during a call, finalizes to WAV,
    uploads to MinIO, and stores metadata (waveform, timestamped transcript).
    """

    def start_recording(self, call_log_id: str, sample_rate: int = 8000) -> None:
        """Initialize a recording buffer for a call."""
        _buffers[call_log_id] = []
        _sample_rate[call_log_id] = sample_rate
        logger.debug("[recording] started buffer for call %s at %d Hz", call_log_id, sample_rate)

    def append_chunk(self, call_log_id: str, pcm_bytes: bytes) -> None:
        """Append a raw PCM chunk. Thread-safe for asyncio tasks."""
        if call_log_id in _buffers:
            _buffers[call_log_id].append(pcm_bytes)

    def discard(self, call_log_id: str) -> None:
        """Discard a recording (e.g. caller didn't consent)."""
        _buffers.pop(call_log_id, None)
        _sample_rate.pop(call_log_id, None)

    async def finish_recording(
        self,
        call_log_id: str,
        tenant_id: str,
        agent_id: str,
        db,
        timestamped_transcript: Optional[list[dict]] = None,
        consent_disclosed: bool = True,
    ) -> Optional[str]:
        """
        Finalize the recording, upload to MinIO, and persist CallRecording row.
        Returns the MinIO object key on success, None on failure.

        timestamped_transcript: [{"start_s": 1.2, "end_s": 3.4, "text": "...", "speaker": "agent"}]
        """
        chunks = _buffers.pop(call_log_id, None)
        sr = _sample_rate.pop(call_log_id, 8000)
        if not chunks:
            return None

        raw_pcm = b"".join(chunks)
        duration_s = len(raw_pcm) // (sr * 2)  # 16-bit mono

        # Build WAV
        wav_bytes = _pcm_to_wav(raw_pcm, sample_rate=sr)
        file_size = len(wav_bytes)

        # Build sparse waveform (1 sample/second, amplitude 0.0–1.0)
        waveform = _build_waveform(raw_pcm, sr, duration_s)

        # Upload to MinIO
        minio_key = f"recordings/{tenant_id}/{agent_id}/{call_log_id}.wav"
        uploaded = await _upload_to_minio(minio_key, wav_bytes)
        if not uploaded:
            logger.warning("[recording] MinIO upload failed for %s", call_log_id)
            return None

        # Persist DB row
        from app.models import CallRecording
        recording = CallRecording(
            tenantId=tenant_id,
            agentId=agent_id,
            callLogId=call_log_id,
            minioKey=minio_key,
            durationSeconds=duration_s,
            fileSizeBytes=file_size,
            consentDisclosed=consent_disclosed,
            waveformData=waveform,
            timestampedTranscript=timestamped_transcript or [],
        )
        db.add(recording)
        await db.commit()
        logger.info("[recording] saved %s (%ds, %d bytes)", minio_key, duration_s, file_size)
        return minio_key

    async def get_download_url(self, minio_key: str, expires_seconds: int = 86400) -> Optional[str]:
        """Generate a presigned download URL (default 24h TTL)."""
        return await _presigned_url(minio_key, expires_seconds)


# ── MinIO helpers (lazy import) ────────────────────────────────────────────────

async def _upload_to_minio(key: str, data: bytes) -> bool:
    try:
        from minio import Minio
        from minio.error import S3Error
        from app.config import settings

        loop = asyncio.get_event_loop()

        def _sync():
            client = Minio(
                settings.MINIO_ENDPOINT.replace("http://", "").replace("https://", ""),
                access_key=settings.MINIO_ROOT_USER,
                secret_key=settings.MINIO_ROOT_PASSWORD,
                secure=settings.MINIO_ENDPOINT.startswith("https"),
            )
            bucket = "voiceflow-recordings"
            try:
                client.make_bucket(bucket)
            except S3Error:
                pass  # already exists
            client.put_object(
                bucket, key, io.BytesIO(data), length=len(data), content_type="audio/wav"
            )
            return True

        return await loop.run_in_executor(None, _sync)
    except Exception as exc:
        logger.warning("[recording] MinIO upload error: %s", exc)
        return False


async def _presigned_url(key: str, expires_s: int) -> Optional[str]:
    try:
        from minio import Minio
        from datetime import timedelta
        from app.config import settings

        loop = asyncio.get_event_loop()

        def _sync():
            client = Minio(
                settings.MINIO_ENDPOINT.replace("http://", "").replace("https://", ""),
                access_key=settings.MINIO_ROOT_USER,
                secret_key=settings.MINIO_ROOT_PASSWORD,
                secure=settings.MINIO_ENDPOINT.startswith("https"),
            )
            return client.presigned_get_object(
                "voiceflow-recordings", key, expires=timedelta(seconds=expires_s)
            )

        return await loop.run_in_executor(None, _sync)
    except Exception as exc:
        logger.warning("[recording] presigned URL error: %s", exc)
        return None


# ── Audio helpers ──────────────────────────────────────────────────────────────

def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 8000, channels: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def _build_waveform(pcm_bytes: bytes, sample_rate: int, duration_s: int) -> list[float]:
    """
    Build a sparse waveform array — one RMS amplitude value per second.
    Values normalized to [0.0, 1.0].
    """
    waveform: list[float] = []
    chunk_size = sample_rate * 2  # 1 second of 16-bit mono
    max_rms = 0.0
    rms_values: list[float] = []

    for i in range(0, len(pcm_bytes), chunk_size):
        chunk = pcm_bytes[i:i + chunk_size]
        n = len(chunk) // 2
        if n == 0:
            rms_values.append(0.0)
            continue
        samples = struct.unpack(f"<{n}h", chunk[:n * 2])
        rms = (sum(s * s for s in samples) / n) ** 0.5
        rms_values.append(rms)
        if rms > max_rms:
            max_rms = rms

    if max_rms > 0:
        waveform = [round(v / max_rms, 3) for v in rms_values]
    else:
        waveform = [0.0] * len(rms_values)
    return waveform


# Module singleton
recording_service = RecordingService()
