"""
Webhook Service — HMAC-signed event dispatch to external HTTP endpoints.

Supported events
----------------
  call.completed         — fired by voice pipeline on call end
  campaign.finished      — fired by campaign worker on completion
  escalation.triggered   — fired by agent when escalation rule matches
  retraining.flagged     — fired when a call is flagged for retraining

Delivery guarantees
-------------------
  • Fire-and-forget async HTTP POST
  • HMAC-SHA256 signature in X-VoiceFlow-Signature header (sha256=<hex>)
  • 3 retries with exponential backoff (1s, 2s, 4s)
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger("voiceflow.webhooks")

# Supported event types
SUPPORTED_EVENTS = {
    "call.completed",
    "campaign.finished",
    "escalation.triggered",
    "retraining.flagged",
}

_RETRY_DELAYS = (1.0, 2.0, 4.0)  # seconds between retries


class WebhookService:
    """Dispatch signed webhook events to registered endpoints."""

    # ── HMAC signing ─────────────────────────────────────────────────────────

    @staticmethod
    def _sign_payload(secret: str, body: str) -> str:
        """Return 'sha256=<hexdigest>' HMAC-SHA256 of *body* signed with *secret*."""
        sig = hmac.new(
            secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={sig}"

    # ── Single delivery attempt ───────────────────────────────────────────────

    async def _deliver(
        self,
        url: str,
        body: str,
        signature: str,
    ) -> bool:
        """Send a single HTTP POST.  Returns True on HTTP 2xx."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    url,
                    content=body.encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "X-VoiceFlow-Signature": signature,
                        "X-VoiceFlow-Event": "webhook",
                    },
                )
            if 200 <= resp.status_code < 300:
                return True
            logger.warning("[webhook] delivery returned %s url=%s", resp.status_code, url)
        except Exception as exc:
            logger.warning("[webhook] delivery error url=%s: %s", url, exc)
        return False

    # ── Retry loop ────────────────────────────────────────────────────────────

    async def _deliver_with_retry(
        self,
        endpoint,  # WebhookEndpoint ORM object
        body: str,
    ) -> None:
        """Attempt delivery up to 3 times with exponential back-off."""
        signature = self._sign_payload(endpoint.secret, body)
        for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
            if await self._deliver(endpoint.url, body, signature):
                logger.info(
                    "[webhook] delivered event to %s (attempt %d)", endpoint.url, attempt
                )
                return
            if attempt < len(_RETRY_DELAYS):
                await asyncio.sleep(delay)
        logger.error("[webhook] all delivery attempts failed for endpoint=%s", endpoint.id)

    # ── Public dispatch ───────────────────────────────────────────────────────

    async def dispatch(
        self,
        tenant_id: str,
        event: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Look up all active WebhookEndpoints that subscribe to *event* and fire
        them concurrently as background tasks.

        Silently ignores unknown events.
        """
        if event not in SUPPORTED_EVENTS:
            logger.debug("[webhook] unsupported event '%s' — skipping dispatch", event)
            return

        from app.database import AsyncSessionLocal
        from app.models import WebhookEndpoint
        from sqlalchemy import select

        body = json.dumps({"event": event, "tenantId": tenant_id, **payload})

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(WebhookEndpoint).where(
                    WebhookEndpoint.tenantId == tenant_id,
                    WebhookEndpoint.isActive.is_(True),
                )
            )
            endpoints = result.scalars().all()

        matching = [ep for ep in endpoints if event in (ep.events or [])]
        if not matching:
            logger.debug("[webhook] no active endpoints for event='%s' tenant=%s", event, tenant_id)
            return

        # Fire all matching endpoints concurrently (each has its own retry loop)
        tasks = [
            asyncio.create_task(self._deliver_with_retry(ep, body))
            for ep in matching
        ]
        await asyncio.gather(*tasks, return_exceptions=True)


# Module-level singleton
webhook_service = WebhookService()
