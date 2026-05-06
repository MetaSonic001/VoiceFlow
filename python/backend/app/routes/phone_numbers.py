"""
Phone Numbers Shop — buy, manage, and assign phone numbers in-platform.

Supports:
  • Twilio — international numbers (local, toll-free, mobile)
  • Exotel — India PSTN numbers (requires Exotel account)

Endpoints
---------
GET  /api/phone-numbers/search           — search available numbers
GET  /api/phone-numbers/owned            — list numbers owned by this tenant
POST /api/phone-numbers/purchase         — buy a number
DELETE /api/phone-numbers/{sid}          — release / delete a number
POST /api/phone-numbers/{sid}/assign     — assign a number to an agent
POST /api/phone-numbers/{sid}/unassign   — remove agent assignment
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
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
        creds = await _exotel_creds(tenant)
        if not creds:
            raise HTTPException(400, "Exotel credentials not configured")
        # Exotel numbers are provisioned via their dashboard; return instruction
        return {
            "numbers": [],
            "message": "For Exotel India numbers, please provision via the Exotel dashboard and enter the number in your agent telephony settings. Exotel DID allocation requires KYC verification.",
            "exotel_dashboard": "https://my.exotel.com/",
        }

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
