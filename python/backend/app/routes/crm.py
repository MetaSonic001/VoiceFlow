"""
/api/crm routes — CRM BYOK integration & field mapping.

GET  /api/crm/field-mapping          — return current field mapping + connect status
POST /api/crm/field-mapping          — save field mapping or disconnect a provider
GET  /api/crm/lookup?phone=...       — enrich a phone number from the connected CRM

BYOK credential endpoints (no OAuth flows — users enter their own tokens):
POST /api/crm/connect/hubspot        — save HubSpot Private App token (pat-...)
POST /api/crm/connect/salesforce     — save Salesforce access token + instance URL
DELETE /api/crm/connect/hubspot      — remove HubSpot credentials
DELETE /api/crm/connect/salesforce   — remove Salesforce credentials

Credentials are validated against the respective API before saving, then stored
AES-256 encrypted in tenant.settings["crm"] (same pattern as BYOK keys in settings.py).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Tenant, Contact
from app.services.credentials import encrypt, decrypt_safe, mask

logger = logging.getLogger("voiceflow.crm")
router = APIRouter()


def _crm_cfg(tenant: Tenant) -> dict:
    return (tenant.settings or {}).get("crm", {})


@router.get("/field-mapping")
async def get_field_mapping(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return JSONResponse({"error": "Tenant not found"}, status_code=404)

    cfg = _crm_cfg(tenant)
    hs_token = decrypt_safe(cfg.get("hubspotAccessToken", ""))
    sf_token = decrypt_safe(cfg.get("salesforceAccessToken", ""))
    return {
        "fieldMap": cfg.get("fieldMap", []),
        "hubspotConnected": bool(hs_token),
        "hubspotMasked": mask(hs_token, prefix_len=6, suffix_len=4) if hs_token else None,
        "salesforceConnected": bool(sf_token),
        "salesforceMasked": mask(sf_token, prefix_len=6, suffix_len=4) if sf_token else None,
        "salesforceInstanceUrl": cfg.get("salesforceInstanceUrl", ""),
    }


@router.post("/field-mapping")
async def save_field_mapping(
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return JSONResponse({"error": "Tenant not found"}, status_code=404)

    settings = dict(tenant.settings or {})
    crm = dict(settings.get("crm", {}))

    if "fieldMap" in body:
        crm["fieldMap"] = body["fieldMap"]

    disconnect = body.get("disconnect")
    if disconnect == "hubspot":
        crm.pop("hubspotAccessToken", None)
    elif disconnect == "salesforce":
        crm.pop("salesforceAccessToken", None)
        crm.pop("salesforceInstanceUrl", None)

    settings["crm"] = crm
    tenant.settings = settings
    await db.commit()
    return {"ok": True}


@router.get("/lookup")
async def crm_lookup(
    phone: str = Query(..., description="Phone number in E.164 format"),
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Look up enriched context for a phone number.
    Strategy:
    1. Check VoiceFlow contacts table first (always available).
    2. If HubSpot connected — query HubSpot contacts search API.
    3. If Salesforce connected — query Salesforce SOQL.
    Returns merged context dict.
    """
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    cfg = _crm_cfg(tenant) if tenant else {}

    # 1. Local contact
    local_row = await db.execute(
        select(Contact).where(Contact.tenantId == auth.tenant_id, Contact.phoneNumber == phone)
    )
    local = local_row.scalar_one_or_none()
    context: dict = {}
    if local:
        context.update({
            "name": local.name,
            "email": local.email,
            "company": local.company,
            "intentLevel": local.intentLevel,
            "totalCalls": local.totalCalls,
            "tags": local.tags,
            "notes": local.notes,
        })

    # 2. HubSpot enrichment
    hs_token = decrypt_safe(cfg.get("hubspotAccessToken", ""))
    if hs_token:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.post(
                    "https://api.hubapi.com/crm/v3/objects/contacts/search",
                    headers={"Authorization": f"Bearer {hs_token}", "Content-Type": "application/json"},
                    json={
                        "filterGroups": [{"filters": [{"propertyName": "phone", "operator": "EQ", "value": phone}]}],
                        "properties": ["firstname", "lastname", "email", "company", "dealstage", "lifecyclestage"],
                        "limit": 1,
                    },
                )
                if r.status_code == 200:
                    results = r.json().get("results", [])
                    if results:
                        props = results[0].get("properties", {})
                        context["hubspot"] = {
                            "firstName": props.get("firstname"),
                            "lastName": props.get("lastname"),
                            "email": props.get("email"),
                            "company": props.get("company"),
                            "dealStage": props.get("dealstage"),
                            "lifecycleStage": props.get("lifecyclestage"),
                        }
        except Exception as exc:
            logger.warning("[crm_lookup] HubSpot error: %s", exc)

    # 3. Salesforce enrichment
    sf_token = decrypt_safe(cfg.get("salesforceAccessToken", ""))
    sf_instance = cfg.get("salesforceInstanceUrl", "https://login.salesforce.com")
    if sf_token:
        try:
            import httpx
            soql = f"SELECT Id,FirstName,LastName,Email,Company,LeadSource,Status FROM Lead WHERE Phone='{phone}' LIMIT 1"
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.get(
                    f"{sf_instance}/services/data/v57.0/query",
                    headers={"Authorization": f"Bearer {sf_token}"},
                    params={"q": soql},
                )
                if r.status_code == 200:
                    records = r.json().get("records", [])
                    if records:
                        rec = records[0]
                        context["salesforce"] = {
                            "firstName": rec.get("FirstName"),
                            "lastName": rec.get("LastName"),
                            "email": rec.get("Email"),
                            "company": rec.get("Company"),
                            "leadSource": rec.get("LeadSource"),
                            "status": rec.get("Status"),
                        }
        except Exception as exc:
            logger.warning("[crm_lookup] Salesforce error: %s", exc)

    return {"phone": phone, "context": context}


