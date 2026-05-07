"""
VoiceFlow Billing Service
=========================
Handles metered billing for MCP and Pro plan tenants.

Two-tier model:
  MCP (Managed Cloud Plan)  — ₹3.5/min all-inclusive. VoiceFlow holds API keys.
                               Loss leader to acquire SMB customers fast.
  Pro (BYOK + Platform Fee) — ₹2/min orchestration fee only. ~100% gross margin.
                               Customer holds their own Groq + Exotel/Twilio keys.
  Free                      — 2 agents, 20 test calls, card required for 21st.
  Pilot                     — First 30 days free (MCP cost absorbed as CAC).

Stripe integration:
  MCP: Stripe Billing Meter event fired per call (voice_minutes meter)
  Pro: Same metering for orchestration fee
  Pilot / Owner: always bypassed
"""
import math
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import yaml
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Tenant, UsageLog

logger = logging.getLogger("voiceflow.billing")

# ── Owner bypass ──────────────────────────────────────────────────────────────
# Comma-separated tenant IDs that are never billed (owner / internal accounts).
_raw_owner_ids = os.getenv("OWNER_TENANT_IDS", "")
OWNER_TENANT_IDS: set[str] = {t.strip() for t in _raw_owner_ids.split(",") if t.strip()}


# ── Load pricing config ───────────────────────────────────────────────────────

def _load_pricing() -> dict:
    """Load pricing_config.yaml from the same directory as this package root."""
    _here = os.path.dirname(os.path.abspath(__file__))
    # services/ → app/ → backend/ → pricing_config.yaml
    config_path = os.path.join(_here, "..", "..", "pricing_config.yaml")
    config_path = os.path.normpath(config_path)
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning("Could not load pricing_config.yaml: %s — using hardcoded defaults", e)
        return {}


_PRICING = _load_pricing()

# ── Provider cost constants (INR) ─────────────────────────────────────────────
# These are the platform's *raw* costs (before markup).
# Computed from pricing_config.yaml; hardcoded fallbacks keep billing safe
# if the YAML is missing.

_USD_TO_INR = float((_PRICING or {}).get("usd_to_inr", 84.0))
_MARKUP = float((_PRICING or {}).get("platform_markup", 2.5))

# ── Provider raw costs (what VoiceFlow actually pays on MCP plan) ─────────────
# Groq: ~1000 tokens/turn (800 in + 200 out), 70b model, ~4 turns/min
_GROQ_70B_PER_MIN_INR: float = (
    ((800 * 0.59 + 200 * 0.79) / 1_000_000) * _USD_TO_INR * 4
)
_GROQ_8B_PER_MIN_INR: float = (
    ((800 * 0.05 + 200 * 0.08) / 1_000_000) * _USD_TO_INR * 4
)

# Sarvam STT: $0.000092/second → INR
_SARVAM_STT_PER_SEC_INR: float = 0.000092 * _USD_TO_INR
# Sarvam TTS: ~600 chars per turn, 4 turns/min
_SARVAM_TTS_PER_MIN_INR: float = (0.0000165 * 600 * 4) * _USD_TO_INR
# Edge TTS (CPU-local via Microsoft Edge): free
_EDGE_TTS_PER_MIN_INR: float = 0.0

# Exotel inbound (India)
_EXOTEL_INBOUND_PER_MIN_INR: float = 0.50
_EXOTEL_OUTBOUND_PER_MIN_INR: float = 0.80

# Twilio India (fallback / international customers)
_TWILIO_INBOUND_PER_MIN_INR: float = 1.40
_TWILIO_OUTBOUND_PER_MIN_INR: float = 1.60

# ── Tier billing rates ────────────────────────────────────────────────────────
# MCP: ₹3.5/min all-inclusive (loss leader; ~75–85% gross margin)
MCP_RATE_PER_MIN_INR: float = float(
    (_PRICING or {}).get("effective_per_minute_inr_mcp", 3.5)
)
# Pro: ₹2/min orchestration fee only (~100% margin; customer pays providers)
PRO_RATE_PER_MIN_INR: float = float(
    (_PRICING or {}).get("effective_per_minute_inr_pro", 2.0)
)
# Backward-compat alias used by billing router
MANAGED_RATE_PER_MIN_INR: float = MCP_RATE_PER_MIN_INR
MANAGED_RATE_PER_MIN_USD: float = 0.042  # MCP rate in USD

# Free-tier call cap (card required after N calls)
FREE_TIER_CALL_CAP: int = 20


# ── Cost calculator ───────────────────────────────────────────────────────────

