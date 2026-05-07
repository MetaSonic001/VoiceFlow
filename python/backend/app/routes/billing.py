"""
/api/billing — Usage, invoices, plan management, cost estimation, and calculator.

Endpoints:
  GET  /api/billing/usage         — Current month usage summary + call history
  GET  /api/billing/invoices      — Past invoices from Stripe
  POST /api/billing/plan          — Switch planType (free → mcp or pro) or upgrade tier
  GET  /api/billing/estimate      — Dynamic cost estimate given duration + providers
  GET  /api/billing/pricing       — Full pricing config for the frontend
  GET  /api/billing/calculator    — Live calculator: calls/day × duration → monthly bill
                                    (fetches rates from pricing_config.yaml; no auth required)
"""
import math
import logging
import os
from typing import Optional

import yaml
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Tenant
from app.services.billing_service import (
    get_current_month_usage,
    get_usage_history,
    MANAGED_RATE_PER_MIN_INR,
    MCP_RATE_PER_MIN_INR,
    PRO_RATE_PER_MIN_INR,
    FREE_TIER_CALL_CAP,
    compute_billed_amount_inr,
    is_owner_tenant,
)

logger = logging.getLogger("voiceflow.billing")
router = APIRouter()

# ── Load pricing config once at module import ─────────────────────────────────

def _load_pricing_yaml() -> dict:
    _here = os.path.dirname(os.path.abspath(__file__))
    # routes/ → app/ → backend/ → pricing_config.yaml
    config_path = os.path.normpath(os.path.join(_here, "..", "..", "pricing_config.yaml"))
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

_PRICING_YAML = _load_pricing_yaml()


# ── GET /api/billing/usage ────────────────────────────────────────────────────

