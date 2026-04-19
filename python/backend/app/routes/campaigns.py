"""
/api/campaigns routes — outbound calling campaign management.

POST   /api/campaigns/                        Create campaign
POST   /api/campaigns/{id}/contacts/upload    Upload contacts CSV
POST   /api/campaigns/{id}/start              Start campaign (enqueue + launch worker)
POST   /api/campaigns/{id}/pause             Pause campaign
GET    /api/campaigns/{id}/stats             Live stats
POST   /api/campaigns/{id}/amd-callback      Twilio AMD webhook (internal)
"""
from __future__ import annotations

import asyncio
import csv
import io
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Campaign, CampaignContact, Agent

logger = logging.getLogger("voiceflow.campaigns")
router = APIRouter()


# ── Helper ────────────────────────────────────────────────────────────────────

def _campaign_to_dict(c: Campaign) -> dict:
    return {
        "id": c.id,
        "tenantId": c.tenantId,
        "agentId": c.agentId,
        "name": c.name,
        "status": c.status,
        "allowedCallHours": c.allowedCallHours,
        "timezone": c.timezone,
        "maxRetries": c.maxRetries,
        "voicemailAction": c.voicemailAction,
        "voicemailMessage": c.voicemailMessage,
        "totalContacts": c.totalContacts,
        "dialedCount": c.dialedCount,
        "answeredCount": c.answeredCount,
        "machinedCount": c.machinedCount,
        "failedCount": c.failedCount,
        "startedAt": c.startedAt.isoformat() if c.startedAt else None,
        "completedAt": c.completedAt.isoformat() if c.completedAt else None,
        "createdAt": c.createdAt.isoformat() if c.createdAt else None,
        "updatedAt": c.updatedAt.isoformat() if c.updatedAt else None,
    }


# ── List campaigns ────────────────────────────────────────────────────────────

@router.get("/")
async def list_campaigns(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign)
        .where(Campaign.tenantId == auth.tenant_id)
        .order_by(Campaign.createdAt.desc())
    )
    return {"campaigns": [_campaign_to_dict(c) for c in result.scalars().all()]}


# ── Create campaign ───────────────────────────────────────────────────────────

