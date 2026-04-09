"""
/api/logs routes — mirrors Express src/routes/logs.ts
"""
import math
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import CallLog, Agent

router = APIRouter()


@router.get("/")
async def list_logs(
    page: int = 1,
    limit: int = 50,
    agentId: Optional[str] = None,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    page = max(1, page)
    limit = min(200, max(1, limit))
    where = [CallLog.tenantId == auth.tenant_id]
    if agentId:
        where.append(CallLog.agentId == agentId)

    total = (await db.execute(select(func.count(CallLog.id)).where(*where))).scalar() or 0
    q = (
        select(CallLog, Agent.id.label("a_id"), Agent.name.label("a_name"))
        .outerjoin(Agent, Agent.id == CallLog.agentId)
        .where(*where)
        .order_by(CallLog.startedAt.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(q)
    rows = result.all()

    logs = []
    for row in rows:
        log = row[0]
        logs.append({
            "id": log.id,
            "tenantId": log.tenantId,
            "agentId": log.agentId,
            "callerPhone": log.callerPhone,
            "startedAt": log.startedAt.isoformat() if log.startedAt else None,
            "endedAt": log.endedAt.isoformat() if log.endedAt else None,
            "durationSeconds": log.durationSeconds,
            "transcript": log.transcript,
            "analysis": log.analysis,
            "rating": log.rating,
            "ratingNotes": log.ratingNotes,
            "flaggedForRetraining": log.flaggedForRetraining,
            "retrained": log.retrained,
            "createdAt": log.createdAt.isoformat() if log.createdAt else None,
            "agent": {"id": row[1], "name": row[2]} if row[1] else None,
        })

    return {"logs": logs, "total": total, "page": page, "limit": limit, "pages": math.ceil(total / limit) if limit else 0}


@router.patch("/{log_id}/rating")
async def rate_log(log_id: str, body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    rating = body.get("rating")
    if rating not in (1, -1):
        return JSONResponse({"error": "rating must be 1 or -1"}, status_code=400)

    result = await db.execute(select(CallLog).where(CallLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        return JSONResponse({"error": "Log not found"}, status_code=404)
    if log.tenantId != auth.tenant_id:
        return JSONResponse({"error": "Forbidden"}, status_code=403)

    log.rating = rating
    log.ratingNotes = body.get("notes")
    await db.commit()
    await db.refresh(log)
    return {"id": log.id, "rating": log.rating, "ratingNotes": log.ratingNotes}


@router.post("/{log_id}/flag")
async def flag_log(log_id: str, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CallLog).where(CallLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        return JSONResponse({"error": "Log not found"}, status_code=404)
    if log.tenantId != auth.tenant_id:
        return JSONResponse({"error": "Forbidden"}, status_code=403)

    log.flaggedForRetraining = True
    await db.commit()
    return {"id": log.id, "flaggedForRetraining": True}
