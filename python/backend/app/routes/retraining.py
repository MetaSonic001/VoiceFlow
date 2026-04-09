"""
/api/retraining routes — mirrors Express src/routes/retraining.ts
"""
import json
import math
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import RetrainingExample, CallLog, Agent

router = APIRouter()


@router.get("/")
async def list_examples(
    page: int = 1,
    limit: int = 50,
    status: Optional[str] = None,
    agentId: Optional[str] = None,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    page = max(1, page)
    limit = min(200, max(1, limit))
    where = [RetrainingExample.tenantId == auth.tenant_id]
    if status:
        where.append(RetrainingExample.status == status)
    if agentId:
        where.append(RetrainingExample.agentId == agentId)

    total = (await db.execute(select(func.count(RetrainingExample.id)).where(*where))).scalar() or 0
    q = (
        select(RetrainingExample, Agent.id.label("a_id"), Agent.name.label("a_name"))
        .outerjoin(Agent, Agent.id == RetrainingExample.agentId)
        .where(*where)
        .order_by(RetrainingExample.createdAt.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(q)
    rows = result.all()

    examples = []
    for row in rows:
        ex = row[0]
        examples.append({
            "id": ex.id,
            "tenantId": ex.tenantId,
            "agentId": ex.agentId,
            "callLogId": ex.callLogId,
            "userQuery": ex.userQuery,
            "badResponse": ex.badResponse,
            "idealResponse": ex.idealResponse,
            "status": ex.status,
            "approvedAt": ex.approvedAt.isoformat() if ex.approvedAt else None,
            "approvedBy": ex.approvedBy,
            "createdAt": ex.createdAt.isoformat() if ex.createdAt else None,
            "updatedAt": ex.updatedAt.isoformat() if ex.updatedAt else None,
            "agent": {"id": row[1], "name": row[2]} if row[1] else None,
        })

    return {"examples": examples, "total": total, "page": page, "limit": limit, "pages": math.ceil(total / limit) if limit else 0}


@router.get("/stats")
async def retraining_stats(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    tid = auth.tenant_id
    pending = (await db.execute(select(func.count(RetrainingExample.id)).where(RetrainingExample.tenantId == tid, RetrainingExample.status == "pending"))).scalar() or 0
    approved = (await db.execute(select(func.count(RetrainingExample.id)).where(RetrainingExample.tenantId == tid, RetrainingExample.status == "approved"))).scalar() or 0
    rejected = (await db.execute(select(func.count(RetrainingExample.id)).where(RetrainingExample.tenantId == tid, RetrainingExample.status == "rejected"))).scalar() or 0
    flagged = (await db.execute(select(func.count(CallLog.id)).where(CallLog.tenantId == tid, CallLog.flaggedForRetraining.is_(True), CallLog.retrained.is_(False)))).scalar() or 0

    return {"pending": pending, "approved": approved, "rejected": rejected, "flaggedNotProcessed": flagged}


@router.patch("/{example_id}")
async def update_example(example_id: str, body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RetrainingExample).where(RetrainingExample.id == example_id))
    ex = result.scalar_one_or_none()
    if not ex:
        return JSONResponse({"error": "Example not found"}, status_code=404)
    if ex.tenantId != auth.tenant_id:
        return JSONResponse({"error": "Forbidden"}, status_code=403)

    if "idealResponse" in body:
        ex.idealResponse = body["idealResponse"]
    if "status" in body:
        ex.status = body["status"]
        if body["status"] == "approved":
            ex.approvedAt = datetime.now(timezone.utc)
            ex.approvedBy = auth.user_id

    await db.commit()
    await db.refresh(ex)
    return {"id": ex.id, "status": ex.status, "idealResponse": ex.idealResponse}


@router.delete("/{example_id}")
async def delete_example(example_id: str, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RetrainingExample).where(RetrainingExample.id == example_id))
    ex = result.scalar_one_or_none()
    if not ex:
        return JSONResponse({"error": "Example not found"}, status_code=404)
    if ex.tenantId != auth.tenant_id:
        return JSONResponse({"error": "Forbidden"}, status_code=403)
    await db.delete(ex)
    await db.commit()
    return {"deleted": True}


@router.post("/process")
async def process_retraining(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    """Process flagged call logs: parse transcripts and create RetrainingExample records."""
    flagged = await db.execute(
        select(CallLog).where(
            CallLog.tenantId == auth.tenant_id,
            CallLog.flaggedForRetraining.is_(True),
            CallLog.retrained.is_(False),
        )
    )
    count = 0
    for log in flagged.scalars().all():
        # Parse transcript to extract Q&A pairs
        try:
            transcript = json.loads(log.transcript) if isinstance(log.transcript, str) else log.transcript
            if isinstance(transcript, list):
                # Extract user-query / assistant-response pairs
                for i in range(len(transcript)):
                    turn = transcript[i]
                    if turn.get("role") == "user" and i + 1 < len(transcript):
                        next_turn = transcript[i + 1]
                        if next_turn.get("role") == "assistant":
                            user_query = turn.get("content", "").strip()
                            bad_response = next_turn.get("content", "").strip()
                            if user_query and bad_response:
                                example = RetrainingExample(
                                    tenantId=auth.tenant_id,
                                    agentId=log.agentId,
                                    callLogId=log.id,
                                    userQuery=user_query,
                                    badResponse=bad_response,
                                    idealResponse=bad_response,  # Admin will edit this
                                    status="pending",
                                )
                                db.add(example)
                                count += 1
        except Exception:
            pass  # Skip unparseable transcripts
        log.retrained = True

    await db.commit()
    return {"processed": True, "examplesCreated": count}


@router.post("/process-now")
async def process_now(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    return await process_retraining(auth=auth, db=db)
