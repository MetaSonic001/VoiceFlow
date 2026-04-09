"""
/analytics routes — mirrors Express src/routes/analytics.ts
"""
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Agent, CallLog, Document

router = APIRouter()


def _fmt_dur(sec: int) -> str:
    return f"{sec // 60}m {sec % 60}s"


def _days_from_range(time_range: str) -> int:
    return {"24h": 1, "7d": 7, "30d": 30, "90d": 90}.get(time_range, 7)


@router.get("/overview")
async def overview(
    timeRange: str = "7d",
    agentId: Optional[str] = None,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    days = _days_from_range(timeRange)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    base = [CallLog.tenantId == auth.tenant_id, CallLog.startedAt >= since]
    if agentId and agentId != "all":
        base.append(CallLog.agentId == agentId)

    total = (await db.execute(select(func.count(CallLog.id)).where(*base))).scalar() or 0
    rated = (await db.execute(select(func.count(CallLog.id)).where(*base, CallLog.rating.isnot(None)))).scalar() or 0
    thumbs_up = (await db.execute(select(func.count(CallLog.id)).where(*base, CallLog.rating == 1))).scalar() or 0
    success_rate = round(thumbs_up / rated * 100, 1) if rated > 0 else None

    avg_dur_r = await db.execute(
        select(func.avg(CallLog.durationSeconds)).where(*base, CallLog.durationSeconds.isnot(None))
    )
    avg_dur = avg_dur_r.scalar() or 0

    # calls per day
    logs_r = await db.execute(select(CallLog.startedAt).where(*base))
    all_dates = [r[0] for r in logs_r.all()]
    now = datetime.now(timezone.utc)
    day_counts: dict[str, int] = {}
    for i in range(days - 1, -1, -1):
        d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        day_counts[d] = 0
    for dt in all_dates:
        key = dt.strftime("%Y-%m-%d")
        if key in day_counts:
            day_counts[key] += 1

    # Count active agents
    active_agents = (await db.execute(
        select(func.count(Agent.id)).where(
            Agent.tenantId == auth.tenant_id, Agent.status == "active"
        )
    )).scalar() or 0

    avg_dur_val = round(float(avg_dur), 1)

    return {
        "totalInteractions": total,
        "successRate": success_rate,
        "avgResponseTime": _fmt_dur(int(avg_dur)),
        "avgResponseTimeSec": avg_dur_val,
        "activeAgents": active_agents,
        "satisfaction": success_rate,
        "timeSeries": [{"date": d, "calls": c, "chats": c} for d, c in day_counts.items()],
        "callsPerDay": [{"date": d, "count": c} for d, c in day_counts.items()],
        "timeRange": timeRange,
        "channelPerformance": {
            "phone": {"count": 0, "avgDuration": "0m 0s", "successRate": success_rate or 0},
            "chat": {"count": total, "avgDuration": _fmt_dur(int(avg_dur)), "successRate": success_rate or 0},
        },
    }


@router.get("/calls")
async def calls(
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None,
    agentId: Optional[str] = None,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    page = max(1, page)
    limit = min(200, max(1, limit))
    where = [CallLog.tenantId == auth.tenant_id]
    if agentId and agentId != "all":
        where.append(CallLog.agentId == agentId)
    if search:
        where.append(CallLog.transcript.ilike(f"%{search}%"))

    total = (await db.execute(select(func.count(CallLog.id)).where(*where))).scalar() or 0

    q = (
        select(CallLog, Agent.name.label("agent_name"))
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
        agent_name = row[1] or "Unknown"
        logs.append({
            "id": log.id,
            "type": "phone" if log.callerPhone else "chat",
            "customerInfo": log.callerPhone or "Web Chat",
            "agentName": agent_name,
            "agentId": log.agentId,
            "startTime": log.startedAt.isoformat() if log.startedAt else None,
            "duration": log.durationSeconds or 0,
            "status": "completed" if log.endedAt else "in-progress",
            "resolution": "resolved" if log.rating == 1 else ("escalated" if log.rating == -1 else "resolved"),
            "summary": "",
            "sentiment": "positive" if log.rating == 1 else ("negative" if log.rating == -1 else "neutral"),
            "tags": [],
            "transcript": log.transcript,
        })

    return {
        "logs": logs,
        "total": total,
        "page": page,
        "limit": limit,
        "totalPages": math.ceil(total / limit) if limit > 0 else 0,
    }


@router.get("/realtime")
async def realtime(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    recent_calls = (await db.execute(
        select(func.count(CallLog.id)).where(
            CallLog.tenantId == auth.tenant_id, CallLog.startedAt >= one_hour_ago, CallLog.callerPhone.isnot(None)
        )
    )).scalar() or 0

    recent_chats = (await db.execute(
        select(func.count(CallLog.id)).where(
            CallLog.tenantId == auth.tenant_id, CallLog.startedAt >= one_hour_ago, CallLog.callerPhone.is_(None)
        )
    )).scalar() or 0

    today_total = (await db.execute(
        select(func.count(CallLog.id)).where(CallLog.tenantId == auth.tenant_id, CallLog.startedAt >= today_start)
    )).scalar() or 0

    agents_count = (await db.execute(
        select(func.count(Agent.id)).where(Agent.tenantId == auth.tenant_id)
    )).scalar() or 0

    return {
        "active_calls": recent_calls,
        "active_chats": recent_chats,
        "queued_interactions": 0,
        "online_agents": agents_count,
        "today_total": today_total,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/metrics-chart")
async def metrics_chart(
    timeRange: str = "7d",
    agentId: Optional[str] = None,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    days = _days_from_range(timeRange)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    where = [CallLog.tenantId == auth.tenant_id, CallLog.startedAt >= since]
    if agentId and agentId != "all":
        where.append(CallLog.agentId == agentId)

    r = await db.execute(select(CallLog.startedAt, CallLog.callerPhone).where(*where))
    logs = r.all()

    now = datetime.now(timezone.utc)
    day_counts: dict[str, dict] = {}
    for i in range(days - 1, -1, -1):
        d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        day_counts[d] = {"calls": 0, "chats": 0}
    for started, phone in logs:
        key = started.strftime("%Y-%m-%d")
        if key in day_counts:
            if phone:
                day_counts[key]["calls"] += 1
            else:
                day_counts[key]["chats"] += 1

    return {
        "data": [
            {"date": d, "calls": v["calls"], "chats": v["chats"], "total": v["calls"] + v["chats"]}
            for d, v in day_counts.items()
        ]
    }


@router.get("/agent-comparison")
async def agent_comparison(
    timeRange: str = "7d",
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    days = _days_from_range(timeRange)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    agents_r = await db.execute(select(Agent).where(Agent.tenantId == auth.tenant_id))
    agents = agents_r.scalars().all()

    comparison = []
    for agent in agents:
        logs_r = await db.execute(
            select(CallLog.rating, CallLog.durationSeconds).where(
                CallLog.agentId == agent.id, CallLog.startedAt >= since
            )
        )
        logs = logs_r.all()
        total = len(logs)
        rated = [l for l in logs if l[0] is not None]
        thumbs_up = len([l for l in rated if l[0] == 1])
        durations = [l[1] for l in logs if l[1] is not None]
        avg_dur = round(sum(durations) / len(durations), 1) if durations else 0

        comparison.append({
            "agentId": agent.id,
            "agentName": agent.name,
            "totalInteractions": total,
            "successRate": round(thumbs_up / len(rated) * 100, 1) if rated else None,
            "avgResponseTime": avg_dur,
            "customerSatisfaction": None,
        })

    return {"agents": comparison}


@router.get("/usage")
async def usage(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    agents_count = (await db.execute(select(func.count(Agent.id)).where(Agent.tenantId == auth.tenant_id))).scalar() or 0
    logs_count = (await db.execute(select(func.count(CallLog.id)).where(CallLog.tenantId == auth.tenant_id))).scalar() or 0
    docs_count = (await db.execute(select(func.count(Document.id)).where(Document.tenantId == auth.tenant_id))).scalar() or 0

    return {
        "agents": agents_count,
        "callLogs": logs_count,
        "documents": docs_count,
    }