# ── BYOK Credential Endpoints ─────────────────────────────────────────────────

@router.post("/connect/hubspot")
async def connect_hubspot(
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Save a HubSpot Private App token (BYOK).

    Expects: { "apiKey": "pat-na1-..." }

    The token is validated by calling the HubSpot account info API before saving.
    Stored AES-256 encrypted in tenant.settings["crm"]["hubspotAccessToken"].
    """
    api_key = (body.get("apiKey") or "").strip()
    if not api_key:
        return JSONResponse({"error": "apiKey is required."}, status_code=400)

    # Validate the token against HubSpot
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.hubapi.com/account-info/v3/details",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        if r.status_code == 401:
            return JSONResponse({"error": "Invalid HubSpot token — authentication failed."}, status_code=400)
        if r.status_code not in (200, 204):
            return JSONResponse({"error": f"HubSpot validation returned HTTP {r.status_code}."}, status_code=400)
        hub_info = r.json() if r.status_code == 200 else {}
    except Exception as exc:
        logger.warning("[crm] HubSpot validation error: %s", exc)
        return JSONResponse({"error": f"Could not reach HubSpot API: {exc}"}, status_code=502)

    # Store encrypted
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return JSONResponse({"error": "Tenant not found"}, status_code=404)

    settings = dict(tenant.settings or {})
    crm = dict(settings.get("crm", {}))
    crm["hubspotAccessToken"] = encrypt(api_key)
    settings["crm"] = crm
    tenant.settings = settings
    await db.commit()

    logger.info("[crm] HubSpot BYOK token saved for tenant=%s hub=%s", auth.tenant_id, hub_info.get("portalId"))
    return {
        "ok": True,
        "maskedKey": mask(api_key, prefix_len=6, suffix_len=4),
        "hubId": hub_info.get("portalId"),
    }


@router.delete("/connect/hubspot")
async def disconnect_hubspot(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Remove stored HubSpot credentials."""
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return JSONResponse({"error": "Tenant not found"}, status_code=404)

    settings = dict(tenant.settings or {})
    crm = dict(settings.get("crm", {}))
    crm.pop("hubspotAccessToken", None)
    settings["crm"] = crm
    tenant.settings = settings
    await db.commit()
    return {"ok": True}


@router.post("/connect/salesforce")
async def connect_salesforce(
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Save Salesforce Connected App credentials (BYOK).

    Expects: { "accessToken": "...", "instanceUrl": "https://yourorg.salesforce.com" }

    Obtain an access token from your Salesforce Connected App (Settings →
    App Manager → View credentials, then use the OAuth 2.0 token endpoint with
    client_credentials or username-password grant).

    The token is validated by calling the Salesforce identity API before saving.
    Stored AES-256 encrypted in tenant.settings["crm"]["salesforceAccessToken"].
    """
    access_token = (body.get("accessToken") or "").strip()
    instance_url = (body.get("instanceUrl") or "").strip().rstrip("/")

    if not access_token:
        return JSONResponse({"error": "accessToken is required."}, status_code=400)
    if not instance_url or not instance_url.startswith("https://"):
        return JSONResponse({"error": "instanceUrl must be a valid https:// URL."}, status_code=400)

    # Validate the token
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{instance_url}/services/oauth2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if r.status_code == 401:
            return JSONResponse({"error": "Invalid Salesforce token — authentication failed."}, status_code=400)
        if r.status_code not in (200,):
            return JSONResponse({"error": f"Salesforce validation returned HTTP {r.status_code}."}, status_code=400)
        sf_info = r.json()
    except Exception as exc:
        logger.warning("[crm] Salesforce validation error: %s", exc)
        return JSONResponse({"error": f"Could not reach Salesforce API: {exc}"}, status_code=502)

    # Store encrypted
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return JSONResponse({"error": "Tenant not found"}, status_code=404)

    settings = dict(tenant.settings or {})
    crm = dict(settings.get("crm", {}))
    crm["salesforceAccessToken"] = encrypt(access_token)
    crm["salesforceInstanceUrl"] = instance_url
    settings["crm"] = crm
    tenant.settings = settings
    await db.commit()

    logger.info("[crm] Salesforce BYOK token saved for tenant=%s org=%s", auth.tenant_id, sf_info.get("organization_id"))
    return {
        "ok": True,
        "maskedKey": mask(access_token, prefix_len=6, suffix_len=4),
        "organizationId": sf_info.get("organization_id"),
        "instanceUrl": instance_url,
    }


@router.delete("/connect/salesforce")
async def disconnect_salesforce(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Remove stored Salesforce credentials."""
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return JSONResponse({"error": "Tenant not found"}, status_code=404)

    settings = dict(tenant.settings or {})
    crm = dict(settings.get("crm", {}))
    crm.pop("salesforceAccessToken", None)
    crm.pop("salesforceInstanceUrl", None)
    settings["crm"] = crm
    tenant.settings = settings
    await db.commit()
    return {"ok": True}




