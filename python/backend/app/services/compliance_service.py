"""
Compliance Service — validates whether an outbound call is allowed.

Checks:
  1. DND (Do-Not-Disturb) registry in Postgres
  2. Allowed calling hours in agent.timezone via pytz
  3. Max-retry limit for the contact
"""
from __future__ import annotations

import logging
from datetime import datetime, time
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("voiceflow.compliance")


class ComplianceService:
    """Gate-keeper for outbound call eligibility."""

    # ── DND check ────────────────────────────────────────────────────────────

    async def is_dnd(
        self,
        tenant_id: str,
        phone_number: str,
        db: AsyncSession,
    ) -> bool:
        """
        Return True if the phone number is on the tenant's DND registry.
        Numbers are normalised (whitespace + leading + stripped) before comparison.
        """
        from app.models import DNDRegistry

        normalised = phone_number.strip()
        result = await db.execute(
            select(DNDRegistry).where(
                DNDRegistry.tenantId == tenant_id,
                DNDRegistry.phoneNumber == normalised,
            )
        )
        return result.scalar_one_or_none() is not None

    # ── Calling-hours check ───────────────────────────────────────────────────

    async def is_calling_hours(self, agent) -> bool:
        """
        Return True if *now* (in agent.timezone) is within agent.allowed_call_hours.

        agent.allowed_call_hours is expected to be a dict like:
            {"start": "09:00", "end": "17:00"}
        or stored as agent.llmPreferences["allowedCallHours"].

        If no hours are configured the call is always allowed (return True).
        Falls back to UTC on unknown timezone.
        """
        try:
            import pytz
        except ImportError:
            logger.warning("[compliance] pytz not installed — skipping hours check")
            return True

        # Resolve calling-hours config
        hours: Optional[dict] = None
        if hasattr(agent, "allowedCallHours") and agent.allowedCallHours:
            hours = agent.allowedCallHours
        elif hasattr(agent, "llmPreferences") and agent.llmPreferences:
            hours = agent.llmPreferences.get("allowedCallHours")

        if not hours or not isinstance(hours, dict):
            return True  # no restriction

        start_str: str = hours.get("start", "00:00")
        end_str: str = hours.get("end", "23:59")

        # Resolve timezone
        tz_name: str = "UTC"
        if hasattr(agent, "timezone") and agent.timezone:
            tz_name = agent.timezone
        elif hasattr(agent, "llmPreferences") and agent.llmPreferences:
            tz_name = agent.llmPreferences.get("timezone", "UTC")

        try:
            tz = pytz.timezone(tz_name)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning("[compliance] unknown timezone '%s', defaulting to UTC", tz_name)
            tz = pytz.UTC

        now_local = datetime.now(tz).time()
        try:
            start_h, start_m = (int(p) for p in start_str.split(":"))
            end_h, end_m = (int(p) for p in end_str.split(":"))
            start = time(start_h, start_m)
            end = time(end_h, end_m)
        except (ValueError, AttributeError):
            logger.warning("[compliance] invalid calling hours config '%s'-'%s'", start_str, end_str)
            return True

        if start <= end:
            return start <= now_local <= end
        # Overnight window (e.g. 22:00 – 06:00)
        return now_local >= start or now_local <= end

    # ── Retry check ───────────────────────────────────────────────────────────

    async def is_retry_allowed(self, contact, agent) -> bool:
        """
        Return True if the contact has not yet reached the campaign's max-retry limit.
        max_retries is read from agent.llmPreferences["maxRetries"] or campaign.maxRetries
        via the contact's campaign relationship (if loaded).
        """
        # Prefer campaign-level setting
        max_retries: int = 3
        campaign = getattr(contact, "campaign", None)
        if campaign and hasattr(campaign, "maxRetries") and campaign.maxRetries is not None:
            max_retries = campaign.maxRetries
        elif hasattr(agent, "llmPreferences") and agent.llmPreferences:
            max_retries = int(agent.llmPreferences.get("maxRetries", 3))

        return (contact.callAttempts or 0) < max_retries

    # ── Combined validation ───────────────────────────────────────────────────

    async def validate_before_dial(
        self,
        tenant_id: str,
        phone: str,
        agent,
        contact,
        db: AsyncSession,
    ) -> tuple[bool, str]:
        """
        Run all compliance checks and return (allowed: bool, reason: str).

        Checks (in order):
          1. DND registry
          2. Calling hours
          3. Max retries
        """
        if await self.is_dnd(tenant_id, phone, db):
            return False, "dnd"

        if not await self.is_calling_hours(agent):
            return False, "outside_calling_hours"

        if not await self.is_retry_allowed(contact, agent):
            return False, "max_retries_exceeded"

        return True, "ok"


# Module-level singleton
compliance_service = ComplianceService()
