"""
Auto-Retry Campaign Service — configurable retry state machine.

When a call fails (no answer, busy, voicemail, error), this service
schedules a retry attempt using a Redis sorted set (score = retry_timestamp).

Rules respected:
  1. Max retries (Campaign.maxRetries, per-contact)
  2. Calling hours (Campaign.allowedCallHours, per tenant timezone)
  3. DND registry (ComplianceService.validate_before_dial)
  4. Min delay between retries (default 30 min, configurable per campaign)
  5. Never retry between 9pm–8am

Redis keys:
  retryqueue:{tenant_id}   — ZSET, score=unix_retry_time, member=contact_id

Background task: scan_and_retry() polls every 60s and dispatches due retries.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger("voiceflow.auto_retry")

_RETRY_QUEUE_KEY = "retryqueue:{tenant_id}"
_RETRY_MIN_DELAY_SECONDS = int(settings.__dict__.get("CAMPAIGN_RETRY_DELAY_SECONDS", 1800))  # 30 min default


def _redis() -> aioredis.Redis:
    return aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=4,
        decode_responses=True,
    )


async def schedule_retry(
    tenant_id: str,
    contact_id: str,
    campaign_id: str,
    delay_seconds: Optional[int] = None,
) -> None:
    """
    Schedule a retry for a failed contact.
    Stores contact_id with a retry_time score in the per-tenant ZSET.
    """
    delay = delay_seconds or _RETRY_MIN_DELAY_SECONDS
    retry_at = time.time() + delay
    payload = json.dumps({"contact_id": contact_id, "campaign_id": campaign_id})
    redis = _redis()
    try:
        queue_key = _RETRY_QUEUE_KEY.format(tenant_id=tenant_id)
        await redis.zadd(queue_key, {payload: retry_at})
        await redis.expire(queue_key, 86400 * 7)  # 7-day TTL on queue
        logger.info("[auto_retry] scheduled retry contact=%s at +%ds", contact_id, delay)
    finally:
        await redis.aclose()


async def cancel_retry(tenant_id: str, contact_id: str) -> None:
    """Remove all pending retries for a contact (e.g. if called manually)."""
    redis = _redis()
    try:
        queue_key = _RETRY_QUEUE_KEY.format(tenant_id=tenant_id)
        # Scan members for this contact_id
        all_members = await redis.zrange(queue_key, 0, -1)
        to_remove = [m for m in all_members if contact_id in m]
        if to_remove:
            await redis.zrem(queue_key, *to_remove)
    finally:
        await redis.aclose()


async def _is_within_calling_hours(
    allowed_call_hours: Optional[dict], tz_name: str
) -> bool:
    """
    Return True if current time is within the campaign's calling window.
    Also enforces a hard 8am–9pm window for caller protection.
    """
    try:
        import pytz
        tz = pytz.timezone(tz_name or "UTC")
        now_local = datetime.now(tz)
    except Exception:
        now_local = datetime.now(timezone.utc)

    hour = now_local.hour
    # Hard boundary: never call before 8am or after 9pm
    if hour < 8 or hour >= 21:
        return False
    if not allowed_call_hours:
        return True
    try:
        start_h, start_m = map(int, allowed_call_hours.get("start", "08:00").split(":"))
        end_h, end_m = map(int, allowed_call_hours.get("end", "21:00").split(":"))
        start_min = start_h * 60 + start_m
        end_min = end_h * 60 + end_m
        current_min = hour * 60 + now_local.minute
        return start_min <= current_min < end_min
    except Exception:
        return True


async def scan_and_retry(tenant_id: str) -> int:
    """
    Poll the retry queue for contacts due for retry.
    Called by the background scheduler.  Returns the number of retries dispatched.
    """
    from app.database import AsyncSessionLocal
    from app.models import Campaign, CampaignContact
    from app.services.compliance_service import compliance_service
    from app.services.campaign_worker import campaign_worker
    from sqlalchemy import select

    now = time.time()
    redis = _redis()
    dispatched = 0

    try:
        queue_key = _RETRY_QUEUE_KEY.format(tenant_id=tenant_id)
        # Fetch all entries due by now
        due = await redis.zrangebyscore(queue_key, 0, now, withscores=False)
        if not due:
            return 0

        for payload_str in due:
            try:
                payload = json.loads(payload_str)
                contact_id = payload.get("contact_id")
                campaign_id = payload.get("campaign_id")
            except Exception:
                await redis.zrem(queue_key, payload_str)
                continue

            async with AsyncSessionLocal() as db:
                c_result = await db.execute(
                    select(CampaignContact).where(CampaignContact.id == contact_id)
                )
                contact = c_result.scalar_one_or_none()
                camp_result = await db.execute(
                    select(Campaign).where(Campaign.id == campaign_id)
                )
                campaign = camp_result.scalar_one_or_none()

                if not contact or not campaign:
                    await redis.zrem(queue_key, payload_str)
                    continue

                # Check calling hours
                in_hours = await _is_within_calling_hours(
                    campaign.allowedCallHours, campaign.timezone or "UTC"
                )
                if not in_hours:
                    # Defer by 15 min — will check again
                    new_score = now + 900
                    await redis.zadd(queue_key, {payload_str: new_score})
                    logger.debug("[auto_retry] deferred (outside hours) contact=%s", contact_id)
                    continue

                # Check max retries
                if (contact.callAttempts or 0) >= (campaign.maxRetries or 3):
                    contact.status = "failed"
                    contact.updatedAt = datetime.now(timezone.utc)
                    await db.commit()
                    await redis.zrem(queue_key, payload_str)
                    continue

                # Compliance check (DND etc.)
                agent_result = await db.execute(
                    select(
                        __import__("app.models", fromlist=["Agent"]).Agent
                    ).where(
                        __import__("app.models", fromlist=["Agent"]).Agent.id == campaign.agentId
                    )
                )
                agent = agent_result.scalar_one_or_none()
                if not agent:
                    await redis.zrem(queue_key, payload_str)
                    continue

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
                    await db.commit()
                    await redis.zrem(queue_key, payload_str)
                    logger.info("[auto_retry] DND/compliance block contact=%s reason=%s", contact_id, reason)
                    continue

                # Reset to pending and re-enqueue for the campaign worker
                contact.status = "pending"
                contact.updatedAt = datetime.now(timezone.utc)
                await db.commit()

                # Push back into the campaign Redis queue
                import redis as sync_redis_lib
                campaign_redis = aioredis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=3,
                    decode_responses=True,
                )
                await campaign_redis.rpush(f"campaign:{campaign_id}:queue", contact_id)
                await campaign_redis.aclose()

                await redis.zrem(queue_key, payload_str)
                dispatched += 1
                logger.info("[auto_retry] dispatched retry for contact=%s campaign=%s attempt=%d",
                            contact_id, campaign_id, contact.callAttempts)

    finally:
        await redis.aclose()

    return dispatched


# ── Background scheduler loop ──────────────────────────────────────────────────

_retry_tasks: dict[str, asyncio.Task] = {}


async def start_retry_scheduler(tenant_id: str) -> None:
    """Start the auto-retry background loop for a tenant if not already running."""
    if tenant_id in _retry_tasks and not _retry_tasks[tenant_id].done():
        return

    async def _loop():
        while True:
            try:
                count = await scan_and_retry(tenant_id)
                if count:
                    logger.info("[auto_retry] dispatched %d retries for tenant %s", count, tenant_id)
            except Exception as exc:
                logger.warning("[auto_retry] scheduler error: %s", exc)
            await asyncio.sleep(60)  # poll every 60s

    task = asyncio.create_task(_loop())
    _retry_tasks[tenant_id] = task
    logger.info("[auto_retry] scheduler started for tenant %s", tenant_id)
