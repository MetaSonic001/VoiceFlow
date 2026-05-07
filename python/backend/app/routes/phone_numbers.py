"""
Phone Numbers Shop — buy, manage, and assign phone numbers in-platform.

Supports:
  • Twilio — international numbers (local, toll-free, mobile)
  • Exotel — India PSTN numbers (Exophones / DIDs)

Exotel Number Shop endpoints:
  GET  /api/phone-numbers/exotel/available           — list available Indian numbers
  POST /api/phone-numbers/exotel/purchase            — purchase an Exophone
  POST /api/phone-numbers/exotel/{number}/configure  — set webhook → agent
  GET  /api/phone-numbers/exotel/owned               — list owned Exophones
  POST /api/phone-numbers/exotel/outbound            — initiate outbound call (campaign use)
  POST /api/phone-numbers/exotel/pilot               — activate 30-day pilot plan

Standard endpoints (Twilio):
  GET  /api/phone-numbers/search           — search available numbers
  GET  /api/phone-numbers/owned            — list numbers owned by this tenant
  POST /api/phone-numbers/purchase         — buy a number
  DELETE /api/phone-numbers/{sid}          — release / delete a number
  POST /api/phone-numbers/{sid}/assign     — assign a number to an agent
  POST /api/phone-numbers/{sid}/unassign   — remove agent assignment

Exotel API base:
  https://api.exotel.com/v1/accounts/{SID}/
  Authentication: HTTP Basic Auth (api_key:api_token)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.config import settings
from app.database import get_db, AsyncSessionLocal
from app.models import Agent, Tenant
from app.services.credentials import decrypt_safe

logger = logging.getLogger("voiceflow.phone_numbers")
router = APIRouter()

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

async def _twilio_creds(tenant: Tenant) -> tuple[str, str] | None:
    """Return (account_sid, auth_token) for this tenant, or None if not configured."""
    s = tenant.settings or {}
    sid = s.get("twilioAccountSid")
    token_enc = s.get("twilioAuthToken")
    if not sid or not token_enc:
        return None
    token = decrypt_safe(token_enc)
    if not token:
        return None
    return sid, token


async def _exotel_creds(tenant: Tenant) -> tuple[str, str, str] | None:
    """Return (sid, api_key, api_token) for Exotel, or None."""
    s = tenant.settings or {}
    sid = s.get("exotelSid")
    key = s.get("exotelApiKey")
    token_enc = s.get("exotelApiToken")
    if not sid or not key or not token_enc:
        return None
    token = decrypt_safe(token_enc)
    if not token:
        return None
    return sid, key, token


# ──────────────────────────────────────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────────────────────────────────────

class PurchaseRequest(BaseModel):
    phone_number: str          # E.164 number to purchase (from search results)
    provider: str = "twilio"   # "twilio" | "exotel"


class AssignRequest(BaseModel):
    agent_id: str


class ExotelPurchaseRequest(BaseModel):
    number: str                 # Exotel DID number (e.g. "07676898XXX")
    activate_pilot: bool = True # auto-activate 30-day free pilot for MCP tenants


class ExotelOutboundRequest(BaseModel):
    agent_id: str
    to: str       # destination phone number (E.164 or Indian 10-digit)
    from_: str    # caller_id — must be one of tenant's Exophones


# ── Platform Exotel credentials fallback ─────────────────────────────────────

async def _exotel_creds_with_fallback(tenant: Tenant) -> tuple[str, str, str] | None:
    """
    Return (sid, api_key, api_token) — first from tenant BYOK settings,
    then from platform env vars (for MCP managed tenants).
    """
    creds = await _exotel_creds(tenant)
    if creds:
        return creds
    # Platform keys fallback (MCP plan — VoiceFlow's own Exotel account)
    sid = settings.PLATFORM_EXOTEL_SID or ""
    key = settings.PLATFORM_EXOTEL_KEY or ""
    token = settings.PLATFORM_EXOTEL_TOKEN or ""
    if sid and key and token:
        return sid, key, token
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Search available numbers
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/search")
async def search_numbers(
    country: str = "US",
    area_code: Optional[str] = None,
    number_type: str = "local",   # local | toll_free | mobile
    limit: int = 20,
    provider: str = "twilio",
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Search available phone numbers from Twilio or Exotel."""
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(403, "Tenant not found")

    if provider == "exotel":
        creds = await _exotel_creds_with_fallback(tenant)
        if not creds:
            raise HTTPException(400, "Exotel credentials not configured. Add them in Settings → API Keys → Exotel.")
        sid, api_key, api_token = creds
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"https://api.exotel.com/v1/accounts/{sid}/available_numbers",
                    auth=(api_key, api_token),
                    params={"country": "IN", "limit": str(min(limit, 50))},
                )
            if resp.status_code == 401:
                raise HTTPException(400, "Invalid Exotel credentials")
            if resp.status_code not in (200, 201):
                # Exotel available_numbers may not be a standard endpoint on all plans;
                # fall back to informational response guiding dashboard provisioning
                return {
                    "numbers": [],
                    "message": "Search your available Exophones at my.exotel.com → Numbers. "
                               "Copy the number here to purchase and assign it to your agent.",
                    "exotel_dashboard": "https://my.exotel.com/numbers",
                }
            data = resp.json()
            numbers = []
            for n in data.get("Numbers", data.get("numbers", [])):
                numbers.append({
                    "phone_number": n.get("PhoneNumber") or n.get("phone_number"),
                    "friendly_name": n.get("PhoneNumber") or n.get("phone_number"),
                    "region": "India",
                    "iso_country": "IN",
                    "number_type": "local",
                    "voice": True,
                    "sms": True,
                    "monthly_price_inr": "₹400",
                    "pilot_note": "First 30 days free for MCP plan customers",
                    "provider": "exotel",
                })
            return {"numbers": numbers, "total": len(numbers)}
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("[phone_numbers] Exotel search error: %s", exc)
            raise HTTPException(502, "Failed to reach Exotel API")

    # Twilio path
    creds = await _twilio_creds(tenant)
    if not creds:
        raise HTTPException(400, "Twilio credentials not configured. Add them in Settings → API Keys → Twilio.")
    sid, token = creds

    country = country.upper()
    type_map = {"local": "Local", "toll_free": "TollFree", "mobile": "Mobile"}
    number_type_path = type_map.get(number_type, "Local")

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/AvailablePhoneNumbers/{country}/{number_type_path}.json"
    params: dict = {"PageSize": str(min(limit, 40))}
    if area_code:
        params["AreaCode"] = area_code

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, auth=(sid, token), params=params)
        if resp.status_code == 401:
            raise HTTPException(400, "Invalid Twilio credentials")
        if resp.status_code == 400:
            detail = resp.json().get("message", "Bad request")
            raise HTTPException(400, f"Twilio: {detail}")
        resp.raise_for_status()
        data = resp.json()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[phone_numbers] search error: %s", exc)
        raise HTTPException(502, "Failed to reach Twilio API")

    numbers = []
    for n in data.get("available_phone_numbers", []):
        caps = n.get("capabilities", {})
        numbers.append({
            "phone_number": n.get("phone_number"),
            "friendly_name": n.get("friendly_name"),
            "region": n.get("region"),
            "city": n.get("locality"),
            "iso_country": n.get("iso_country"),
            "number_type": number_type,
            "voice": caps.get("voice", False),
            "sms": caps.get("SMS", False),
            "mms": caps.get("MMS", False),
            "monthly_price": _price_estimate(number_type, country),
            "provider": "twilio",
        })
    return {"numbers": numbers, "total": len(numbers)}


