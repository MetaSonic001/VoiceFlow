"""
/analytics routes — mirrors Express src/routes/analytics.ts
"""
import csv
import io
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Agent, CallLog, Campaign, Document

router = APIRouter()


def _fmt_dur(sec: int) -> str:
    return f"{sec // 60}m {sec % 60}s"


def _days_from_range(time_range: str) -> int:
    return {"24h": 1, "7d": 7, "30d": 30, "90d": 90}.get(time_range, 7)


def _infer_conversion(analysis: Optional[dict], extracted: Optional[Any]) -> bool:
    """Business conversion signal — extend analysis JSON over time."""
    if isinstance(analysis, dict):
        co = str(analysis.get("callOutcome") or analysis.get("call_outcome") or "").lower()
        if co in ("booked", "converted", "sale", "appointment", "appointment_booked", "qualified_sale"):
            return True
        if analysis.get("goalAchieved") is True:
            return True
    if isinstance(extracted, dict):
        stage = str(extracted.get("conversionStage") or extracted.get("stage") or "").lower()
        if stage in ("won", "booked", "converted", "closed"):
            return True
    return False


def _infer_qualified_lead(analysis: Optional[dict], extracted: Optional[Any]) -> bool:
    """Qualification / lead readiness heuristic."""
    if isinstance(analysis, dict):
        if analysis.get("qualified") is True or analysis.get("leadQualified") is True:
            return True
    if isinstance(extracted, dict):
        if extracted.get("qualified") is True:
            return True
        filled = sum(
            1 for v in extracted.values() if v is not None and str(v).strip()
        )
        if filled >= 3:
            return True
    return False


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
        analysis = log.analysis if isinstance(log.analysis, dict) else {}
        extracted = log.extractedVariables if isinstance(log.extractedVariables, dict) else {}
        logs.append({
            "id": log.id,
            "type": "phone" if log.callerPhone else "chat",
            "customerInfo": log.callerPhone or "Web Chat",
            "agentName": agent_name,
            "agentId": log.agentId,
            "callSid": log.callSid,
            "startTime": log.startedAt.isoformat() if log.startedAt else None,
            "duration": log.durationSeconds or 0,
            "status": "completed" if log.endedAt else "in-progress",
            "resolution": "resolved" if log.rating == 1 else ("escalated" if log.rating == -1 else "resolved"),
            "summary": (analysis.get("summary") or "")[:500],
            "goalAchieved": analysis.get("goalAchieved"),
            "conversionInferred": _infer_conversion(analysis if analysis else None, extracted or None),
            "qualifiedInferred": _infer_qualified_lead(analysis if analysis else None, extracted or None),
            "sentiment": analysis.get("sentiment") or (
                "positive" if log.rating == 1 else ("negative" if log.rating == -1 else "neutral")
            ),
            "tags": [],
            "transcript": log.transcript,
            "recordingUrl": log.recordingUrl,
            "hasRecording": bool(log.recordingUrl),
            "hasAnalysis": bool(log.analysis),
            "extractedVariables": log.extractedVariables,
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


@router.get("/bi-summary")
async def bi_summary(
    timeRange: str = "7d",
    agentId: Optional[str] = None,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Unified business-intelligence snapshot: duration split, conversion & qualification rates,
    recording coverage, and per-agent leaderboard (volume-weighted).
    """
    days = _days_from_range(timeRange)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    where = [CallLog.tenantId == auth.tenant_id, CallLog.startedAt >= since]
    if agentId and agentId != "all":
        where.append(CallLog.agentId == agentId)

    result = await db.execute(
        select(
            CallLog.callerPhone,
            CallLog.durationSeconds,
            CallLog.analysis,
            CallLog.extractedVariables,
            CallLog.recordingUrl,
            CallLog.agentId,
        ).where(*where)
    )
    rows = result.all()

    phone_durs: list[int] = []
    chat_durs: list[int] = []
    conv_count = 0
    qual_count = 0
    analyzed = 0
    with_rec = 0
    phone_n = 0
    chat_n = 0

    per_agent: dict[str, dict[str, Any]] = {}

    for caller_phone, dur, analysis, extracted, rec_url, aid in rows:
        if caller_phone:
            phone_n += 1
            if dur is not None:
                phone_durs.append(int(dur))
        else:
            chat_n += 1
            if dur is not None:
                chat_durs.append(int(dur))

        ad = analysis if isinstance(analysis, dict) else {}
        ex = extracted if isinstance(extracted, dict) else {}
        if ad:
            analyzed += 1
        if rec_url:
            with_rec += 1
        if _infer_conversion(ad if ad else None, ex if ex else None):
            conv_count += 1
        if _infer_qualified_lead(ad if ad else None, ex if ex else None):
            qual_count += 1

        bucket = per_agent.setdefault(
            aid,
            {"calls": 0, "conv": 0, "dur_sum": 0, "dur_n": 0},
        )
        bucket["calls"] += 1
        if _infer_conversion(ad if ad else None, ex if ex else None):
            bucket["conv"] += 1
        if dur is not None:
            bucket["dur_sum"] += int(dur)
            bucket["dur_n"] += 1

    total = len(rows)

    names_map: dict[str, str] = {}
    if per_agent:
        agent_ids = list(per_agent.keys())
        ar = await db.execute(select(Agent.id, Agent.name).where(Agent.id.in_(agent_ids)))
        names_map = {r[0]: r[1] for r in ar.all()}

    leaderboard = []
    for aid, b in sorted(per_agent.items(), key=lambda x: x[1]["calls"], reverse=True)[:12]:
        cr = round(b["conv"] / b["calls"] * 100, 1) if b["calls"] else None
        avgd = round(b["dur_sum"] / b["dur_n"], 1) if b["dur_n"] else None
        leaderboard.append({
            "agentId": aid,
            "agentName": names_map.get(aid, str(aid)[:8]),
            "interactions": b["calls"],
            "conversionRatePercent": cr,
            "avgDurationSeconds": avgd,
        })

    return {
        "timeRange": timeRange,
        "windowStart": since.isoformat(),
        "totals": {
            "interactions": total,
            "phoneSessions": phone_n,
            "chatSessions": chat_n,
            "withPostCallAnalysis": analyzed,
            "withRecording": with_rec,
            "recordingCoveragePercent": round(with_rec / total * 100, 1) if total else None,
            "avgDurationSecondsPhone": round(sum(phone_durs) / len(phone_durs), 1) if phone_durs else None,
            "avgDurationSecondsChat": round(sum(chat_durs) / len(chat_durs), 1) if chat_durs else None,
        },
        "conversion": {
            "count": conv_count,
            "ratePercent": round(conv_count / total * 100, 1) if total else None,
            "definition": "goalAchieved, callOutcome booked/converted/sale, or CRM stage won/booked",
        },
        "qualification": {
            "count": qual_count,
            "ratePercent": round(qual_count / total * 100, 1) if total else None,
            "definition": "qualified flags in analysis/extractedVariables or 3+ captured fields",
        },
        "agentLeaderboard": leaderboard,
        "deepLinks": {
            "conversations": "/dashboard/calls/",
            "liveMonitor": "/dashboard/live-monitor/",
            "campaigns": "/dashboard/campaigns/",
            "recordings": "/dashboard/recordings/",
        },
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


@router.get("/resolution-stats")
async def resolution_stats(
    timeRange: str = "7d",
    agentId: Optional[str] = None,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Resolution rate, escalation rate and goal achievement from call analysis JSON."""
    days = _days_from_range(timeRange)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    where = [CallLog.tenantId == auth.tenant_id, CallLog.startedAt >= since, CallLog.analysis.isnot(None)]
    if agentId and agentId != "all":
        where.append(CallLog.agentId == agentId)

    logs_r = await db.execute(select(CallLog.analysis, CallLog.durationSeconds).where(*where))
    rows = logs_r.all()

    total = len(rows)
    resolved = 0
    escalated = 0
    total_duration = 0
    quality_scores: list[float] = []

    for analysis, dur in rows:
        if not isinstance(analysis, dict):
            continue
        if analysis.get("goalAchieved") is True:
            resolved += 1
        if analysis.get("escalated") is True or analysis.get("transferredToHuman") is True:
            escalated += 1
        if dur:
            total_duration += dur
        qs = analysis.get("qualityScore")
        if qs is not None:
            try:
                quality_scores.append(float(qs))
            except (TypeError, ValueError):
                pass

    resolution_rate = round(resolved / total * 100, 1) if total > 0 else None
    escalation_rate = round(escalated / total * 100, 1) if total > 0 else None
    avg_quality = round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else None
    avg_duration = round(total_duration / total, 1) if total > 0 else None

    return {
        "totalCalls": total,
        "resolvedCalls": resolved,
        "escalatedCalls": escalated,
        "resolutionRate": resolution_rate,
        "escalationRate": escalation_rate,
        "avgQualityScore": avg_quality,
        "avgDurationSeconds": avg_duration,
        "timeRange": timeRange,
    }


@router.get("/top-intents")
async def top_intents(
    timeRange: str = "7d",
    agentId: Optional[str] = None,
    limit: int = Query(default=10, le=50),
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Top N intents aggregated from call analysis JSON."""
    days = _days_from_range(timeRange)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    where = [CallLog.tenantId == auth.tenant_id, CallLog.startedAt >= since, CallLog.analysis.isnot(None)]
    if agentId and agentId != "all":
        where.append(CallLog.agentId == agentId)

    logs_r = await db.execute(select(CallLog.analysis).where(*where))
    rows = logs_r.scalars().all()

    intent_counts: dict[str, int] = {}
    for analysis in rows:
        if not isinstance(analysis, dict):
            continue
        intent = analysis.get("intent") or analysis.get("primaryIntent")
        if intent and isinstance(intent, str):
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

    sorted_intents = sorted(intent_counts.items(), key=lambda x: x[1], reverse=True)
    total = sum(intent_counts.values())

    return {
        "topIntents": [
            {
                "intent": name,
                "count": count,
                "percentage": round(count / total * 100, 1) if total > 0 else 0,
            }
            for name, count in sorted_intents[:limit]
        ],
        "totalClassified": total,
        "timeRange": timeRange,
    }


@router.get("/failure-modes")
async def failure_modes(
    timeRange: str = "7d",
    agentId: Optional[str] = None,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Common failure patterns from missedOpportunities and hallucinations in analysis JSON."""
    days = _days_from_range(timeRange)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    where = [CallLog.tenantId == auth.tenant_id, CallLog.startedAt >= since, CallLog.analysis.isnot(None)]
    if agentId and agentId != "all":
        where.append(CallLog.agentId == agentId)

    logs_r = await db.execute(select(CallLog.analysis).where(*where))
    rows = logs_r.scalars().all()

    failed_calls = 0
    hallucination_risk_calls = 0
    missed_opportunity_counts: dict[str, int] = {}

    total = 0
    for analysis in rows:
        if not isinstance(analysis, dict):
            continue
        total += 1
        if analysis.get("goalAchieved") is False:
            failed_calls += 1
        if analysis.get("hallucinationRisk") is True:
            hallucination_risk_calls += 1
        missed = analysis.get("missedOpportunities", [])
        if isinstance(missed, list):
            for item in missed:
                if isinstance(item, str):
                    missed_opportunity_counts[item] = missed_opportunity_counts.get(item, 0) + 1

    sorted_missed = sorted(missed_opportunity_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "totalAnalyzed": total,
        "failedCalls": failed_calls,
        "failureRate": round(failed_calls / total * 100, 1) if total > 0 else None,
        "hallucinationRiskCalls": hallucination_risk_calls,
        "hallucinationRate": round(hallucination_risk_calls / total * 100, 1) if total > 0 else None,
        "topMissedOpportunities": [
            {"description": desc, "count": count}
            for desc, count in sorted_missed[:10]
        ],
        "timeRange": timeRange,
    }


@router.get("/cost-estimate")
async def cost_estimate(
    timeRange: str = "7d",
    agentId: Optional[str] = None,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Estimated cost per call modeled from duration × token cost heuristics."""
    # Cost model (approximate USD):
    #   STT: $0.006/min (Groq Whisper turbo)
    #   LLM: $0.002/min of conversation (Llama 3.3 70B at ~500 tokens/min, $0.0039/1K)
    #   TTS: $0.004/min (Sarvam / ElevenLabs estimate)
    #   Telephony: $0.0085/min (Twilio)
    # Total: ~$0.0205 / minute
    COST_PER_SECOND = 0.0205 / 60

    days = _days_from_range(timeRange)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    where = [
        CallLog.tenantId == auth.tenant_id,
        CallLog.startedAt >= since,
        CallLog.durationSeconds.isnot(None),
    ]
    if agentId and agentId != "all":
        where.append(CallLog.agentId == agentId)

    r = await db.execute(
        select(
            func.count(CallLog.id),
            func.sum(CallLog.durationSeconds),
            func.avg(CallLog.durationSeconds),
            func.min(CallLog.durationSeconds),
            func.max(CallLog.durationSeconds),
        ).where(*where)
    )
    row = r.one()
    count, total_sec, avg_sec, min_sec, max_sec = row
    count = count or 0
    total_sec = float(total_sec or 0)
    avg_sec = float(avg_sec or 0)

    total_cost = round(total_sec * COST_PER_SECOND, 4)
    avg_cost = round(avg_sec * COST_PER_SECOND, 4)

    return {
        "totalCalls": count,
        "totalDurationSeconds": int(total_sec),
        "avgDurationSeconds": round(avg_sec, 1),
        "estimatedTotalCostUSD": total_cost,
        "estimatedAvgCostPerCallUSD": avg_cost,
        "costModel": {
            "sttPerMin": 0.006,
            "llmPerMin": 0.002,
            "ttsPerMin": 0.004,
            "telephonyPerMin": 0.0085,
            "totalPerMin": 0.0205,
        },
        "timeRange": timeRange,
    }


@router.get("/sentiment-trend")
async def sentiment_trend(
    timeRange: str = "7d",
    agentId: Optional[str] = None,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Daily average sentiment score (from CallLog.analysis.sentimentScore) for trend line."""
    days = _days_from_range(timeRange)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    where = [
        CallLog.tenantId == auth.tenant_id,
        CallLog.startedAt >= since,
        CallLog.analysis.isnot(None),
    ]
    if agentId and agentId != "all":
        where.append(CallLog.agentId == agentId)

    result = await db.execute(select(CallLog).where(*where).order_by(CallLog.startedAt))
    logs = result.scalars().all()

    # Bucket by day
    buckets: dict[str, list[float]] = {}
    for log in logs:
        analysis = log.analysis or {}
        score = analysis.get("sentimentScore")
        if score is None:
            # Derive from rating: 1=positive(0.8), -1=negative(0.2), 0=neutral(0.5)
            rating = log.rating or 0
            score = 0.8 if rating == 1 else (0.2 if rating == -1 else 0.5)
        day_key = log.startedAt.strftime("%Y-%m-%d") if log.startedAt else "unknown"
        buckets.setdefault(day_key, []).append(float(score))

    trend = [
        {"date": day, "avgSentiment": round(sum(scores) / len(scores), 3), "callCount": len(scores)}
        for day, scores in sorted(buckets.items())
    ]
    return {"trend": trend, "timeRange": timeRange}


@router.get("/handle-time-histogram")
async def handle_time_histogram(
    timeRange: str = "7d",
    agentId: Optional[str] = None,
    buckets: int = Query(10, ge=3, le=30),
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Duration distribution histogram — how many calls fall into each duration bucket."""
    days = _days_from_range(timeRange)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    where = [
        CallLog.tenantId == auth.tenant_id,
        CallLog.startedAt >= since,
        CallLog.durationSeconds.isnot(None),
        CallLog.durationSeconds > 0,
    ]
    if agentId and agentId != "all":
        where.append(CallLog.agentId == agentId)

    result = await db.execute(
        select(CallLog.durationSeconds).where(*where)
    )
    durations = [row[0] for row in result.all()]

    if not durations:
        return {"histogram": [], "timeRange": timeRange}

    min_d, max_d = min(durations), max(durations)
    if min_d == max_d:
        return {"histogram": [{"bucketLabel": f"{min_d}s", "count": len(durations), "minSec": min_d, "maxSec": max_d}], "timeRange": timeRange}

    bucket_size = math.ceil((max_d - min_d) / buckets)
    hist: dict[int, int] = {}
    for d in durations:
        bucket_idx = (d - min_d) // bucket_size
        hist[bucket_idx] = hist.get(bucket_idx, 0) + 1

    histogram = []
    for i in range(buckets):
        lo = min_d + i * bucket_size
        hi = lo + bucket_size
        histogram.append({
            "bucketLabel": f"{lo}–{hi}s",
            "minSec": lo,
            "maxSec": hi,
            "count": hist.get(i, 0),
        })

    # Trim trailing empty buckets
    while histogram and histogram[-1]["count"] == 0:
        histogram.pop()

    return {
        "histogram": histogram,
        "totalCalls": len(durations),
        "avgSec": round(sum(durations) / len(durations), 1),
        "medianSec": sorted(durations)[len(durations) // 2],
        "timeRange": timeRange,
    }


@router.get("/campaign-roi")
async def campaign_roi(
    timeRange: str = "30d",
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Campaign ROI: calls attempted, answered, resolved + estimated cost per resolution."""
    COST_PER_SECOND = 0.0205 / 60

    days = _days_from_range(timeRange)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    camps_result = await db.execute(
        select(Campaign).where(
            Campaign.tenantId == auth.tenant_id,
            Campaign.createdAt >= since,
        ).order_by(Campaign.createdAt.desc()).limit(50)
    )
    campaigns = camps_result.scalars().all()

    rows = []
    for camp in campaigns:
        # Get call logs for this campaign via agentId + createdAt range
        # (campaign contacts map to call logs via callerPhone + agentId)
        logs_result = await db.execute(
            select(
                func.count(CallLog.id),
                func.sum(CallLog.durationSeconds),
            ).where(
                CallLog.agentId == camp.agentId,
                CallLog.tenantId == auth.tenant_id,
                CallLog.startedAt >= (camp.createdAt or since),
            )
        )
        row = logs_result.one()
        total_calls, total_sec = (row[0] or 0), float(row[1] or 0)
        total_cost = round(total_sec * COST_PER_SECOND, 4)

        # Count resolved calls via analysis.goalAchieved
        resolved_result = await db.execute(
            select(func.count(CallLog.id)).where(
                CallLog.agentId == camp.agentId,
                CallLog.tenantId == auth.tenant_id,
                CallLog.startedAt >= (camp.createdAt or since),
                CallLog.analysis["goalAchieved"].as_boolean() == True,
            )
        )
        resolved = resolved_result.scalar() or 0
        cost_per_resolved = round(total_cost / resolved, 4) if resolved else None

        rows.append({
            "campaignId": camp.id,
            "campaignName": camp.name,
            "status": camp.status,
            "totalContacts": camp.totalContacts or 0,
            "callsAttempted": total_calls,
            "callsResolved": resolved,
            "resolutionRate": round(resolved / total_calls, 3) if total_calls else 0,
            "estimatedCostUSD": total_cost,
            "costPerResolutionUSD": cost_per_resolved,
        })

    return {"campaigns": rows, "timeRange": timeRange}


@router.get("/export.csv")
async def export_csv(
    timeRange: str = "7d",
    agentId: Optional[str] = None,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Export call log analytics to CSV for tenant reporting."""
    days = _days_from_range(timeRange)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    where = [
        CallLog.tenantId == auth.tenant_id,
        CallLog.startedAt >= since,
    ]
    if agentId and agentId != "all":
        where.append(CallLog.agentId == agentId)

    result = await db.execute(
        select(CallLog).where(*where).order_by(CallLog.startedAt.desc()).limit(5000)
    )
    logs = result.scalars().all()

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "id", "agentId", "callerPhone", "channel",
        "durationSeconds", "startedAt", "rating",
        "sentiment", "goalAchieved", "intent", "summary",
        "recordingUrl", "conversionInferred", "qualifiedInferred",
    ])
    writer.writeheader()
    for log in logs:
        analysis = log.analysis if isinstance(log.analysis, dict) else {}
        ex = log.extractedVariables if isinstance(log.extractedVariables, dict) else {}
        writer.writerow({
            "id": log.id,
            "agentId": log.agentId,
            "callerPhone": log.callerPhone or "",
            "channel": "phone" if log.callerPhone else "chat",
            "durationSeconds": log.durationSeconds or 0,
            "startedAt": log.startedAt.isoformat() if log.startedAt else "",
            "rating": log.rating or 0,
            "sentiment": analysis.get("sentiment", "neutral"),
            "goalAchieved": analysis.get("goalAchieved", False),
            "intent": analysis.get("intent", ""),
            "summary": (analysis.get("summary") or "")[:200],
            "recordingUrl": log.recordingUrl or "",
            "conversionInferred": _infer_conversion(analysis, ex),
            "qualifiedInferred": _infer_qualified_lead(analysis, ex),
        })

    output.seek(0)
    filename = f"voiceflow_calls_{timeRange}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
