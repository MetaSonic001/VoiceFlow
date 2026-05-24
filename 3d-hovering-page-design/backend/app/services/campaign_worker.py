"""
Campaign Worker — outbound dialling engine.

Design principles
-----------------
  • Does NOT block FastAPI: runs as an asyncio background task.
  • Uses Redis list `campaign:{campaign_id}:queue` for contact IDs.
  • Rate-limits to 1 call per second.
  • Delegates compliance checks to ComplianceService.
  • Uses Twilio REST API with AnsweringMachineDetection.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
import redis.asyncio as aioredis

from app.config import settings
from app.services.compliance_service import compliance_service

logger = logging.getLogger("voiceflow.campaign_worker")

# ── Redis helpers ─────────────────────────────────────────────────────────────

def _redis() -> aioredis.Redis:
    return aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=3,
        decode_responses=True,
    )

_QUEUE_KEY = "campaign:{campaign_id}:queue"
_AMD_KEY   = "campaign_amd:{call_sid}"  # stores campaign_id + contact_id while AMD pending


class CampaignWorker:
    """Processes outbound campaigns from a Redis queue."""

    # ── Enqueue ───────────────────────────────────────────────────────────────

    async def enqueue_campaign(self, campaign_id: str, db) -> int:
        """
        Load all *pending* contacts for the campaign into the Redis queue.
        Returns the number of contacts enqueued.
        """
        from app.models import CampaignContact
        from sqlalchemy import select, update

        result = await db.execute(
            select(CampaignContact).where(
                CampaignContact.campaignId == campaign_id,
                CampaignContact.status == "pending",
            )
        )
        contacts = result.scalars().all()
        if not contacts:
            return 0

        redis = _redis()
        queue_key = f"campaign:{campaign_id}:queue"
        try:
            pipe = redis.pipeline()
            pipe.delete(queue_key)  # clear stale queue
            for c in contacts:
                pipe.rpush(queue_key, c.id)
            pipe.expire(queue_key, 86400)  # 24-hour TTL
            await pipe.execute()
        finally:
            await redis.aclose()

        logger.info("[campaign_worker] enqueued %d contacts campaign=%s", len(contacts), campaign_id)
        return len(contacts)

    # ── Process ───────────────────────────────────────────────────────────────

    async def process_campaign(self, campaign_id: str) -> None:
        """
        Main worker loop.

        1. Pop a contact ID from the Redis queue.
        2. Run compliance checks (DND, hours, retries).
        3. Initiate a Twilio call with AMD enabled.
        4. Update contact/campaign stats in Postgres.
        5. Sleep 1 second between calls.
        """
        from app.database import AsyncSessionLocal
        from app.models import Campaign, CampaignContact, Agent
        from sqlalchemy import select, update

        queue_key = f"campaign:{campaign_id}:queue"
        redis = _redis()

        try:
            async with AsyncSessionLocal() as db:
                camp_result = await db.execute(
                    select(Campaign).where(Campaign.id == campaign_id)
                )
                campaign = camp_result.scalar_one_or_none()
                if not campaign:
                    logger.error("[campaign_worker] campaign not found: %s", campaign_id)
                    return

                agent_result = await db.execute(
                    select(Agent).where(Agent.id == campaign.agentId)
                )
                agent = agent_result.scalar_one_or_none()
                if not agent:
                    logger.error("[campaign_worker] agent not found for campaign %s", campaign_id)
                    return

                # Mark as active
                campaign.status = "active"
                campaign.startedAt = datetime.now(timezone.utc)
                await db.commit()

            # Main dial loop
            while True:
                contact_id = await redis.lpop(queue_key)
                if contact_id is None:
                    logger.info("[campaign_worker] queue empty — campaign %s complete", campaign_id)
                    break

                async with AsyncSessionLocal() as db:
                    c_result = await db.execute(
                        select(CampaignContact).where(CampaignContact.id == contact_id)
                    )
                    contact = c_result.scalar_one_or_none()
                    if not contact or contact.campaignId != campaign_id:
                        continue

                    # Check if campaign was paused/cancelled
                    camp_check = await db.execute(
                        select(Campaign.status).where(Campaign.id == campaign_id)
                    )
                    current_status = camp_check.scalar_one_or_none()
                    if current_status in ("paused", "cancelled"):
                        logger.info("[campaign_worker] campaign %s is %s — stopping", campaign_id, current_status)
                        # Put the contact back
                        await redis.lpush(queue_key, contact_id)
                        break

                    # Compliance check
                    allowed, reason = await compliance_service.validate_before_dial(
                        tenant_id=contact.tenantId,
                        phone=contact.phoneNumber,
                        agent=agent,
                        contact=contact,
                        db=db,
                    )
                    if not allowed:
                        contact.status = "skipped"
                        contact.updatedAt = datetime.now(timezone.utc)
                        await db.execute(
                            update(Campaign)
                            .where(Campaign.id == campaign_id)
                            .values(failedCount=Campaign.failedCount + 1)
                        )
                        await db.commit()
                        logger.info(
                            "[campaign_worker] skipped contact reason=%s", reason
                        )
                        await asyncio.sleep(1)
                        continue

                    # Initiate call
                    call_sid = await self._initiate_call(
                        campaign=campaign,
                        agent=agent,
                        contact=contact,
                        db=db,
                    )
                    if call_sid:
                        contact.status = "dialing"
                        contact.callAttempts = (contact.callAttempts or 0) + 1
                        contact.lastCallSid = call_sid
                        contact.lastCalledAt = datetime.now(timezone.utc)
                        await db.execute(
                            update(Campaign)
                            .where(Campaign.id == campaign_id)
                            .values(dialedCount=Campaign.dialedCount + 1)
                        )
                        # Store AMD key so the callback can update stats
                        amd_data = json.dumps({
                            "campaignId": campaign_id,
                            "contactId": contact_id,
                        })
                        await redis.setex(f"campaign_amd:{call_sid}", 3600, amd_data)
                    else:
                        contact.status = "failed"
                        await db.execute(
                            update(Campaign)
                            .where(Campaign.id == campaign_id)
                            .values(failedCount=Campaign.failedCount + 1)
                        )
                    await db.commit()

                await asyncio.sleep(1)  # 1 call/second rate limit

            # Mark campaign completed
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Campaign)
                    .where(Campaign.id == campaign_id)
                    .values(
                        status="completed",
                        completedAt=datetime.now(timezone.utc),
                    )
                )
                await db.commit()

            logger.info("[campaign_worker] campaign %s finished", campaign_id)

        except Exception:
            logger.exception("[campaign_worker] error in campaign %s", campaign_id)
            async with AsyncSessionLocal() as db:
                from sqlalchemy import update as sa_update
                from app.models import Campaign
                await db.execute(
                    sa_update(Campaign)
                    .where(Campaign.id == campaign_id)
                    .values(status="failed")
                )
                await db.commit()
        finally:
            await redis.aclose()

    # ── AMD callback ──────────────────────────────────────────────────────────

    async def handle_amd_result(
        self,
        call_sid: str,
        answered_by: str,
        campaign_id: str,
    ) -> None:
        """
        Handle Twilio AnsweringMachineDetection callback.

        answered_by: 'human' | 'machine_start' | 'machine_end_beep' | 'fax' | 'unknown'
        """
        from app.database import AsyncSessionLocal
        from app.models import Campaign, CampaignContact
        from sqlalchemy import select, update

        redis = _redis()
        try:
            raw = await redis.get(f"campaign_amd:{call_sid}")
            if not raw:
                return
            amd_data = json.loads(raw)
            contact_id = amd_data.get("contactId", "")
        finally:
            await redis.aclose()

        is_human = answered_by == "human"
        is_machine = answered_by.startswith("machine")

        async with AsyncSessionLocal() as db:
            c_result = await db.execute(
                select(CampaignContact).where(CampaignContact.id == contact_id)
            )
            contact = c_result.scalar_one_or_none()
            if not contact:
                return

            camp_result = await db.execute(
                select(Campaign).where(Campaign.id == campaign_id)
            )
            campaign = camp_result.scalar_one_or_none()

            if is_human:
                contact.status = "answered"
                if campaign:
                    campaign.answeredCount = (campaign.answeredCount or 0) + 1
            elif is_machine:
                contact.status = "voicemail"
                if campaign:
                    campaign.machinedCount = (campaign.machinedCount or 0) + 1
                # Handle voicemail action
                if campaign and campaign.voicemailAction == "leave_voicemail":
                    await self._leave_voicemail(call_sid, campaign)
                else:
                    await self._hangup_call(call_sid, campaign)
            else:
                contact.status = "failed"
                if campaign:
                    campaign.failedCount = (campaign.failedCount or 0) + 1

            contact.updatedAt = datetime.now(timezone.utc)
            await db.commit()

        logger.info(
            "[campaign_worker] AMD result call=%s answered_by=%s contact=%s",
            call_sid, answered_by, contact_id,
        )

    # ── Twilio helpers ────────────────────────────────────────────────────────

    async def _resolve_twilio_creds(self, tenant_id: str) -> tuple[str | None, str | None]:
        """Return (account_sid, auth_token) preferring tenant-level creds."""
        from app.database import AsyncSessionLocal
        from app.models import Tenant
        from app.services.credentials import decrypt_safe
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
            tenant = result.scalar_one_or_none()

        if tenant and tenant.settings:
            sid = tenant.settings.get("twilioAccountSid")
            token_enc = tenant.settings.get("twilioAuthToken")
            if sid and token_enc:
                return sid, decrypt_safe(token_enc)

        return settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN

    async def _initiate_call(
        self,
        *,
        campaign,
        agent,
        contact,
        db,
    ) -> str | None:
        """Use Twilio REST API to place an outbound call.  Returns call_sid or None."""
        sid, token = await self._resolve_twilio_creds(campaign.tenantId)
        if not sid or not token:
            logger.warning(
                "[campaign_worker] no Twilio creds for tenant=%s", campaign.tenantId
            )
            return None

        # Webhook URL for Twilio to deliver the call to the agent
        base_url = settings.TWILIO_WEBHOOK_BASE_URL or settings.FASTAPI_URL
        provider = (agent.telephony_provider or "twilio-gather").lower()
        if provider == "twilio-stream":
            twiml_url = f"{base_url}/api/voice/inbound/{agent.id}"
        else:
            twiml_url = f"{base_url}/api/voice/gather-inbound/{agent.id}"

        # AMD callback
        amd_callback_url = f"{base_url}/api/campaigns/{campaign.id}/amd-callback"

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json",
                    auth=(sid, token),
                    data={
                        "To": contact.phoneNumber,
                        "From": agent.phoneNumber or "",
                        "Url": twiml_url,
                        "MachineDetection": "Enable",
                        "AsyncAmd": "true",
                        "AsyncAmdStatusCallback": amd_callback_url,
                        "StatusCallback": f"{base_url}/api/voice/status/{agent.id}",
                    },
                )
            if resp.status_code in (200, 201):
                call_sid = resp.json().get("sid")
                logger.info(
                    "[campaign_worker] initiated call=%s", call_sid
                )
                return call_sid
            else:
                logger.warning(
                    "[campaign_worker] Twilio call failed status=%s body=%s",
                    resp.status_code, resp.text[:200],
                )
        except Exception:
            logger.exception(
                "[campaign_worker] Twilio call error"
            )
        return None

    async def _leave_voicemail(self, call_sid: str, campaign) -> None:
        """Play a voicemail message via TTS and hang up."""
        if not campaign.voicemailMessage:
            await self._hangup_call(call_sid, campaign)
            return

        sid, token = await self._resolve_twilio_creds(campaign.tenantId)
        if not sid or not token:
            return

        message = campaign.voicemailMessage
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response><Say>{message}</Say><Hangup/></Response>"""

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls/{call_sid}.json",
                    auth=(sid, token),
                    data={"Twiml": twiml},
                )
        except Exception:
            logger.exception("[campaign_worker] voicemail error call=%s", call_sid)

    async def _hangup_call(self, call_sid: str, campaign) -> None:
        """Immediately hang up a call via Twilio REST API."""
        sid, token = await self._resolve_twilio_creds(campaign.tenantId)
        if not sid or not token:
            return
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls/{call_sid}.json",
                    auth=(sid, token),
                    data={"Status": "completed"},
                )
        except Exception:
            logger.exception("[campaign_worker] hangup error call=%s", call_sid)


# Module-level singleton
campaign_worker = CampaignWorker()
