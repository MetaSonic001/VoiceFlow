"""
A/B Testing routes — variant cloning, 50/50 traffic splitting, results.

All A/B metrics are stored in Redis (db=5) to avoid schema changes.
Redis key patterns:
  ab:variant:{variant_id}:config   — JSON config for a variant
  ab:campaign:{campaign_id}:split  — JSON {a: variant_id_a, b: variant_id_b}
  ab:variant:{variant_id}:stats    — JSON {calls, conversions, duration_sum, escalations, sentiment_sum}
"""
from __future__ import annotations

import json
import logging
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.config import settings
from app.database import get_db
from app.models import Agent, Campaign

logger = logging.getLogger("voiceflow.ab_testing")

router = APIRouter(prefix="/api/ab", tags=["ab-testing"])

_AB_REDIS_DB = 5
_WINNER_MIN_CALLS = 100        # calls per variant before auto-promotion
_WINNER_MIN_DIFF = 0.10        # 10% conversion rate difference


# ── Redis helper ──────────────────────────────────────────────────────────────

async def _get_redis() -> aioredis.Redis:
    return aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=_AB_REDIS_DB,
        decode_responses=True,
    )


# ── POST /api/ab/agents/{id}/variant ─────────────────────────────────────────

@router.post("/agents/{id}/variant")
async def create_agent_variant(
    id: str,
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Clone an agent with one or more changed fields.
    Body: { "changes": {"systemPrompt": "...", "name": "Variant B"} }
    Returns: { "variant_id": "...", "original_id": "..." }
    """
    body = await request.json()
    changes = body.get("changes", {}) if isinstance(body, dict) else {}

    # Fetch original agent
    result = await db.execute(
        select(Agent).where(Agent.id == id, Agent.tenantId == auth.tenant_id)
    )
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Clone
    variant = Agent(
        name=changes.get("name", f"{original.name} (Variant)"),
        description=changes.get("description", original.description),
        systemPrompt=changes.get("systemPrompt", original.systemPrompt),
        status="inactive",
        templateId=original.templateId,
        brandId=original.brandId,
        channels=original.channels,
        telephonyProvider=original.telephonyProvider,
        llmPreferences=changes.get("llmPreferences", original.llmPreferences),
        tokenLimit=original.tokenLimit,
        tenantId=auth.tenant_id,
        userId=auth.user_id,
    )
    db.add(variant)
    await db.commit()
    await db.refresh(variant)

    # Store variant config in Redis
    r = await _get_redis()
    variant_config = {
        "variant_id": variant.id,
        "original_id": id,
        "tenant_id": auth.tenant_id,
        "changes": changes,
    }
    await r.set(f"ab:variant:{variant.id}:config", json.dumps(variant_config))
    await r.close()

    logger.info("[ab] created variant %s from original %s", variant.id, id)
    return {"variant_id": variant.id, "original_id": id}


# ── POST /api/ab/campaigns/{id}/split ────────────────────────────────────────

@router.post("/campaigns/{id}/split")
async def create_campaign_split(
    id: str,
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Configure a 50/50 A/B split for a campaign.
    Body: { "variant_a": "<agent_id>", "variant_b": "<agent_id>" }
    """
    body = await request.json()

    # Verify campaign belongs to tenant
    result = await db.execute(
        select(Campaign).where(Campaign.id == id, Campaign.tenantId == auth.tenant_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    variant_a = body.get("variant_a")
    variant_b = body.get("variant_b")
    if not variant_a or not variant_b:
        raise HTTPException(status_code=400, detail="variant_a and variant_b are required")

    r = await _get_redis()
    split_config = {
        "campaign_id": id,
        "variant_a": variant_a,
        "variant_b": variant_b,
        "split_ratio": 0.5,
    }
    await r.set(f"ab:campaign:{id}:split", json.dumps(split_config))
    # Initialise stats for both variants
    for vid in (variant_a, variant_b):
        if not await r.exists(f"ab:variant:{vid}:stats"):
            await r.set(
                f"ab:variant:{vid}:stats",
                json.dumps({
                    "calls": 0,
                    "conversions": 0,
                    "duration_sum": 0,
                    "escalations": 0,
                    "sentiment_sum": 0.0,
                }),
            )
    await r.close()

    logger.info("[ab] campaign %s split configured: A=%s B=%s", id, variant_a, variant_b)
    return {"campaign_id": id, "variant_a": variant_a, "variant_b": variant_b, "split_ratio": 0.5}


# ── GET /api/ab/campaigns/{id}/results ───────────────────────────────────────

@router.get("/campaigns/{id}/results")
async def get_campaign_results(
    id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Return comparative A/B metrics and (if eligible) auto-winner recommendation.

    Metrics tracked per variant:
      - calls              — total calls made
      - conversions        — contacts that reached a positive outcome
      - avg_call_duration  — mean call duration in seconds
      - escalation_rate    — escalations / calls
      - sentiment_score    — mean sentiment (−1 … +1)
      - conversion_rate    — conversions / calls
    """
    r = await _get_redis()
    split_raw = await r.get(f"ab:campaign:{id}:split")
    if not split_raw:
        await r.close()
        raise HTTPException(status_code=404, detail="No A/B split configured for this campaign")

    split = json.loads(split_raw)
    variant_a = split["variant_a"]
    variant_b = split["variant_b"]

    def _load_stats(raw: str | None) -> dict:
        default = {
            "calls": 0, "conversions": 0, "duration_sum": 0,
            "escalations": 0, "sentiment_sum": 0.0,
        }
        if not raw:
            return default
        try:
            return {**default, **json.loads(raw)}
        except json.JSONDecodeError:
            return default

    stats_a = _load_stats(await r.get(f"ab:variant:{variant_a}:stats"))
    stats_b = _load_stats(await r.get(f"ab:variant:{variant_b}:stats"))
    await r.close()

    def _metrics(stats: dict) -> dict:
        calls = max(stats["calls"], 1)
        return {
            "calls": stats["calls"],
            "conversion_rate": round(stats["conversions"] / calls, 4),
            "avg_call_duration": round(stats["duration_sum"] / calls, 1),
            "escalation_rate": round(stats["escalations"] / calls, 4),
            "sentiment_score": round(stats["sentiment_sum"] / calls, 4),
        }

    metrics_a = _metrics(stats_a)
    metrics_b = _metrics(stats_b)

    # Auto-winner logic
    winner = None
    if stats_a["calls"] >= _WINNER_MIN_CALLS and stats_b["calls"] >= _WINNER_MIN_CALLS:
        diff = metrics_a["conversion_rate"] - metrics_b["conversion_rate"]
        if abs(diff) >= _WINNER_MIN_DIFF:
            winner = variant_a if diff > 0 else variant_b
            logger.info(
                "[ab] auto-winner for campaign %s: variant %s (diff=%.2f%%)",
                id, winner, diff * 100,
            )

    return {
        "campaign_id": id,
        "variant_a": {"id": variant_a, **metrics_a},
        "variant_b": {"id": variant_b, **metrics_b},
        "auto_winner": winner,
        "eligible_for_promotion": (
            stats_a["calls"] >= _WINNER_MIN_CALLS and stats_b["calls"] >= _WINNER_MIN_CALLS
        ),
    }


# ── Helper: record a call result for A/B tracking ────────────────────────────

async def record_ab_call(
    campaign_id: str,
    variant_id: str,
    converted: bool = False,
    duration_seconds: float = 0,
    escalated: bool = False,
    sentiment: float = 0.0,
) -> None:
    """Update Redis stats for a completed call in an A/B test. Fire-and-forget."""
    try:
        r = await _get_redis()
        key = f"ab:variant:{variant_id}:stats"
        raw = await r.get(key)
        stats = json.loads(raw) if raw else {
            "calls": 0, "conversions": 0, "duration_sum": 0,
            "escalations": 0, "sentiment_sum": 0.0,
        }
        stats["calls"] += 1
        stats["conversions"] += int(converted)
        stats["duration_sum"] += duration_seconds
        stats["escalations"] += int(escalated)
        stats["sentiment_sum"] += sentiment
        await r.set(key, json.dumps(stats))
        await r.close()
    except Exception:
        logger.exception("[ab] failed to record call for variant %s", variant_id)
