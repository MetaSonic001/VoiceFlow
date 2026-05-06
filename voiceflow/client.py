"""
VoiceFlowClient — async REST client for the hosted VoiceFlow platform API.

Usage:
    import asyncio
    from voiceflow import VoiceFlowClient

    async def main():
        client = VoiceFlowClient(api_key="vf_live_...")
        agents = await client.list_agents()
        print(agents)

    asyncio.run(main())

All methods raise ``VoiceFlowError`` on non-2xx responses.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


class VoiceFlowError(Exception):
    """Raised when the VoiceFlow API returns a non-2xx status."""
    def __init__(self, status: int, message: str):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status


class VoiceFlowClient:
    """
    Async HTTP client for the VoiceFlow platform REST API.

    Parameters
    ----------
    api_key:
        Your VoiceFlow API key (also readable from ``VOICEFLOW_API_KEY`` env var).
    base_url:
        Override the API base URL (default: ``https://api.voiceflow.ai``).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.voiceflow.ai",
    ):
        self.api_key = api_key or os.environ.get("VOICEFLOW_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "api_key is required. Pass it directly or set VOICEFLOW_API_KEY."
            )
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> Any:
        try:
            import httpx
        except ImportError as exc:
            raise ImportError(
                "httpx is required for VoiceFlowClient: pip install httpx"
            ) from exc

        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.request(method, url, headers=self._headers(), **kwargs)

        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise VoiceFlowError(resp.status_code, detail)

        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    # ------------------------------------------------------------------ #
    # Agents                                                               #
    # ------------------------------------------------------------------ #

    async def list_agents(self) -> List[Dict]:
        """Return all agents for your account."""
        return await self._request("GET", "/v1/agents")

    async def get_agent(self, agent_id: str) -> Dict:
        """Fetch a single agent by ID."""
        return await self._request("GET", f"/v1/agents/{agent_id}")

    async def create_agent(
        self,
        name: str,
        system_prompt: str,
        language: str = "en-US",
        voice_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict:
        """
        Create a new agent.

        Parameters
        ----------
        name:          Human-readable agent name.
        system_prompt: The persona / instruction prompt.
        language:      BCP-47 language code (default ``en-US``).
        voice_id:      Optional TTS voice identifier.
        **kwargs:      Any additional fields passed through to the API.
        """
        payload: Dict[str, Any] = {
            "name": name,
            "systemPrompt": system_prompt,
            "language": language,
            **kwargs,
        }
        if voice_id:
            payload["voiceId"] = voice_id
        return await self._request("POST", "/v1/agents", json=payload)

    async def update_agent(self, agent_id: str, **kwargs: Any) -> Dict:
        """Partial-update an agent with the provided keyword fields."""
        return await self._request("PATCH", f"/v1/agents/{agent_id}", json=kwargs)

    async def delete_agent(self, agent_id: str) -> Dict:
        """Permanently delete an agent. Returns ``{}`` on success."""
        return await self._request("DELETE", f"/v1/agents/{agent_id}")

    # ------------------------------------------------------------------ #
    # Knowledge Base                                                       #
    # ------------------------------------------------------------------ #

    async def upload_knowledge(
        self,
        agent_id: str,
        file_path: str,
        *,
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> Dict:
        """
        Upload a document (PDF, TXT, DOCX, MD) to an agent's knowledge base.

        The file is streamed as ``multipart/form-data``.
        """
        try:
            import httpx
        except ImportError as exc:
            raise ImportError("httpx is required: pip install httpx") from exc

        url = f"{self.base_url}/v1/agents/{agent_id}/knowledge"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        with open(file_path, "rb") as fh:
            async with httpx.AsyncClient(timeout=120) as http:
                resp = await http.post(
                    url,
                    headers=headers,
                    files={"file": (os.path.basename(file_path), fh)},
                    data={"chunkSize": chunk_size, "overlap": overlap},
                )

        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise VoiceFlowError(resp.status_code, detail)
        return resp.json()

    async def list_knowledge(self, agent_id: str) -> List[Dict]:
        """List all knowledge base documents for an agent."""
        return await self._request("GET", f"/v1/agents/{agent_id}/knowledge")

    async def delete_knowledge(self, agent_id: str, doc_id: str) -> Dict:
        """Remove a single document from the knowledge base."""
        return await self._request(
            "DELETE", f"/v1/agents/{agent_id}/knowledge/{doc_id}"
        )

    # ------------------------------------------------------------------ #
    # Calls                                                                #
    # ------------------------------------------------------------------ #

    async def make_call(
        self,
        agent_id: str,
        to_number: str,
        from_number: str,
        *,
        variables: Optional[Dict[str, str]] = None,
        campaign_id: Optional[str] = None,
    ) -> Dict:
        """
        Initiate an outbound call from the given agent.

        Parameters
        ----------
        agent_id:    The agent that will handle the call.
        to_number:   Destination phone in E.164 format (e.g. ``+14155550100``).
        from_number: Caller ID in E.164 format.
        variables:   Optional dict of variables injected into the agent prompt.
        campaign_id: Attach the call to a campaign for tracking.
        """
        payload: Dict[str, Any] = {
            "agentId": agent_id,
            "to": to_number,
            "from": from_number,
        }
        if variables:
            payload["variables"] = variables
        if campaign_id:
            payload["campaignId"] = campaign_id
        return await self._request("POST", "/v1/calls/outbound", json=payload)

    async def get_call_logs(
        self,
        agent_id: Optional[str] = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        """
        Retrieve call logs, optionally filtered by agent.

        Parameters
        ----------
        agent_id: Filter logs to a specific agent.
        limit:    Maximum records to return (default 50).
        offset:   Pagination offset.
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if agent_id:
            params["agentId"] = agent_id
        return await self._request("GET", "/v1/calls", params=params)

    async def get_call(self, call_id: str) -> Dict:
        """Fetch the full detail for a single call log entry."""
        return await self._request("GET", f"/v1/calls/{call_id}")

    # ------------------------------------------------------------------ #
    # Webhooks                                                             #
    # ------------------------------------------------------------------ #

    async def list_webhooks(self, agent_id: str) -> List[Dict]:
        """List configured post-call webhooks for an agent."""
        return await self._request("GET", f"/v1/agents/{agent_id}/webhooks")

    async def create_webhook(
        self,
        agent_id: str,
        url: str,
        *,
        secret: Optional[str] = None,
        events: Optional[List[str]] = None,
    ) -> Dict:
        """
        Register a new post-call webhook.

        Parameters
        ----------
        url:    The HTTPS endpoint that will receive the event POST.
        secret: Optional HMAC-SHA256 signing secret.
        events: List of event names to subscribe to. Defaults to all events.
        """
        payload: Dict[str, Any] = {"url": url}
        if secret:
            payload["secret"] = secret
        if events:
            payload["events"] = events
        return await self._request(
            "POST", f"/v1/agents/{agent_id}/webhooks", json=payload
        )

    async def delete_webhook(self, agent_id: str, webhook_id: str) -> Dict:
        """Remove a webhook subscription."""
        return await self._request(
            "DELETE", f"/v1/agents/{agent_id}/webhooks/{webhook_id}"
        )