def _compute_raw_cost_inr(
    duration_seconds: int,
    providers_used: list[str],
) -> float:
    """
    Compute the raw platform cost in INR for a completed call.
    `providers_used` is a list of provider keys, e.g.:
      ["groq_70b", "sarvam_stt", "edge_tts", "exotel_inbound"]
    """
    minutes = duration_seconds / 60.0  # fractional minutes for accurate costing

    cost = 0.0

    for provider in providers_used:
        p = provider.lower()
        if p == "groq_70b":
            cost += _GROQ_70B_PER_MIN_INR * minutes
        elif p == "groq_8b":
            cost += _GROQ_8B_PER_MIN_INR * minutes
        elif p == "sarvam_stt":
            cost += _SARVAM_STT_PER_SEC_INR * duration_seconds
        elif p == "sarvam_tts":
            cost += _SARVAM_TTS_PER_MIN_INR * minutes
        elif p == "edge_tts":
            cost += 0.0
        elif p == "exotel_inbound":
            cost += _EXOTEL_INBOUND_PER_MIN_INR * minutes
        elif p == "exotel_outbound":
            cost += _EXOTEL_OUTBOUND_PER_MIN_INR * minutes
        elif p == "twilio_inbound":
            cost += _TWILIO_INBOUND_PER_MIN_INR * minutes
        elif p == "twilio_outbound":
            cost += _TWILIO_OUTBOUND_PER_MIN_INR * minutes

    return round(cost, 4)


def compute_billed_amount_inr(
    duration_seconds: int,
    providers_used: list[str],
    plan_type: str = "mcp",
) -> tuple[float, float]:
    """
    Returns (raw_cost_inr, billed_to_tenant_inr).

    MCP plan: billed = ceiling(duration_seconds / 60) × MCP_RATE_PER_MIN_INR (₹3.5)
    Pro plan: billed = ceiling(duration_seconds / 60) × PRO_RATE_PER_MIN_INR (₹2)
              raw_cost = 0 (customer pays their own providers)
    Free / pilot: billed = 0
    """
    raw_cost = _compute_raw_cost_inr(duration_seconds, providers_used)
    billed_minutes = math.ceil(duration_seconds / 60)

    if plan_type == "mcp" or plan_type == "managed":
        billed = round(billed_minutes * MCP_RATE_PER_MIN_INR, 2)
    elif plan_type == "pro":
        raw_cost = 0.0   # customer pays providers; VoiceFlow charges orchestration only
        billed = round(billed_minutes * PRO_RATE_PER_MIN_INR, 2)
    else:
        billed = 0.0

    return raw_cost, billed


# ── Owner bypass check ────────────────────────────────────────────────────────

def is_owner_tenant(tenant_id: str) -> bool:
    """Return True if this tenant ID is in OWNER_TENANT_IDS (never billed)."""
    return tenant_id in OWNER_TENANT_IDS


async def should_bill(tenant_id: str, db: AsyncSession) -> bool:
    """
    Return True only if this tenant should be billed via Stripe.

    Suppressed when:
    - Tenant is in OWNER_TENANT_IDS
    - Tenant planType is 'free' (20-call cap, no Stripe involvement)
    - Tenant is within their pilot window (first 30 days free)
    - Tenant has no stripeCustomerId (payment not set up)
    """
    if is_owner_tenant(tenant_id):
        return False

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return False

    if tenant.planType == "free":
        return False

    # Pilot window: MCP or Pro tenants within first 30 free days
    if tenant.planTier == "pilot" and tenant.pilotPlanEndDate:
        if datetime.now(timezone.utc) < tenant.pilotPlanEndDate:
            logger.info("Pilot bypass for tenant %s (pilot ends %s)", tenant_id, tenant.pilotPlanEndDate)
            return False

    if tenant.planType not in ("mcp", "managed", "pro"):
        return False

    # Require a valid Stripe customer ID before billing
    if not tenant.stripeCustomerId:
        logger.warning("Billable tenant %s has no stripeCustomerId — skipping", tenant_id)
        return False

    return True


# ── Stripe meter event ────────────────────────────────────────────────────────

async def fire_stripe_meter_event(
    tenant: Tenant,
    billed_minutes: int,
) -> Optional[str]:
    """
    Send a Stripe Billing Meter event for `billed_minutes` consumed.
    Returns the Stripe event ID on success, None on failure.
    """
    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    meter_id = os.getenv("STRIPE_VOICE_MINUTES_METER_ID", "")

    if not stripe_key or not meter_id or not tenant.stripeCustomerId:
        return None

    try:
        import stripe  # type: ignore
        import uuid as _uuid
        stripe.api_key = stripe_key

        event = stripe.billing.MeterEvent.create(
            event_name=meter_id,
            payload={
                "stripe_customer_id": tenant.stripeCustomerId,
                "value": str(billed_minutes),
            },
            identifier=f"vf-{tenant.id}-{_uuid.uuid4().hex}",  # idempotency key
        )
        return event.get("identifier") or event.get("id")
    except Exception as e:
        logger.warning("Stripe meter event failed for tenant %s: %s", tenant.id, e)
        return None


