"""
/api/recordings routes — call recording CRUD + presigned download.

GET  /api/recordings/                      — list recordings for tenant
GET  /api/recordings/{recording_id}        — get recording metadata + waveform + transcript
GET  /api/recordings/{recording_id}/download  — presigned MinIO download URL
DELETE /api/recordings/{recording_id}      — delete recording + MinIO object
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import CallRecording
from app.services.call_recording_service import recording_service

logger = logging.getLogger("voiceflow.recordings_routes")
router = APIRouter()


@router.get("/")
async def list_recordings(
    agent_id: str | None = None,
    limit: int = 50,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    where = [CallRecording.tenantId == auth.tenant_id]
    if agent_id:
        where.append(CallRecording.agentId == agent_id)
    result = await db.execute(
        select(CallRecording).where(*where).order_by(CallRecording.createdAt.desc()).limit(limit)
    )
    recordings = result.scalars().all()
    return [
        {
            "id": r.id,
            "callLogId": r.callLogId,
            "agentId": r.agentId,
            "durationSeconds": r.durationSeconds,
            "fileSizeBytes": r.fileSizeBytes,
            "consentDisclosed": r.consentDisclosed,
            "createdAt": r.createdAt.isoformat() if r.createdAt else None,
        }
        for r in recordings
    ]


@router.get("/{recording_id}")
async def get_recording(
    recording_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CallRecording).where(
            CallRecording.id == recording_id,
            CallRecording.tenantId == auth.tenant_id,
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return {
        "id": rec.id,
        "callLogId": rec.callLogId,
        "agentId": rec.agentId,
        "minioKey": rec.minioKey,
        "durationSeconds": rec.durationSeconds,
        "fileSizeBytes": rec.fileSizeBytes,
        "consentDisclosed": rec.consentDisclosed,
        "waveformData": rec.waveformData,
        "timestampedTranscript": rec.timestampedTranscript,
        "createdAt": rec.createdAt.isoformat() if rec.createdAt else None,
    }


@router.get("/{recording_id}/download")
async def get_download_url(
    recording_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CallRecording).where(
            CallRecording.id == recording_id,
            CallRecording.tenantId == auth.tenant_id,
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        return JSONResponse({"error": "Not found"}, status_code=404)
    url = await recording_service.get_download_url(rec.minioKey)
    if not url:
        return JSONResponse({"error": "Could not generate download URL"}, status_code=503)
    return {"url": url, "expires_in": 86400}


@router.delete("/{recording_id}")
async def delete_recording(
    recording_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CallRecording).where(
            CallRecording.id == recording_id,
            CallRecording.tenantId == auth.tenant_id,
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        return JSONResponse({"error": "Not found"}, status_code=404)
    # Best-effort MinIO deletion
    try:
        from minio import Minio
        from app.config import settings
        client = Minio(
            settings.MINIO_ENDPOINT.replace("http://", "").replace("https://", ""),
            access_key=settings.MINIO_ROOT_USER,
            secret_key=settings.MINIO_ROOT_PASSWORD,
            secure=settings.MINIO_ENDPOINT.startswith("https"),
        )
        client.remove_object("voiceflow-recordings", rec.minioKey)
    except Exception as exc:
        logger.warning("[recordings] MinIO delete failed for %s: %s", rec.minioKey, exc)
    await db.delete(rec)
    await db.commit()
    return {"deleted": True}