@router.post("/")
async def create_campaign(
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Create a new campaign in *draft* status."""
    body = await request.json()

    agent_id: str = body.get("agentId", "")
    if not agent_id:
        raise HTTPException(status_code=400, detail="agentId is required")

    # Verify agent belongs to tenant
    agent_result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id)
    )
    if not agent_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")

    campaign = Campaign(
        tenantId=auth.tenant_id,
        agentId=agent_id,
        name=body.get("name", "Untitled Campaign"),
        allowedCallHours=body.get("allowedCallHours"),
        timezone=body.get("timezone", "UTC"),
        maxRetries=int(body.get("maxRetries", 3)),
        voicemailAction=body.get("voicemailAction", "hangup"),
        voicemailMessage=body.get("voicemailMessage"),
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return _campaign_to_dict(campaign)


# ── Upload contacts CSV ───────────────────────────────────────────────────────

@router.post("/{campaign_id}/contacts/upload")
async def upload_contacts(
    campaign_id: str,
    file: UploadFile = File(...),
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a CSV file of contacts.

    Required column : phone_number
    Optional columns: name, plus any variable columns stored in contact.variables
    """
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenantId == auth.tenant_id,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status not in ("draft", "paused"):
        raise HTTPException(
            status_code=400,
            detail="Contacts can only be uploaded to draft or paused campaigns",
        )

    content = await file.read()
    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames or "phone_number" not in reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV must contain a 'phone_number' column")

    reserved_cols = {"phone_number", "name"}
    added = 0
    skipped = 0

    for row in reader:
        phone = (row.get("phone_number") or "").strip()
        if not phone:
            skipped += 1
            continue

        # Normalize phone number to E.164 format
        try:
            import phonenumbers
            parsed = phonenumbers.parse(phone, "IN")  # default region India
            phone = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except Exception:
            logger.warning("[campaigns] could not normalize phone number (row skipped)")
            skipped += 1
            continue

        name = (row.get("name") or "").strip() or None
        variables = {k: v for k, v in row.items() if k not in reserved_cols and v}

        contact = CampaignContact(
            campaignId=campaign_id,
            tenantId=auth.tenant_id,
            phoneNumber=phone,
            name=name,
            variables=variables or None,
        )
        db.add(contact)
        added += 1

    # Update totalContacts counter
    campaign.totalContacts = (campaign.totalContacts or 0) + added
    await db.commit()

    return {"added": added, "skipped": skipped, "totalContacts": campaign.totalContacts}


# ── Start campaign ────────────────────────────────────────────────────────────

@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Enqueue contacts into Redis and launch the worker as a background task."""
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenantId == auth.tenant_id,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status not in ("draft", "paused"):
        raise HTTPException(
            status_code=400,
            detail=f"Campaign is already {campaign.status}",
        )

    from app.services.campaign_worker import campaign_worker

    enqueued = await campaign_worker.enqueue_campaign(campaign_id, db)
    if enqueued == 0:
        raise HTTPException(status_code=400, detail="No pending contacts to dial")

    # Launch worker without blocking the request
    asyncio.create_task(campaign_worker.process_campaign(campaign_id))

    return {"status": "started", "contactsEnqueued": enqueued}


# ── Pause campaign ────────────────────────────────────────────────────────────

@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Set campaign status to 'paused'. The worker will stop after the current call."""
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenantId == auth.tenant_id,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Campaign is not active (current status: {campaign.status})",
        )

    await db.execute(
        update(Campaign)
        .where(Campaign.id == campaign_id)
        .values(status="paused")
    )
    await db.commit()
    return {"status": "paused"}


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/{campaign_id}/stats")
async def campaign_stats(
    campaign_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Return live stats for a campaign, including Redis queue depth."""
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenantId == auth.tenant_id,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Redis queue depth
    queue_remaining = 0
    try:
        import redis.asyncio as aioredis
        from app.config import settings as _settings

        r = aioredis.Redis(
            host=_settings.REDIS_HOST,
            port=_settings.REDIS_PORT,
            db=3,
            decode_responses=True,
        )
        queue_remaining = await r.llen(f"campaign:{campaign_id}:queue")
        await r.aclose()
    except Exception:
        pass

    answered = campaign.answeredCount or 0
    dialed = campaign.dialedCount or 0

    return {
        "id": campaign.id,
        "name": campaign.name,
        "status": campaign.status,
        "totalContacts": campaign.totalContacts,
        "dialedCount": dialed,
        "answeredCount": answered,
        "machinedCount": campaign.machinedCount,
        "failedCount": campaign.failedCount,
        "queueRemaining": queue_remaining,
        "answerRate": round(answered / dialed * 100, 1) if dialed else 0,
        "startedAt": campaign.startedAt.isoformat() if campaign.startedAt else None,
        "completedAt": campaign.completedAt.isoformat() if campaign.completedAt else None,
    }


# ── AMD Callback (Twilio webhook) ─────────────────────────────────────────────

@router.post("/{campaign_id}/amd-callback")
async def amd_callback(campaign_id: str, request: Request):
    """
    Twilio AsyncAmd status callback.
    Updates contact and campaign stats based on answering machine detection result.
    """
    form = await request.form()
    call_sid = form.get("CallSid", "")
    answered_by = form.get("AnsweredBy", "unknown")

    if call_sid:
        from app.services.campaign_worker import campaign_worker

        asyncio.create_task(
            campaign_worker.handle_amd_result(
                call_sid=call_sid,
                answered_by=answered_by,
                campaign_id=campaign_id,
            )
        )

    return JSONResponse({"received": True})