# ── Main entry point ──────────────────────────────────────────────────────────

async def log_call_usage(
    tenant_id: str,
    call_log_id: Optional[str],
    duration_seconds: int,
    providers_used: Optional[list[str]] = None,
) -> Optional[UsageLog]:
    """
    Called at call-end. Computes cost, persists UsageLog, fires Stripe event.

    providers_used defaults to the typical managed stack if not provided:
      ["groq_70b", "sarvam_stt", "edge_tts", "exotel_inbound"]

    Safe to call from background tasks — opens its own DB session.
    """
    if duration_seconds <= 0:
        return None

    if providers_used is None:
        providers_used = ["groq_70b", "sarvam_stt", "edge_tts", "exotel_inbound"]

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            logger.warning("log_call_usage: tenant %s not found", tenant_id)
            return None

        plan_type = tenant.planType or "free"
        # Atomically increment the tenant's lifetime call count (race-safe UPDATE)
        from sqlalchemy import update as sa_update
        await db.execute(
            sa_update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(totalCallCount=Tenant.totalCallCount + 1)
        )
        await db.flush()

        raw_cost, billed = compute_billed_amount_inr(
            duration_seconds, providers_used, plan_type
        )

        stripe_event_id: Optional[str] = None

        # Only fire Stripe meter for managed tenants with billing set up
        bill = await should_bill(tenant_id, db)
        if bill:
            billed_minutes = math.ceil(duration_seconds / 60)
            stripe_event_id = await fire_stripe_meter_event(tenant, billed_minutes)

        usage = UsageLog(
            tenantId=tenant_id,
            callLogId=call_log_id,
            durationSeconds=duration_seconds,
            providersUsed=",".join(providers_used),
            costRupees=raw_cost,
            billedRupees=billed,
            stripeEventId=stripe_event_id,
        )
        db.add(usage)
        await db.commit()
        await db.refresh(usage)

        logger.info(
            "UsageLog created: tenant=%s call=%s dur=%ds cost=₹%.4f billed=₹%.2f stripe=%s",
            tenant_id, call_log_id, duration_seconds, raw_cost, billed, stripe_event_id or "n/a"
        )
        return usage


# ── Dashboard aggregation ─────────────────────────────────────────────────────

async def get_current_month_usage(tenant_id: str, db: AsyncSession) -> dict:
    """
    Aggregate usage for the current calendar month.
    Returns a dict suitable for the billing dashboard API.
    """
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    rows = await db.execute(
        select(
            sqlfunc.count(UsageLog.id).label("call_count"),
            sqlfunc.sum(UsageLog.durationSeconds).label("total_seconds"),
            sqlfunc.sum(UsageLog.costRupees).label("total_cost_inr"),
            sqlfunc.sum(UsageLog.billedRupees).label("total_billed_inr"),
        ).where(
            UsageLog.tenantId == tenant_id,
            UsageLog.createdAt >= month_start,
        )
    )
    row = rows.one()

    total_seconds = int(row.total_seconds or 0)
    return {
        "period": now.strftime("%B %Y"),
        "call_count": int(row.call_count or 0),
        "total_minutes": round(total_seconds / 60, 1),
        "total_cost_inr": round(float(row.total_cost_inr or 0), 2),
        "total_billed_inr": round(float(row.total_billed_inr or 0), 2),
        "currency": "INR",
    }


async def get_usage_history(
    tenant_id: str,
    db: AsyncSession,
    limit: int = 100,
) -> list[dict]:
    """Return recent UsageLog rows for the billing page call table."""
    result = await db.execute(
        select(UsageLog)
        .where(UsageLog.tenantId == tenant_id)
        .order_by(UsageLog.createdAt.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": u.id,
            "callLogId": u.callLogId,
            "durationSeconds": u.durationSeconds,
            "durationMinutes": round(u.durationSeconds / 60, 2),
            "providersUsed": u.providersUsed,
            "costRupees": u.costRupees,
            "billedRupees": u.billedRupees,
            "stripeEventId": u.stripeEventId,
            "createdAt": u.createdAt.isoformat() if u.createdAt else None,
        }
        for u in logs
    ]
