"""
Caller Enrichment Service — identify and enrich incoming callers.

Provides caller name, carrier, region, and business info before the call
is answered, so the AI agent can greet by name ("Welcome back, Rahul!")
or reference the caller's context.

Enrichment layers (fastest → most complete):
  1. Local contacts database — instant, returns previous call data
  2. phonenumbers library   — carrier + region metadata (offline, free)
  3. Truecaller Business API — name + profile (requires partner key, paid)

The result is cached in Redis (TTL=24h) to avoid re-querying on every call.

Usage:
    from app.services.caller_enrichment import caller_enrichment, CallerInfo

    info = await caller_enrichment.enrich("+919876543210", tenant_id)
    # info.name → "Rahul Sharma"  (or None)
    # info.carrier → "Airtel India"
    # info.is_returning → True
    # info.previous_calls → 3
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger("voiceflow.caller_enrichment")

# Redis TTL for cached caller info (24 hours)
_CACHE_TTL = 86400


@dataclass
class CallerInfo:
    phone_number: str
    name: Optional[str] = None
    carrier: Optional[str] = None
    region: Optional[str] = None
    country_code: Optional[str] = None
    number_type: Optional[str] = None  # mobile | fixed_line | toll_free | unknown
    is_returning: bool = False
    previous_calls: int = 0
    contact_id: Optional[str] = None
    truecaller_verified: bool = False
    extra: dict = field(default_factory=dict)


class CallerEnrichmentService:
    """
    Enrich an incoming caller's phone number with name, carrier, and history.
    """

    # ── Public entry point ────────────────────────────────────────────────────

    async def enrich(
        self,
        phone_number: str,
        tenant_id: str,
        force_refresh: bool = False,
    ) -> CallerInfo:
        """
        Return enriched caller info. Results are cached for 24h.

        Parameters
        ----------
        phone_number:  E.164 caller number (e.g. "+919876543210")
        tenant_id:     Tenant scope
        force_refresh: Skip cache and re-fetch all layers
        """
        info = CallerInfo(phone_number=phone_number)

        # 1. Redis cache
        if not force_refresh:
            cached = await self._from_cache(phone_number, tenant_id)
            if cached:
                return cached

        # 2. Local contacts DB (instant)
        await self._enrich_from_contacts(info, tenant_id)

        # 3. phonenumbers metadata (offline)
        self._enrich_from_phonenumbers(info)

        # 4. Truecaller (if key configured)
        await self._enrich_from_truecaller(info, tenant_id)

        # Cache the result
        await self._save_cache(info, tenant_id)

        return info

    # ── Layer 1: cached result ────────────────────────────────────────────────

    async def _from_cache(self, phone: str, tenant_id: str) -> Optional[CallerInfo]:
        try:
            from app.config import settings
            import redis.asyncio as aioredis
            r = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=3,
                decode_responses=True,
            )
            key = f"caller_info:{tenant_id}:{phone}"
            raw = await r.get(key)
            await r.aclose()
            if raw:
                d = json.loads(raw)
                return CallerInfo(**d)
        except Exception:
            pass
        return None

    async def _save_cache(self, info: CallerInfo, tenant_id: str) -> None:
        try:
            from app.config import settings
            import redis.asyncio as aioredis
            r = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=3,
                decode_responses=True,
            )
            key = f"caller_info:{tenant_id}:{info.phone_number}"
            await r.setex(key, _CACHE_TTL, json.dumps(asdict(info)))
            await r.aclose()
        except Exception:
            pass

    # ── Layer 2: local contacts + call history ─────────────────────────────

    async def _enrich_from_contacts(self, info: CallerInfo, tenant_id: str) -> None:
        """Check our contacts DB for a pre-existing record."""
        try:
            from app.database import AsyncSessionLocal
            from app.models import Contact, CallLog
            from sqlalchemy import select, func
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Contact).where(
                        Contact.tenantId == tenant_id,
                        Contact.phoneNumber == info.phone_number,
                    )
                )
                contact = result.scalar_one_or_none()
                if contact:
                    info.contact_id = contact.id
                    info.is_returning = True
                    if contact.name:
                        info.name = contact.name
                    if contact.email:
                        info.extra["email"] = contact.email

                # Count previous calls from this number
                count_result = await db.execute(
                    select(func.count()).where(
                        CallLog.tenantId == tenant_id,
                        CallLog.from_ == info.phone_number,
                    )
                )
                count = count_result.scalar() or 0
                info.previous_calls = count
                if count > 0:
                    info.is_returning = True
        except Exception as exc:
            logger.debug("[caller_enrichment] contacts layer: %s", exc)

    # ── Layer 3: phonenumbers metadata ────────────────────────────────────────

    def _enrich_from_phonenumbers(self, info: CallerInfo) -> None:
        """Add carrier, region, and number type from phonenumbers library (offline)."""
        try:
            import phonenumbers
            from phonenumbers import geocoder, carrier, number_type, PhoneNumberType

            parsed = phonenumbers.parse(info.phone_number)
            info.country_code = phonenumbers.region_code_for_number(parsed)

            # Region (city/area)
            geo = geocoder.description_for_number(parsed, "en")
            if geo:
                info.region = geo

            # Carrier
            carr = carrier.name_for_number(parsed, "en")
            if carr:
                info.carrier = carr

            # Number type
            ntype = number_type(parsed)
            type_map = {
                PhoneNumberType.MOBILE: "mobile",
                PhoneNumberType.FIXED_LINE: "fixed_line",
                PhoneNumberType.TOLL_FREE: "toll_free",
                PhoneNumberType.FIXED_LINE_OR_MOBILE: "mobile",
                PhoneNumberType.VOIP: "voip",
                PhoneNumberType.PERSONAL_NUMBER: "personal",
            }
            info.number_type = type_map.get(ntype, "unknown")

        except Exception as exc:
            logger.debug("[caller_enrichment] phonenumbers layer: %s", exc)

    # ── Layer 4: Truecaller Business API ──────────────────────────────────────

    async def _enrich_from_truecaller(self, info: CallerInfo, tenant_id: str) -> None:
        """
        Query the Truecaller Business API if a partner key is configured.

        Settings key: `truecallerPartnerKey` (set in Settings → API Keys)
        Truecaller Business API docs: https://docs.truecaller.com/truecaller-sdk/server-side
        """
        try:
            from app.database import AsyncSessionLocal
            from app.models import Tenant
            from app.services.credentials import decrypt_safe
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
                tenant = result.scalar_one_or_none()

            if not tenant or not tenant.settings:
                return

            key_enc = tenant.settings.get("truecallerPartnerKey")
            if not key_enc:
                return
            api_key = decrypt_safe(key_enc)
            if not api_key:
                return

        except Exception as exc:
            logger.debug("[caller_enrichment] truecaller key lookup: %s", exc)
            return

        # Strip leading "+" for Truecaller API
        number = info.phone_number.lstrip("+")

        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    "https://api4.truecaller.com/v1/bulk",
                    params={"q": number},
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            if resp.status_code == 200:
                data = resp.json()
                # Extract name from Truecaller response shape
                # Shape varies by API version; cover common patterns
                name = (
                    data.get("name")
                    or (data.get("data", [{}])[0] if isinstance(data.get("data"), list) else {}).get("name")
                    or data.get("firstName", "")
                )
                if name and not info.name:
                    info.name = name.strip()
                    info.truecaller_verified = True
                    logger.info(
                        "[caller_enrichment] truecaller name=%s phone=%s",
                        info.name, info.phone_number,
                    )
            elif resp.status_code == 429:
                logger.warning("[caller_enrichment] truecaller rate-limited")
            elif resp.status_code == 401:
                logger.warning("[caller_enrichment] truecaller invalid API key")
        except Exception as exc:
            logger.debug("[caller_enrichment] truecaller API: %s", exc)

    # ── Quick helper ──────────────────────────────────────────────────────────

    def greeting_for(self, info: CallerInfo, agent_name: str = "Assistant") -> str:
        """
        Build a personalised greeting based on enriched caller info.

        Examples:
          "Welcome back, Rahul! You have called us 3 times before."
          "Hello! I'm your AI assistant. How can I help?"
        """
        if info.name and info.is_returning:
            if info.previous_calls > 1:
                return (
                    f"Welcome back, {info.name.split()[0]}! "
                    f"Great to speak with you again. How can I help you today?"
                )
            return (
                f"Hello again, {info.name.split()[0]}! Good to have you back. "
                f"How can I assist you today?"
            )
        if info.name:
            return (
                f"Hello, {info.name.split()[0]}! Welcome. "
                f"How can I help you today?"
            )
        return "Hello! How can I help you today?"


# Module singleton
caller_enrichment = CallerEnrichmentService()