def _price_estimate(number_type: str, country: str) -> str:
    """Return a rough monthly price estimate string."""
    prices = {
        ("local", "US"): "$1.15", ("local", "GB"): "$1.00", ("local", "IN"): "$0.50",
        ("toll_free", "US"): "$2.15", ("mobile", "US"): "$1.15",
    }
    return prices.get((number_type, country), "~$1–3")


# ──────────────────────────────────────────────────────────────────────────────
# List owned numbers
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/owned")
async def list_owned_numbers(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """List all phone numbers owned/provisioned by this tenant."""
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(403, "Tenant not found")

    twilio_numbers = []
    creds = await _twilio_creds(tenant)
    if creds:
        sid, token = creds
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"https://api.twilio.com/2010-04-01/Accounts/{sid}/IncomingPhoneNumbers.json",
                    auth=(sid, token),
                    params={"PageSize": "100"},
                )
            if resp.status_code == 200:
                # Enrich with agent assignment from our DB
                agent_result = await db.execute(select(Agent).where(Agent.tenantId == auth.tenant_id))
                agents = {a.phoneNumber: a for a in agent_result.scalars().all() if a.phoneNumber}

                for n in resp.json().get("incoming_phone_numbers", []):
                    phone = n.get("phone_number", "")
                    assigned_agent = agents.get(phone)
                    twilio_numbers.append({
                        "sid": n.get("sid"),
                        "phone_number": phone,
                        "friendly_name": n.get("friendly_name"),
                        "capabilities": n.get("capabilities", {}),
                        "date_created": n.get("date_created"),
                        "voice_url": n.get("voice_url"),
                        "provider": "twilio",
                        "assigned_agent_id": assigned_agent.id if assigned_agent else None,
                        "assigned_agent_name": assigned_agent.name if assigned_agent else None,
                    })
        except Exception as exc:
            logger.warning("[phone_numbers] owned list error: %s", exc)

    return {"numbers": twilio_numbers, "total": len(twilio_numbers)}


