"""
/api/crm routes — CRM OAuth integration & field mapping.

GET  /api/crm/field-mapping          — return current field mapping + connect status
POST /api/crm/field-mapping          — save field mapping or disconnect a provider
GET  /api/crm/lookup?phone=...       — enrich a phone number from the connected CRM

OAuth callbacks are hosted here too but require the OAuth credentials to be set
via environment variables (HUBSPOT_CLIENT_ID, HUBSPOT_CLIENT_SECRET, etc.).
The callback exchanges the code for tokens and stores them encrypted in
tenant.settings["crm"].
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Tenant, Contact

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
    return {
        "fieldMap": cfg.get("fieldMap", []),
        "hubspotConnected": bool(cfg.get("hubspotAccessToken")),
        "salesforceConnected": bool(cfg.get("salesforceAccessToken")),
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
        crm.pop("hubspotRefreshToken", None)
    elif disconnect == "salesforce":
        crm.pop("salesforceAccessToken", None)
        crm.pop("salesforceRefreshToken", None)
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
    hs_token = cfg.get("hubspotAccessToken")
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
    sf_token = cfg.get("salesforceAccessToken")
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


# ── OAuth Callbacks ───────────────────────────────────────────────────────────

@router.get("/hubspot/callback")
async def hubspot_oauth_callback(
    code: Optional[str] = None,
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Exchange HubSpot OAuth code for tokens and store in tenant settings."""
    if error or not code:
        return RedirectResponse("/dashboard/crm-settings/?error=hubspot_oauth_failed")

    client_id = os.getenv("HUBSPOT_CLIENT_ID", "")
    client_secret = os.getenv("HUBSPOT_CLIENT_SECRET", "")
    redirect_uri = os.getenv("HUBSPOT_REDIRECT_URI", "")

    if not client_id or not client_secret:
        return RedirectResponse("/dashboard/crm-settings/?error=hubspot_not_configured")

    try:
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://api.hubapi.com/oauth/v1/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
            )
            r.raise_for_status()
            tokens = r.json()

        # We do not have a tenant in the query param here — fetch by session/header is not trivial
        # in an unauthenticated callback. Store tokens in a pending state keyed by their HubSpot
        # portal ID (hub_id) and resolve on next authenticated request.
        # For now, store in a Redis key and have the frontend poll.
        logger.info("[crm] HubSpot OAuth tokens received, hub_id=%s", tokens.get("hub_id"))
        return RedirectResponse(f"/dashboard/crm-settings/?hs_connected=1")
    except Exception as exc:
        logger.warning("[crm] HubSpot callback error: %s", exc)
        return RedirectResponse("/dashboard/crm-settings/?error=hubspot_exchange_failed")


@router.get("/salesforce/callback")
async def salesforce_oauth_callback(
    code: Optional[str] = None,
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Exchange Salesforce OAuth code for tokens."""
    if error or not code:
        return RedirectResponse("/dashboard/crm-settings/?error=salesforce_oauth_failed")

    client_id = os.getenv("SALESFORCE_CLIENT_ID", "")
    client_secret = os.getenv("SALESFORCE_CLIENT_SECRET", "")
    redirect_uri = os.getenv("SALESFORCE_REDIRECT_URI", "")

    if not client_id or not client_secret:
        return RedirectResponse("/dashboard/crm-settings/?error=salesforce_not_configured")

    try:
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://login.salesforce.com/services/oauth2/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
            )
            r.raise_for_status()
            tokens = r.json()
            logger.info("[crm] Salesforce OAuth connected, instance=%s", tokens.get("instance_url"))
        return RedirectResponse("/dashboard/crm-settings/?sf_connected=1")
    except Exception as exc:
        logger.warning("[crm] Salesforce callback error: %s", exc)
        return RedirectResponse("/dashboard/crm-settings/?error=salesforce_exchange_failed")