@router.get("/usage")
async def get_usage(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Return current month usage summary and recent call records."""
    summary = await get_current_month_usage(auth.tenant_id, db)
    history = await get_usage_history(auth.tenant_id, db, limit=50)

    # Attach plan info
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()

    plan_info = {}
    if tenant:
        plan_info = {
            "planType": tenant.planType,
            "planTier": tenant.planTier,
            "managedMinutesBalance": tenant.managedMinutesBalance,
            "stripeCustomerId": tenant.stripeCustomerId,
            "isOwnerAccount": is_owner_tenant(auth.tenant_id),
        }

    return {
        "summary": summary,
        "plan": plan_info,
        "recentCalls": history,
    }


# ── GET /api/billing/invoices ─────────────────────────────────────────────────

@router.get("/invoices")
async def get_invoices(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Return past invoices from Stripe for this tenant."""
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant or not tenant.stripeCustomerId:
        return {"invoices": [], "message": "No payment method on file"}

    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        return {"invoices": [], "message": "Stripe not configured"}

    try:
        import stripe  # type: ignore
        stripe.api_key = stripe_key
        inv_list = stripe.Invoice.list(customer=tenant.stripeCustomerId, limit=24)
        invoices = [
            {
                "id": inv.id,
                "number": inv.number,
                "status": inv.status,
                "amount_due": inv.amount_due / 100,  # cents → rupees/dollars
                "currency": inv.currency.upper(),
                "period_start": inv.period_start,
                "period_end": inv.period_end,
                "invoice_pdf": inv.invoice_pdf,
                "hosted_invoice_url": inv.hosted_invoice_url,
            }
            for inv in inv_list.auto_paging_iter()
        ]
        return {"invoices": invoices}
    except Exception as exc:
        logger.warning("Failed to fetch Stripe invoices for tenant %s: %s", auth.tenant_id, exc)
        return {"invoices": [], "error": "Failed to fetch invoices"}


# ── POST /api/billing/plan ────────────────────────────────────────────────────

@router.post("/plan")
async def update_plan(
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Switch the tenant's plan type or tier.

    Body:
      planType: "mcp" | "pro" | "free"
        mcp = Managed Cloud Plan (₹3.5/min all-in; VoiceFlow holds API keys)
        pro = BYOK + Platform Fee (₹2/min orchestration; customer holds own keys)
        free = default (2 agents, 20 test calls)
      planTier: for mcp: "payg" | "pilot"
               for pro: "free" | "starter" | "growth" | "scale"
      stripePaymentMethodId: (optional) — attach payment method when switching to mcp/pro
    """
    body = await request.json()
    new_plan_type = body.get("planType")
    new_tier = body.get("planTier")
    payment_method_id = body.get("stripePaymentMethodId")

    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return JSONResponse({"error": "Tenant not found"}, status_code=404)

    if new_plan_type in ("mcp", "pro", "free", "managed"):
        tenant.planType = new_plan_type

    if new_tier:
        tenant.planTier = new_tier

    # If switching to mcp or pro and payment method provided, create/update Stripe customer
    if new_plan_type in ("mcp", "managed", "pro") and payment_method_id:
        stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
        if stripe_key:
            try:
                import stripe  # type: ignore
                stripe.api_key = stripe_key

                if not tenant.stripeCustomerId:
                    customer = stripe.Customer.create(
                        metadata={"tenantId": auth.tenant_id},
                        payment_method=payment_method_id,
                        invoice_settings={"default_payment_method": payment_method_id},
                    )
                    tenant.stripeCustomerId = customer.id
                else:
                    stripe.PaymentMethod.attach(payment_method_id, customer=tenant.stripeCustomerId)
                    stripe.Customer.modify(
                        tenant.stripeCustomerId,
                        invoice_settings={"default_payment_method": payment_method_id},
                    )
            except Exception as exc:
                logger.warning("Stripe customer setup failed: %s", exc)
                return JSONResponse({"error": f"Stripe error: {exc}"}, status_code=400)

    await db.commit()
    return {
        "success": True,
        "planType": tenant.planType,
        "planTier": tenant.planTier,
        "stripeCustomerId": tenant.stripeCustomerId,
    }


# ── GET /api/billing/estimate ─────────────────────────────────────────────────

@router.get("/estimate")
async def cost_estimate(
    duration_minutes: float = 10.0,
    providers: str = "groq_70b,sarvam_stt,edge_tts,exotel_inbound",
    plan_type: str = "mcp",
):
    """
    Dynamic cost estimate for the given parameters.
    Does NOT require authentication — used on the pricing/signup page.

    ?duration_minutes=10&providers=groq_70b,sarvam_stt,edge_tts,exotel_inbound&plan_type=mcp
    plan_type: mcp (₹3.5/min) | pro (₹2/min) | free (₹0)
    """
    duration_seconds = int(duration_minutes * 60)
    provider_list = [p.strip() for p in providers.split(",") if p.strip()]

    raw_cost, billed = compute_billed_amount_inr(duration_seconds, provider_list, plan_type)
    billed_minutes = math.ceil(duration_seconds / 60)

    rate = MCP_RATE_PER_MIN_INR if plan_type in ("mcp", "managed") else (
        PRO_RATE_PER_MIN_INR if plan_type == "pro" else 0
    )

    return {
        "duration_minutes": round(duration_minutes, 2),
        "billed_minutes": billed_minutes,
        "providers": provider_list,
        "plan_type": plan_type,
        "raw_cost_inr": raw_cost,
        "billed_inr": billed,
        "rate_per_minute_inr": rate,
        "note": (
            "MCP plan: ₹3.5/min all-inclusive (no keys needed)." if plan_type in ("mcp", "managed") else
            "Pro plan: ₹2/min orchestration fee only. You pay your own providers."
            if plan_type == "pro" else
            "Free plan: 0 charges (20 test calls max)."
        ),
    }


# ── GET /api/billing/calculator ───────────────────────────────────────────────

@router.get("/calculator")
async def pricing_calculator(
    calls_per_day: float = 100.0,
    avg_duration_seconds: float = 120.0,
    plan_type: str = "mcp",
    days_per_month: int = 26,
):
    """
    Monthly cost calculator — no auth required (public pricing page).

    ?calls_per_day=100&avg_duration_seconds=120&plan_type=mcp&days_per_month=26

    Returns monthly estimates for both MCP and Pro plans so the
    frontend can show a side-by-side comparison.
    """
    total_calls_month = calls_per_day * days_per_month
    total_seconds_month = total_calls_month * avg_duration_seconds
    total_minutes_month = math.ceil(total_seconds_month / 60)

    # MCP: ₹3.5/min all-inclusive
    mcp_monthly_inr = round(total_minutes_month * MCP_RATE_PER_MIN_INR, 2)
    # Pro: ₹2/min orchestration (customer also pays ~₹1.85/min to providers separately)
    pro_monthly_inr = round(total_minutes_month * PRO_RATE_PER_MIN_INR, 2)
    # Competitor comparison
    bolna_monthly_inr = round(total_minutes_month * 7.0, 2)   # Bolna ~₹7/min
    retell_monthly_inr = round(total_minutes_month * 19.0, 2)  # Retell ~$0.12/min × 84 + tele

    return {
        "inputs": {
            "calls_per_day": calls_per_day,
            "avg_duration_seconds": avg_duration_seconds,
            "days_per_month": days_per_month,
        },
        "totals": {
            "total_calls_month": int(total_calls_month),
            "total_minutes_month": total_minutes_month,
        },
        "plans": {
            "voiceflow_mcp": {
                "name": "VoiceFlow MCP (Managed Cloud)",
                "description": "No API keys needed. VoiceFlow handles everything.",
                "monthly_inr": mcp_monthly_inr,
                "monthly_usd": round(mcp_monthly_inr / 84, 2),
                "rate_per_min_inr": MCP_RATE_PER_MIN_INR,
                "includes": "Groq LLM + Sarvam STT + Edge TTS + Exotel telephony",
                "pilot": "First 30 days free",
            },
            "voiceflow_pro": {
                "name": "VoiceFlow Pro (BYOK)",
                "description": "Bring your own Groq + Exotel keys. Pay just for orchestration.",
                "monthly_inr": pro_monthly_inr,
                "monthly_usd": round(pro_monthly_inr / 84, 2),
                "rate_per_min_inr": PRO_RATE_PER_MIN_INR,
                "plus_provider_cost_estimate_inr": round(total_minutes_month * 1.85, 2),
                "note": "You also pay providers directly (~₹1.85/min raw cost)",
            },
        },
        "competitors": {
            "bolna": {"monthly_inr": bolna_monthly_inr, "rate_per_min_inr": 7.0},
            "retell": {"monthly_inr": retell_monthly_inr, "rate_per_min_inr": 19.0},
        },
        "savings_vs_bolna_inr": max(0, bolna_monthly_inr - mcp_monthly_inr),
        "savings_vs_retell_inr": max(0, retell_monthly_inr - mcp_monthly_inr),
        "rate_source": "pricing_config.yaml",
    }


# ── GET /api/billing/pricing ──────────────────────────────────────────────────

@router.get("/pricing")
async def get_pricing():
    """Return the full pricing config (no auth required — used on public pricing page)."""
    if not _PRICING_YAML:
        return JSONResponse({"error": "Pricing config not available"}, status_code=500)

    return {
        "mcp_plan": _PRICING_YAML.get("mcp_plan", {}),
        "pro_plan": _PRICING_YAML.get("pro_plan", {}),
        "free_tier": _PRICING_YAML.get("free_tier", {}),
        "addons": _PRICING_YAML.get("addons", {}),
        "effective_per_minute_inr_mcp": _PRICING_YAML.get("effective_per_minute_inr_mcp", 3.5),
        "effective_per_minute_inr_pro": _PRICING_YAML.get("effective_per_minute_inr_pro", 2.0),
        "last_updated": _PRICING_YAML.get("last_updated"),
    }