# ──────────────────────────────────────────────────────────────────────────────
# Purchase a number
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/purchase")
async def purchase_number(
    body: PurchaseRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Buy a phone number from Twilio. Charges your Twilio account."""
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(403, "Tenant not found")

    if body.provider != "twilio":
        raise HTTPException(400, "Only Twilio purchasing is supported via API")

    creds = await _twilio_creds(tenant)
    if not creds:
        raise HTTPException(400, "Twilio credentials not configured")
    sid, token = creds

    # Sanitize phone number: must be E.164
    phone = body.phone_number.strip()
    if not phone.startswith("+"):
        raise HTTPException(400, "Phone number must be in E.164 format (e.g. +14155552671)")

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/IncomingPhoneNumbers.json",
                auth=(sid, token),
                data={"PhoneNumber": phone},
            )
        if resp.status_code == 400:
            detail = resp.json().get("message", "Purchase failed")
            raise HTTPException(400, f"Twilio: {detail}")
        if resp.status_code == 401:
            raise HTTPException(400, "Invalid Twilio credentials")
        resp.raise_for_status()
        purchased = resp.json()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[phone_numbers] purchase error: %s", exc)
        raise HTTPException(502, "Failed to purchase number")

    logger.info("[phone_numbers] tenant=%s purchased %s", auth.tenant_id, phone)
    return {
        "success": True,
        "sid": purchased.get("sid"),
        "phone_number": purchased.get("phone_number"),
        "friendly_name": purchased.get("friendly_name"),
        "message": f"Successfully purchased {phone}",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Release a number
# ──────────────────────────────────────────────────────────────────────────────

@router.delete("/{number_sid}")
async def release_number(
    number_sid: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Release (delete) a Twilio number. Stops billing from Twilio."""
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(403, "Tenant not found")

    creds = await _twilio_creds(tenant)
    if not creds:
        raise HTTPException(400, "Twilio credentials not configured")
    sid, token = creds

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.delete(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/IncomingPhoneNumbers/{number_sid}.json",
                auth=(sid, token),
            )
        if resp.status_code == 404:
            raise HTTPException(404, "Number not found in your Twilio account")
        if resp.status_code not in (200, 204):
            raise HTTPException(400, "Failed to release number")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[phone_numbers] release error: %s", exc)
        raise HTTPException(502, "Error contacting Twilio API")

    # Remove from any agent that had this number assigned (lookup by SID is tricky;
    # instead the frontend should send the E.164 number separately; for now we skip)
    return {"success": True, "message": "Number released successfully"}


# ──────────────────────────────────────────────────────────────────────────────
# Assign / unassign number to agent
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{phone_e164_encoded}/assign")
async def assign_number(
    phone_e164_encoded: str,
    body: AssignRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Assign a phone number to an agent (sets agent.phoneNumber)."""
    from urllib.parse import unquote
    phone = unquote(phone_e164_encoded)

    agent_result = await db.execute(
        select(Agent).where(Agent.id == body.agent_id, Agent.tenantId == auth.tenant_id)
    )
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")

    agent.phoneNumber = phone
    db.add(agent)
    await db.commit()

    logger.info("[phone_numbers] assigned %s → agent %s", phone, body.agent_id)
    return {"success": True, "phone_number": phone, "agent_id": body.agent_id, "agent_name": agent.name}


@router.post("/{phone_e164_encoded}/unassign")
async def unassign_number(
    phone_e164_encoded: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Remove agent assignment from a phone number."""
    from urllib.parse import unquote
    phone = unquote(phone_e164_encoded)

    agent_result = await db.execute(
        select(Agent).where(Agent.phoneNumber == phone, Agent.tenantId == auth.tenant_id)
    )
    agent = agent_result.scalar_one_or_none()
    if agent:
        agent.phoneNumber = None
        db.add(agent)
        await db.commit()

    return {"success": True, "phone_number": phone}


# ══════════════════════════════════════════════════════════════════════════════
# Exotel Number Shop — dedicated endpoints
# ══════════════════════════════════════════════════════════════════════════════

def _exotel_base(sid: str) -> str:
    return f"https://api.exotel.com/v1/accounts/{sid}"


@router.get("/exotel/available")
async def exotel_available_numbers(
    limit: int = 20,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    List available Indian Exophones (DIDs) that can be purchased.
    Uses Exotel's GET /available_numbers API.
    Falls back to guidance message if the endpoint isn't available on the account plan.
    """
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(403, "Tenant not found")

    creds = await _exotel_creds_with_fallback(tenant)
    if not creds:
        raise HTTPException(400, "Exotel not configured. Add credentials in Settings → API Keys.")
    sid, api_key, api_token = creds

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{_exotel_base(sid)}/available_numbers",
                auth=(api_key, api_token),
                params={"country": "IN", "limit": min(limit, 50)},
            )
        if resp.status_code == 401:
            raise HTTPException(400, "Invalid Exotel credentials")
        if resp.status_code == 404:
            return {
                "numbers": [],
                "message": "Browse available Exophones at my.exotel.com → Numbers Shop. "
                           "Once purchased there, use POST /exotel/configure to link them here.",
                "exotel_numbers_shop": "https://my.exotel.com/numbers",
            }
        data = resp.json()
        numbers = [
            {
                "phone_number": n.get("PhoneNumber") or n.get("phone_number"),
                "region": n.get("Region", "India"),
                "number_type": n.get("Type", "mobile"),
                "monthly_price_inr": 150,
                "retail_price_inr": 400,
                "pilot_free_days": 30,
                "provider": "exotel",
            }
            for n in data.get("Numbers", data.get("numbers", []))
        ]
        return {"numbers": numbers, "total": len(numbers)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[exotel] available_numbers error: %s", exc)
        raise HTTPException(502, "Exotel API error")


@router.get("/exotel/owned")
async def exotel_owned_numbers(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """List Exophones already owned by this tenant's Exotel account."""
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(403, "Tenant not found")

    creds = await _exotel_creds_with_fallback(tenant)
    if not creds:
        return {"numbers": [], "message": "Exotel not configured"}
    sid, api_key, api_token = creds

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{_exotel_base(sid)}/phone_numbers",
                auth=(api_key, api_token),
                params={"PageSize": 100},
            )
        if resp.status_code == 401:
            raise HTTPException(400, "Invalid Exotel credentials")
        resp.raise_for_status()
        data = resp.json()

        # Enrich with agent assignment from our DB
        agent_q = await db.execute(select(Agent).where(Agent.tenantId == auth.tenant_id))
        agents_by_phone = {a.phoneNumber: a for a in agent_q.scalars().all() if a.phoneNumber}

        numbers = []
        for n in data.get("Numbers", data.get("numbers", [])):
            phone = n.get("PhoneNumber") or n.get("phone_number", "")
            assigned = agents_by_phone.get(phone)
            numbers.append({
                "phone_number": phone,
                "sid": n.get("Sid") or n.get("sid"),
                "status": n.get("Status", "active"),
                "voice_url": n.get("VoiceUrl") or n.get("voice_url"),
                "provider": "exotel",
                "assigned_agent_id": assigned.id if assigned else None,
                "assigned_agent_name": assigned.name if assigned else None,
            })
        return {"numbers": numbers, "total": len(numbers)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[exotel] owned numbers error: %s", exc)
        raise HTTPException(502, "Exotel API error")


@router.post("/exotel/purchase")
async def exotel_purchase_number(
    body: ExotelPurchaseRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Purchase an Exophone DID.
    Optionally activates a 30-day pilot plan (free for MCP tenants).

    Exotel API: POST /accounts/{SID}/phone_numbers/purchase
    """
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(403, "Tenant not found")

    creds = await _exotel_creds_with_fallback(tenant)
    if not creds:
        raise HTTPException(400, "Exotel not configured")
    sid, api_key, api_token = creds

    phone = body.number.strip()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{_exotel_base(sid)}/phone_numbers/purchase",
                auth=(api_key, api_token),
                data={"PhoneNumber": phone},
            )
        if resp.status_code == 401:
            raise HTTPException(400, "Invalid Exotel credentials")
        if resp.status_code == 400:
            detail = resp.json().get("RestException", {}).get("Message", "Purchase failed")
            raise HTTPException(400, f"Exotel: {detail}")
        resp.raise_for_status()
        purchased = resp.json()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[exotel] purchase error: %s", exc)
        raise HTTPException(502, "Exotel API error")

    # Activate pilot plan if requested (first DID is free for 30 days)
    if body.activate_pilot and tenant.planType in ("mcp", "managed"):
        if not tenant.pilotPlanEndDate:
            tenant.planTier = "pilot"
            tenant.pilotPlanEndDate = datetime.now(timezone.utc) + timedelta(days=30)
            await db.commit()
            logger.info("[exotel] Pilot plan activated for tenant %s until %s", auth.tenant_id, tenant.pilotPlanEndDate)

    phone_number = purchased.get("PhoneNumber") or purchased.get("phone_number") or phone
    logger.info("[exotel] tenant=%s purchased Exophone %s", auth.tenant_id, phone_number)
    return {
        "success": True,
        "phone_number": phone_number,
        "sid": purchased.get("Sid") or purchased.get("sid"),
        "pilot_active": tenant.planTier == "pilot",
        "pilot_end_date": tenant.pilotPlanEndDate.isoformat() if tenant.pilotPlanEndDate else None,
        "message": f"Exophone {phone_number} purchased successfully."
                   + (" 30-day free pilot activated." if tenant.planTier == "pilot" else ""),
    }


@router.post("/exotel/configure/{phone_number:path}")
async def exotel_configure_number(
    phone_number: str,
    body: AssignRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Assign an Exophone to an agent and set the webhook URL on Exotel.
    This wires Exotel's incoming call → your VoiceFlow inbound handler.

    Exotel API: POST /accounts/{SID}/phone_numbers/{id}/update
      VoiceUrl = {FASTAPI_URL}/api/voice/exotel/inbound/{agent_id}
    """
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(403, "Tenant not found")

    agent_q = await db.execute(
        select(Agent).where(Agent.id == body.agent_id, Agent.tenantId == auth.tenant_id)
    )
    agent = agent_q.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")

    creds = await _exotel_creds_with_fallback(tenant)
    if not creds:
        raise HTTPException(400, "Exotel not configured")
    sid, api_key, api_token = creds

    base_url = settings.TWILIO_WEBHOOK_BASE_URL or settings.FASTAPI_URL
    voice_url = f"{base_url}/api/voice/exotel/inbound/{body.agent_id}"
    status_url = f"{base_url}/api/voice/exotel/status/{body.agent_id}"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{_exotel_base(sid)}/phone_numbers/{phone_number}/update",
                auth=(api_key, api_token),
                data={
                    "VoiceUrl": voice_url,
                    "VoiceMethod": "POST",
                    "StatusCallback": status_url,
                    "StatusCallbackMethod": "POST",
                },
            )
        if resp.status_code not in (200, 201):
            detail = resp.json().get("RestException", {}).get("Message", "Configure failed")
            raise HTTPException(400, f"Exotel: {detail}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[exotel] configure error: %s", exc)
        raise HTTPException(502, "Exotel API error")

    # Persist assignment in our DB
    agent.phoneNumber = phone_number
    agent.telephony_provider = "exotel"
    db.add(agent)
    await db.commit()

    logger.info("[exotel] %s configured → agent %s (webhook: %s)", phone_number, body.agent_id, voice_url)
    return {
        "success": True,
        "phone_number": phone_number,
        "agent_id": body.agent_id,
        "voice_url": voice_url,
        "message": f"Exophone {phone_number} now routes to agent '{agent.name}'",
    }


@router.post("/exotel/outbound")
async def exotel_outbound_call(
    body: ExotelOutboundRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate an outbound call via Exotel — used by the Campaign dialer.

    Exotel API: POST /accounts/{SID}/calls/connect
    The 'from_' must be one of this tenant's Exophones.
    """
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(403, "Tenant not found")

    agent_q = await db.execute(
        select(Agent).where(Agent.id == body.agent_id, Agent.tenantId == auth.tenant_id)
    )
    agent = agent_q.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")

    creds = await _exotel_creds_with_fallback(tenant)
    if not creds:
        raise HTTPException(400, "Exotel not configured")
    sid, api_key, api_token = creds

    base_url = settings.TWILIO_WEBHOOK_BASE_URL or settings.FASTAPI_URL
    url = f"{base_url}/api/voice/exotel/inbound/{body.agent_id}"

    # Sanitize 'to' — Exotel expects 10-digit or E.164
    to = body.to.strip().lstrip("+")
    if to.startswith("91") and len(to) == 12:
        to = to[2:]   # strip country code for Exotel India API

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{_exotel_base(sid)}/calls/connect",
                auth=(api_key, api_token),
                data={
                    "From": body.from_,
                    "To": to,
                    "CallerId": body.from_,
                    "Url": url,
                    "StatusCallback": f"{base_url}/api/voice/exotel/status/{body.agent_id}",
                    "Method": "POST",
                },
            )
        if resp.status_code == 401:
            raise HTTPException(400, "Invalid Exotel credentials")
        if resp.status_code not in (200, 201):
            detail = resp.json().get("RestException", {}).get("Message", "Call failed")
            raise HTTPException(400, f"Exotel: {detail}")
        data = resp.json()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[exotel] outbound call error: %s", exc)
        raise HTTPException(502, "Exotel API error")

    call_sid = data.get("Call", {}).get("Sid") or data.get("Sid")
    logger.info("[exotel] outbound call initiated: sid=%s from=%s to=%s agent=%s",
                call_sid, body.from_, to, body.agent_id)
    return {
        "success": True,
        "call_sid": call_sid,
        "status": data.get("Call", {}).get("Status", "initiated"),
        "from": body.from_,
        "to": body.to,
    }


@router.post("/exotel/pilot")
async def activate_exotel_pilot(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually activate the 30-day pilot plan for this tenant.
    During pilot: MCP per-minute charges and DID rental are waived.
    Can only be activated once per tenant.
    """
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(403, "Tenant not found")

    if tenant.pilotPlanEndDate:
        return {
            "success": False,
            "message": "Pilot plan already used for this account.",
            "pilot_end_date": tenant.pilotPlanEndDate.isoformat(),
        }

    tenant.planTier = "pilot"
    tenant.pilotPlanEndDate = datetime.now(timezone.utc) + timedelta(days=30)
    # Credit 100 pilot minutes for MCP plan
    if tenant.planType in ("mcp", "managed"):
        tenant.managedMinutesBalance = max(tenant.managedMinutesBalance, 100)
    await db.commit()

    logger.info("[pilot] Activated for tenant %s — expires %s", auth.tenant_id, tenant.pilotPlanEndDate)
    return {
        "success": True,
        "pilot_end_date": tenant.pilotPlanEndDate.isoformat(),
        "free_minutes_credited": 100 if tenant.planType in ("mcp", "managed") else 0,
        "message": "30-day pilot activated. All MCP charges and DID rental waived until expiry.",
    }
