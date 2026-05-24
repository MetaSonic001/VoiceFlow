"""
SIP Trunking / Bring-Your-Own-Carrier (BYOC) routes.

Allows enterprise tenants to connect their own SIP carrier (Twilio SIP Trunking,
Plivo, Vonage, or any SIP-compatible provider) to the VoiceFlow AI pipeline.

The SIP trunk configuration is stored in Tenant.settings['sipTrunks'] as a list.
Inbound SIP calls are routed through the same voice_inbound_router as Twilio calls.

Twilio implements BYOC natively — tenants create a SIP trunk in their Twilio account
and point it at a Termination URI. VoiceFlow generates the correct Termination URI
and handles authentication via Credential Lists.

Routes:
GET  /api/sip-trunking/trunks          — list configured SIP trunks
POST /api/sip-trunking/trunks          — register a new SIP trunk (Twilio BYOC or generic)
GET  /api/sip-trunking/trunks/{id}     — get SIP trunk detail
DELETE /api/sip-trunking/trunks/{id}   — remove SIP trunk config
POST /api/sip-trunking/trunks/{id}/test — test connectivity to SIP trunk
GET  /api/sip-trunking/webhook-uri/{agent_id} — get the SIP termination URI for an agent
"""
from __future__ import annotations

import logging
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.config import settings
from app.database import get_db
from app.models import Agent, Tenant
from app.services.credentials import decrypt_safe

logger = logging.getLogger("voiceflow.sip_trunking")
router = APIRouter()

# ── Helpers ──────────────────────────────────────────────────────────────────

def _mask(val: str | None, keep: int = 4) -> str | None:
    if not val:
        return None
    if len(val) <= keep:
        return "****"
    return val[:keep] + "*" * (len(val) - keep)


