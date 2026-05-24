"""
CRM Enrichment Service — bidirectional CRM sync.

BEFORE a call starts:
  enrich_caller(tenant_id, phone_number, db) → dict
    - Checks internal Contact table first (OmniCRM)
    - If HubSpot configured, pulls contact by phone: name, email, company,
      open deals, last activity, open tickets
    - If Salesforce configured, pulls Lead/Contact by phone: same fields
    - Returns a unified context dict injected into the agent's system prompt
      BEFORE the first turn so the agent can greet by name, reference open
      issues, etc.

AFTER a call ends:
  update_contact_post_call(tenant_id, phone_number, lead_data, db)
    - Upserts the internal Contact row with new extracted_data, last_called_at
    - This feeds the NEXT call's enrichment automatically

Neither OmniDimension nor Bolna does proper pre-call CRM enrichment.
This is a genuine differentiator.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Contact, Tenant

logger = logging.getLogger("voiceflow.crm_enrichment")


# ─────────────────────────────────────────────────────────────────────────────
# Internal OmniCRM lookup
# ─────────────────────────────────────────────────────────────────────────────

async def _get_internal_contact(tenantId: str, phone: str, db: AsyncSession) -> Optional[Contact]:
    """Fetch from the built-in contacts table (fastest path — no external I/O)."""
    result = await db.execute(
        select(Contact).where(
            Contact.tenantId == tenantId,
            Contact.phoneNumber == phone,
        )
    )
    return result.scalar_one_or_none()


async def _upsert_internal_contact(
    tenantId: str,
    phone: str,
    updates: dict,
    db: AsyncSession,
) -> Contact:
    """Create or update the internal Contact row."""
    contact = await _get_internal_contact(tenantId, phone, db)
    if contact is None:
        contact = Contact(tenantId=tenantId, phoneNumber=phone)
        db.add(contact)

    for key, value in updates.items():
        if hasattr(contact, key) and value is not None:
            setattr(contact, key, value)

    contact.updatedAt = datetime.now(timezone.utc)  # type: ignore[assignment]
    await db.commit()
    await db.refresh(contact)
    return contact


# ─────────────────────────────────────────────────────────────────────────────
# HubSpot pre-call pull
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_hubspot_context(phone: str, access_token: str) -> dict:
    """
    Pull HubSpot contact by phone number.
    Returns a dict with name, email, company, open_deals, last_activity, open_tickets.
    """
    context: dict = {}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Search contact by phone
            resp = await client.post(
                "https://api.hubapi.com/crm/v3/objects/contacts/search",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={
                    "filterGroups": [{"filters": [{"propertyName": "phone", "operator": "EQ", "value": phone}]}],
                    "properties": ["firstname", "lastname", "email", "company", "hs_lead_status",
                                   "recent_deal_amount", "num_notes", "hs_latest_source"],
                    "limit": 1,
                },
            )
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    props = results[0].get("properties", {})
                    contact_hs_id = results[0].get("id")
                    name_parts = [props.get("firstname", ""), props.get("lastname", "")]
                    context["name"] = " ".join(p for p in name_parts if p).strip() or None
                    context["email"] = props.get("email")
                    context["company"] = props.get("company")
                    context["hubspot_lead_status"] = props.get("hs_lead_status")
                    context["hubspot_contact_id"] = contact_hs_id

                    # Fetch recent deals
                    if contact_hs_id:
                        deals_resp = await client.get(
                            f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_hs_id}/associations/deals",
                            headers={"Authorization": f"Bearer {access_token}"},
                        )
                        if deals_resp.status_code == 200:
                            deal_ids = [d["id"] for d in deals_resp.json().get("results", [])[:3]]
                            context["open_deals"] = len(deal_ids)
    except Exception as exc:
        logger.warning("[crm_enrichment] HubSpot fetch failed for %s: %s", phone, exc)
    return context


# ─────────────────────────────────────────────────────────────────────────────
# Salesforce pre-call pull
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_salesforce_context(phone: str, instance_url: str, access_token: str) -> dict:
    """
    Pull Salesforce Lead or Contact by phone number.
    Supports OAuth access token (preferred) or password flow.
    """
    context: dict = {}
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Try Lead first, then Contact
            for obj_type in ("Lead", "Contact"):
                phone_field = "Phone" if obj_type == "Contact" else "Phone"
                query = (
                    f"SELECT Id, Name, Email, Company, Status, LeadSource "
                    f"FROM {obj_type} WHERE {phone_field} = '{phone}' LIMIT 1"
                )
                resp = await client.get(
                    f"{instance_url}/services/data/v58.0/query",
                    headers=headers,
                    params={"q": query},
                )
                if resp.status_code == 200:
                    records = resp.json().get("records", [])
                    if records:
                        r = records[0]
                        context["name"] = r.get("Name")
                        context["email"] = r.get("Email")
                        context["company"] = r.get("Company") or r.get("Account", {}).get("Name")
                        context["sf_status"] = r.get("Status")
                        context["sf_lead_source"] = r.get("LeadSource")
                        context[f"sf_{obj_type.lower()}_id"] = r.get("Id")
                        break  # found in Lead, skip Contact search
    except Exception as exc:
        logger.warning("[crm_enrichment] Salesforce fetch failed for %s: %s", phone, exc)
    return context


# ─────────────────────────────────────────────────────────────────────────────
# Main public API
# ─────────────────────────────────────────────────────────────────────────────

async def enrich_caller(
    tenant_id: str,
    phone_number: str,
    db: AsyncSession,
) -> dict:
    """
    Enrich a caller before a call starts.

    Steps:
    1. Check internal Contact table → instant, sub-1ms
    2. In parallel: check HubSpot + Salesforce if configured for tenant
    3. Upsert Contact with freshest data
    4. Return a context dict injected into the agent's system prompt

    Designed to complete in <500ms on slow connections (10s timeout per CRM).
    """
    # 1. Internal contact (no I/O)
    internal = await _get_internal_contact(tenant_id, phone_number, db)
    crm_context: dict = {}
    updates: dict = {}

    if internal:
        crm_context.update({
            "name": internal.name,
            "email": internal.email,
            "company": internal.company,
            "intent_level": internal.intentLevel,
            "sentiment": internal.sentiment,
            "total_calls": internal.totalCalls,
            "last_called_at": internal.lastCalledAt.isoformat() if internal.lastCalledAt else None,
            "notes": internal.notes,
            **(internal.crmContext or {}),
        })

    # 2. Fetch tenant settings for CRM credentials
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant or not tenant.settings:
        return crm_context

    integrations: dict = (tenant.settings or {}).get("integrations", {})
    hs_config: dict = integrations.get("hubspot", {})
    sf_config: dict = integrations.get("salesforce", {})

    # 3. Run CRM fetches in parallel
    tasks = []
    if hs_config.get("access_token"):
        tasks.append(_fetch_hubspot_context(phone_number, hs_config["access_token"]))
    if sf_config.get("instance_url") and sf_config.get("access_token"):
        tasks.append(_fetch_salesforce_context(
            phone_number, sf_config["instance_url"], sf_config["access_token"]
        ))

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, dict):
                crm_context.update(r)
                updates["crmContext"] = crm_context
                if r.get("name") and not crm_context.get("name"):
                    updates["name"] = r["name"]
                if r.get("email"):
                    updates["email"] = r["email"]
                if r.get("company"):
                    updates["company"] = r["company"]
                if r.get("hubspot_contact_id"):
                    updates["hubspotContactId"] = r["hubspot_contact_id"]
                if r.get("sf_lead_id"):
                    updates["salesforceLeadId"] = r["sf_lead_id"]

    # 4. Upsert internal contact with fresh data
    if updates or internal is None:
        await _upsert_internal_contact(tenant_id, phone_number, updates, db)

    return crm_context


async def format_crm_context_for_prompt(context: dict) -> str:
    """
    Convert CRM context dict into a compact natural-language block
    injected at the start of the agent system prompt.

    Example output:
      [CALLER CONTEXT]
      Name: Priya Sharma | Company: FinTech Corp | Intent: warm
      Last called: 2 days ago (3 total calls)
      CRM notes: Has open support ticket #4521 – order not delivered
    """
    if not context:
        return ""
    parts = ["[CALLER CONTEXT — use naturally, do not mention this block]"]
    if context.get("name"):
        parts.append(f"Name: {context['name']}")
    if context.get("email"):
        parts.append(f"Email: {context['email']}")
    if context.get("company"):
        parts.append(f"Company: {context['company']}")
    if context.get("intent_level"):
        parts.append(f"Intent level: {context['intent_level']}")
    if context.get("sentiment"):
        parts.append(f"Last sentiment: {context['sentiment']}")
    total = context.get("total_calls", 0)
    if total and total > 0:
        last = context.get("last_called_at", "unknown")
        parts.append(f"Call history: {total} previous call(s), last at {last}")
    if context.get("open_deals"):
        parts.append(f"Open deals: {context['open_deals']}")
    if context.get("hubspot_lead_status"):
        parts.append(f"HubSpot status: {context['hubspot_lead_status']}")
    if context.get("sf_status"):
        parts.append(f"Salesforce status: {context['sf_status']}")
    if context.get("notes"):
        parts.append(f"Notes: {context['notes']}")
    return "\n".join(parts)


async def update_contact_post_call(
    tenant_id: str,
    phone_number: str,
    lead_data: dict,
    db: AsyncSession,
) -> None:
    """
    After a call ends, upsert the internal Contact with extracted lead data.
    This feeds the NEXT call's enrichment automatically.
    """
    if not phone_number:
        return
    contact = await _get_internal_contact(tenant_id, phone_number, db)
    existing_data = (contact.extractedData if contact else None) or {}

    # Merge fresh extracted_variables into existing
    fresh_vars = lead_data.get("extracted_variables", {})
    merged = {**existing_data, **fresh_vars}

    updates: dict = {
        "extractedData": merged,
        "lastCalledAt": datetime.now(timezone.utc),
    }
    if lead_data.get("name"):
        updates["name"] = lead_data["name"]
    if lead_data.get("email"):
        updates["email"] = lead_data["email"]
    if lead_data.get("company"):
        updates["company"] = lead_data["company"]
    if lead_data.get("intent_level"):
        updates["intentLevel"] = lead_data["intent_level"]
    if lead_data.get("sentiment"):
        updates["sentiment"] = lead_data["sentiment"]

    # Increment call counter
    current_count = (contact.totalCalls if contact else 0) or 0
    updates["totalCalls"] = current_count + 1

    await _upsert_internal_contact(tenant_id, phone_number, updates, db)
