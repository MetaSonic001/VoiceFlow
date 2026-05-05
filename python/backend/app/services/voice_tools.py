"""
Voice Tools — live function calling during voice calls.

Provides a registry of callable external integrations (CRM, calendar, SMS, DTMF,
warm transfer, real-time web search) that the orchestrator can invoke mid-conversation.

Real-time web search uses DuckDuckGo (no API key required) so agents can answer
live questions like "what's today's gold price?" or "current HDFC home loan rate?"
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger("voiceflow.voice_tools")

_DDGS_AVAILABLE = False
try:
    from duckduckgo_search import DDGS  # noqa: F401
    _DDGS_AVAILABLE = True
    logger.info("[voice_tools] duckduckgo-search available — live web search enabled")
except ImportError:
    logger.info("[voice_tools] duckduckgo-search not installed — web search disabled")


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class VoiceTool:
    """Descriptor for an external API that can be called during a voice conversation."""

    name: str
    description: str
    url: str
    method: str                             # GET | POST | PATCH | PUT | DELETE
    headers: dict = field(default_factory=dict)
    parameters: list[dict] = field(default_factory=list)
    # e.g. [{"name": "order_id", "type": "string", "required": True}]


# ── Pre-built tool registry ───────────────────────────────────────────────────

BUILT_IN_TOOLS: list[VoiceTool] = [
    VoiceTool(
        name="book_appointment",
        description="Schedule an appointment via the calendar API.",
        url="",  # Configured per-tenant via agent settings
        method="POST",
        parameters=[
            {"name": "name", "type": "string", "required": True},
            {"name": "email", "type": "string", "required": False},
            {"name": "datetime_utc", "type": "string", "required": True},
            {"name": "duration_minutes", "type": "integer", "required": False},
        ],
    ),
    VoiceTool(
        name="lookup_crm",
        description="Look up a customer record by phone number.",
        url="",
        method="GET",
        parameters=[
            {"name": "phone", "type": "string", "required": True},
        ],
    ),
    VoiceTool(
        name="send_sms",
        description="Send an SMS to the caller.",
        url="https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
        method="POST",
        parameters=[
            {"name": "to", "type": "string", "required": True},
            {"name": "body", "type": "string", "required": True},
        ],
    ),
    VoiceTool(
        name="capture_dtmf",
        description="Ask the caller to press digits (e.g., confirmation code).",
        url="",  # Handled inline via TwiML <Gather input='dtmf'>
        method="POST",
        parameters=[
            {"name": "prompt", "type": "string", "required": True},
            {"name": "num_digits", "type": "integer", "required": False},
        ],
    ),
    VoiceTool(
        name="update_lead",
        description="Update a CRM lead status.",
        url="",
        method="PATCH",
        parameters=[
            {"name": "lead_id", "type": "string", "required": True},
            {"name": "status", "type": "string", "required": True},
            {"name": "notes", "type": "string", "required": False},
        ],
    ),
    VoiceTool(
        name="transfer_call",
        description="Warm transfer the active call to a human agent.",
        url="",  # Handled via Twilio REST API
        method="POST",
        parameters=[
            {"name": "transfer_to", "type": "string", "required": True},
            {"name": "whisper_message", "type": "string", "required": False},
        ],
    ),
    VoiceTool(
        name="web_search",
        description="Search the web in real-time for current information (prices, news, rates, hours, etc.).",
        url="__builtin__",  # Handled by VoiceToolExecutor._execute_web_search
        method="GET",
        parameters=[
            {"name": "query", "type": "string", "required": True},
        ],
    ),
]

# Quick lookup by name
TOOL_REGISTRY: dict[str, VoiceTool] = {t.name: t for t in BUILT_IN_TOOLS}


# ── Executor ──────────────────────────────────────────────────────────────────

class VoiceToolExecutor:
    """
    Execute voice tool calls and provide filler audio while the API call is in flight.
    """

    def __init__(self) -> None:
        # Cache filler mulaw bytes per tool name to avoid re-synthesising on every call
        self._filler_cache: dict[str, bytes] = {}

    async def execute(self, tool: VoiceTool, arguments: dict) -> dict:
        """
        Call the external API described by *tool* with *arguments*.
        Returns the parsed JSON response or an error dict.
        """
        # Built-in tools handled locally
        if tool.name == "web_search":
            return await self._execute_web_search(arguments)

        if not tool.url:
            logger.warning("[voice_tools] tool '%s' has no URL configured", tool.name)
            return {"error": f"Tool '{tool.name}' is not configured yet."}

        method = tool.method.upper()
        headers = {"Content-Type": "application/json", **tool.headers}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                if method == "GET":
                    resp = await client.get(tool.url, headers=headers, params=arguments)
                elif method == "POST":
                    resp = await client.post(tool.url, headers=headers, json=arguments)
                elif method == "PATCH":
                    resp = await client.patch(tool.url, headers=headers, json=arguments)
                elif method == "PUT":
                    resp = await client.put(tool.url, headers=headers, json=arguments)
                elif method == "DELETE":
                    resp = await client.delete(tool.url, headers=headers, params=arguments)
                else:
                    return {"error": f"Unsupported HTTP method: {method}"}

                if resp.status_code in (200, 201, 204):
                    try:
                        return resp.json()
                    except Exception:
                        return {"status": "ok", "status_code": resp.status_code}
                else:
                    logger.warning(
                        "[voice_tools] tool='%s' returned %s", tool.name, resp.status_code
                    )
                    return {
                        "error": f"API returned {resp.status_code}",
                        "body": resp.text[:200],
                    }

        except httpx.TimeoutException:
            logger.warning("[voice_tools] tool='%s' timed out", tool.name)
            return {"error": "Request timed out"}
        except Exception as exc:
            logger.exception("[voice_tools] tool='%s' unexpected error", tool.name)
            return {"error": str(exc)}

    async def _execute_web_search(self, arguments: dict) -> dict:
        """
        Real-time web search using DuckDuckGo (no API key needed).
        Returns top-3 snippets concatenated as a string for LLM context injection.

        This mirrors OmniDimension's live web search tool — agents can now answer
        "What's the current gold price?", "Today's HDFC home loan rate?", etc.
        """
        query = arguments.get("query", "").strip()
        if not query:
            return {"error": "query is required"}
        if not _DDGS_AVAILABLE:
            return {"error": "Web search not available. Install duckduckgo-search: pip install duckduckgo-search"}

        def _search() -> list[dict]:
            from duckduckgo_search import DDGS
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=3):
                    results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", ""),
                    })
            return results

        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, _search)
            if not results:
                return {"answer": "No results found.", "sources": []}
            # Format into a concise summary the LLM can consume inline
            answer_parts = []
            for r in results:
                if r["snippet"]:
                    answer_parts.append(f"{r['title']}: {r['snippet']}")
            return {
                "answer": "\n".join(answer_parts),
                "sources": [r["url"] for r in results if r["url"]],
            }
        except Exception as exc:
            logger.warning("[voice_tools] web search failed: %s", exc)
            return {"error": f"Web search failed: {exc}"}

    async def get_filler_audio(self, tool_name: str) -> bytes:
        """
        Return brief μ-law 8kHz mono audio to play while an API call is executing.
        Result is cached after first synthesis.
        """
        if tool_name in self._filler_cache:
            return self._filler_cache[tool_name]

        filler_text = _FILLER_PHRASES.get(tool_name, "One moment please.")

        from app.services.tts_router import TTSRouter

        tts = TTSRouter()
        try:
            mulaw = await tts.synthesize_mulaw(
                text=filler_text,
                engine="kokoro",
                voice_id="af_bella",
            )
        except Exception:
            logger.warning(
                "[voice_tools] filler TTS failed for '%s', using empty bytes", tool_name
            )
            mulaw = b""

        self._filler_cache[tool_name] = mulaw
        return mulaw


# ── Filler phrase map ─────────────────────────────────────────────────────────

_FILLER_PHRASES: dict[str, str] = {
    "book_appointment": "Let me check the calendar for you, just one moment.",
    "lookup_crm": "Let me pull up your account, one moment please.",
    "send_sms": "Sending that to you now, just a second.",
    "capture_dtmf": "Please enter the digits using your keypad.",
    "update_lead": "Updating your information, one moment.",
    "transfer_call": "Let me connect you with one of our specialists, please hold.",
    "web_search": "Let me look that up for you, one moment.",
}

# Module-level singleton
voice_tool_executor = VoiceToolExecutor()