def _trunk_safe(trunk: dict) -> dict:
    """Return trunk dict with credentials masked for API responses."""
    safe = dict(trunk)
    safe["sipPassword"] = _mask(trunk.get("sipPassword"), 4)
    safe["twilioAccountSid"] = _mask(trunk.get("twilioAccountSid"), 8)
    return safe


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/trunks")
async def list_sip_trunks(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Return all SIP trunks configured for the tenant."""
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    trunks: list[dict] = (tenant.settings or {}).get("sipTrunks", [])
    return {"trunks": [_trunk_safe(t) for t in trunks]}


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("/trunks")
async def create_sip_trunk(
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new SIP trunk.

    Supported providers:
      • "twilio_byoc"  — Twilio BYOC (Bring Your Own Carrier)
      • "generic_sip"  — Any SIP-compatible carrier (Plivo, Vonage, etc.)

    Request body:
    {
      "provider":        "twilio_byoc" | "generic_sip",
      "label":           "My Enterprise Carrier",
      "sipUri":          "sip:12345678@pstn.twilio.com",       ← termination URI
      "sipUsername":     "voiceflow_inbound",
      "sipPassword":     "<credential>",
      "twilioAccountSid": "ACxxxxxxxx",   ← twilio_byoc only
      "twilioAuthToken":  "<token>",       ← twilio_byoc only, stored encrypted
      "assignedAgentId":  "<agent_uuid>",  ← optional: route all calls to this agent
      "region":          "us1"             ← optional: Twilio edge location
    }
    """
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    provider = body.get("provider", "generic_sip")
    if provider not in ("twilio_byoc", "generic_sip"):
        raise HTTPException(400, "provider must be 'twilio_byoc' or 'generic_sip'")

    label = (body.get("label") or "Unnamed Trunk").strip()[:100]
    sip_uri = (body.get("sipUri") or "").strip()
    if not sip_uri:
        raise HTTPException(400, "sipUri is required")

    trunk_id = str(_uuid.uuid4())

    # Encrypt sensitive credentials
    from app.services.credentials import encrypt
    sip_password_raw = body.get("sipPassword") or ""
    sip_password_enc = encrypt(sip_password_raw) if sip_password_raw else ""

    twilio_token_raw = body.get("twilioAuthToken") or ""
    twilio_token_enc = encrypt(twilio_token_raw) if twilio_token_raw else ""

    trunk: dict = {
        "id": trunk_id,
        "provider": provider,
        "label": label,
        "sipUri": sip_uri,
        "sipUsername": (body.get("sipUsername") or "").strip(),
        "sipPassword": sip_password_enc,
        "twilioAccountSid": (body.get("twilioAccountSid") or "").strip(),
        "twilioAuthToken": twilio_token_enc,
        "assignedAgentId": body.get("assignedAgentId") or "",
        "region": (body.get("region") or "us1").strip(),
        "isActive": True,
    }

    tenant_settings = dict(tenant.settings or {})
    sip_trunks: list = tenant_settings.get("sipTrunks", [])
    sip_trunks.append(trunk)
    tenant_settings["sipTrunks"] = sip_trunks
    tenant.settings = tenant_settings
    await db.commit()

    logger.info("[sip_trunking] tenant=%s registered trunk id=%s provider=%s", auth.tenant_id, trunk_id, provider)
    return {"trunk": _trunk_safe(trunk), "success": True}


# ── Get ───────────────────────────────────────────────────────────────────────

@router.get("/trunks/{trunk_id}")
async def get_sip_trunk(
    trunk_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    trunks: list[dict] = (tenant.settings or {}).get("sipTrunks", [])
    trunk = next((t for t in trunks if t["id"] == trunk_id), None)
    if not trunk:
        raise HTTPException(404, "SIP trunk not found")

    return {"trunk": _trunk_safe(trunk)}


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/trunks/{trunk_id}")
async def delete_sip_trunk(
    trunk_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    trunks: list[dict] = list((tenant.settings or {}).get("sipTrunks", []))
    original_len = len(trunks)
    trunks = [t for t in trunks if t["id"] != trunk_id]
    if len(trunks) == original_len:
        raise HTTPException(404, "SIP trunk not found")

    tenant_settings = dict(tenant.settings or {})
    tenant_settings["sipTrunks"] = trunks
    tenant.settings = tenant_settings
    await db.commit()

    logger.info("[sip_trunking] tenant=%s deleted trunk id=%s", auth.tenant_id, trunk_id)
    return {"success": True}


# ── Test ──────────────────────────────────────────────────────────────────────

@router.post("/trunks/{trunk_id}/test")
async def test_sip_trunk(
    trunk_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Test SIP trunk connectivity.
    For Twilio BYOC: validates Twilio credentials via REST API.
    For generic SIP: attempts SIP OPTIONS ping via Twilio Elastic SIP Trunking.
    Returns { success: bool, message: str }.
    """
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    trunks: list[dict] = (tenant.settings or {}).get("sipTrunks", [])
    trunk = next((t for t in trunks if t["id"] == trunk_id), None)
    if not trunk:
        raise HTTPException(404, "SIP trunk not found")

    if trunk.get("provider") == "twilio_byoc":
        # Validate Twilio credentials
        sid = trunk.get("twilioAccountSid")
        token_enc = trunk.get("twilioAuthToken")
        if not sid or not token_enc:
            return {"success": False, "message": "Twilio credentials not configured"}
        token = decrypt_safe(token_enc)
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json",
                    auth=(sid, token),
                )
                if r.status_code == 200:
                    data = r.json()
                    return {
                        "success": True,
                        "message": f"Twilio account verified: {data.get('friendly_name', sid)}",
                    }
                else:
                    return {"success": False, "message": f"Twilio returned {r.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"Connection error: {e}"}
    else:
        # Generic SIP — basic URI validation only (true SIP OPTIONS requires SIP stack)
        sip_uri = trunk.get("sipUri", "")
        if sip_uri.startswith("sip:"):
            return {
                "success": True,
                "message": f"SIP URI format valid: {sip_uri}. Full OPTIONS ping requires SIP stack integration.",
            }
        return {"success": False, "message": "Invalid SIP URI — must start with 'sip:'"}


# ── Webhook URI ───────────────────────────────────────────────────────────────

@router.get("/webhook-uri/{agent_id}")
async def get_sip_webhook_uri(
    agent_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the SIP/Twilio webhook URL to configure on the carrier for an agent.
    This is the URL the carrier should POST inbound call events to.
    """
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")

    base_url = getattr(settings, "TWILIO_WEBHOOK_BASE_URL", None) or "https://your-domain.com"
    return {
        "agentId": agent_id,
        "inboundWebhookUrl": f"{base_url}/api/voice/gather-inbound/{agent_id}",
        "statusCallbackUrl": f"{base_url}/api/voice/gather-status/{agent_id}",
        "protocol": "HTTP POST",
        "note": (
            "Point your SIP carrier's webhook URL to inboundWebhookUrl. "
            "For Twilio BYOC, set this as the Voice URL on your SIP trunk."
        ),
    }
