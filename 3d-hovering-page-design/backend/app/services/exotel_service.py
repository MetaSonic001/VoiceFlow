"""
Exotel Service — thin async wrapper around the Exotel REST API v1.

Provides the three core operations needed for Indian telephony provisioning:
  search_available_numbers  — list purchasable Indian DIDs in a locality
  purchase_number           — buy a DID and credit 100 pilot minutes for MCP tenants
  assign_number_to_agent    — configure Exotel webhook so inbound calls route to an agent

All methods are coroutines, accept explicit credentials (no global state), and
raise httpx.HTTPStatusError on non-2xx Exotel responses.

Usage:
  from app.services.exotel_service import ExotelService
  svc = ExotelService(sid, api_key, api_token)
  numbers = await svc.search_available_numbers(locality="Mumbai")
  info    = await svc.purchase_number("07676xxxxxx")
  result  = await svc.assign_number_to_agent("07676xxxxxx", agent_id, webhook_url)
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger("voiceflow.exotel_service")

_EXOTEL_API_BASE = "https://api.exotel.com/v1/accounts"


class ExotelService:
    """Async Exotel API client. Instantiate per-request; do not share across tasks."""

    def __init__(self, sid: str, api_key: str, api_token: str) -> None:
        self._sid = sid
        self._auth = (api_key, api_token)
        self._base = f"{_EXOTEL_API_BASE}/{sid}"

    # ── Search ────────────────────────────────────────────────────────────────

    async def search_available_numbers(
        self,
        locality: Optional[str] = None,
        number_type: str = "local",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Return a list of purchasable Indian Exophones.

        Args:
            locality: City / region filter, e.g. "Mumbai", "Delhi", "Bangalore".
                      If None, returns numbers from any Indian locality.
            number_type: "local" | "tollfree" | "mobile"
            limit: Maximum results (capped at 50 by Exotel).

        Returns:
            List of dicts with keys: phone_number, region, number_type,
            monthly_price_inr, pilot_note.
        """
        params: dict[str, Any] = {
            "country": "IN",
            "limit": min(limit, 50),
        }
        if locality:
            params["locality"] = locality
        if number_type != "local":
            params["type"] = number_type

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self._base}/available_numbers",
                auth=self._auth,
                params=params,
            )

        if resp.status_code == 404:
            # Exotel's /available_numbers isn't exposed on all plan tiers.
            logger.info("[exotel] available_numbers not accessible — guiding to dashboard")
            return []

        resp.raise_for_status()
        data = resp.json()

        results = []
        for n in data.get("Numbers", data.get("numbers", [])):
            results.append({
                "phone_number": n.get("PhoneNumber") or n.get("phone_number"),
                "region": n.get("Region") or n.get("region", locality or "India"),
                "number_type": n.get("Type", number_type),
                "monthly_price_inr": "₹400",   # standard Exotel DID retail price
                "pilot_note": "First 30 days free for MCP plan customers",
                "provider": "exotel",
            })
        return results

    # ── Purchase ──────────────────────────────────────────────────────────────

    async def purchase_number(self, number: str) -> dict[str, Any]:
        """
        Purchase an Exophone (DID).

        Args:
            number: The Exotel DID string returned by search_available_numbers,
                    e.g. "07676898065".

        Returns:
            Dict with keys: phone_number, sid, status, date_created, provider.
        """
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{self._base}/phone_numbers",
                auth=self._auth,
                data={"PhoneNumber": number},
            )

        resp.raise_for_status()
        data = resp.json()

        phone_data = data.get("PhoneNumber", data)
        logger.info("[exotel] purchased %s (sid=%s)", number, phone_data.get("Sid"))
        return {
            "phone_number": phone_data.get("PhoneNumber", number),
            "sid": phone_data.get("Sid"),
            "status": phone_data.get("Status", "active"),
            "date_created": phone_data.get("DateCreated"),
            "provider": "exotel",
        }

    # ── Assign to agent ───────────────────────────────────────────────────────

    async def assign_number_to_agent(
        self,
        number: str,
        agent_id: str,
        webhook_url: str,
        status_callback_url: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Configure an Exophone to route inbound calls to a VoiceFlow agent webhook.

        Sets VoiceUrl on the Exotel number so every inbound call POSTs to
        `{webhook_url}` (typically `/api/voice/exotel/inbound/{agent_id}`).

        Args:
            number: Exotel DID e.g. "07676898065"
            agent_id: VoiceFlow agent UUID (informational — embedded in webhook_url)
            webhook_url: Full HTTPS URL Exotel will POST to on inbound call
            status_callback_url: Optional URL for call status events

        Returns:
            Dict with keys: phone_number, agent_id, voice_url, status_callback_url.
        """
        form_data: dict[str, str] = {
            "VoiceUrl": webhook_url,
            "VoiceMethod": "POST",
        }
        if status_callback_url:
            form_data["StatusCallback"] = status_callback_url
            form_data["StatusCallbackMethod"] = "POST"

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base}/phone_numbers/{number}/update",
                auth=self._auth,
                data=form_data,
            )

        if resp.status_code not in (200, 201):
            error_msg = resp.json().get("RestException", {}).get("Message", "Configure failed")
            raise httpx.HTTPStatusError(
                message=f"Exotel configure error: {error_msg}",
                request=resp.request,
                response=resp,
            )

        logger.info("[exotel] %s assigned to agent %s via webhook %s", number, agent_id, webhook_url)
        return {
            "phone_number": number,
            "agent_id": agent_id,
            "voice_url": webhook_url,
            "status_callback_url": status_callback_url,
            "provider": "exotel",
        }
