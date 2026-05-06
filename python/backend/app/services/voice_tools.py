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
    VoiceTool(
        name="check_calcom_availability",
        description="Check available appointment slots on Cal.com for the configured event type.",
        url="__calcom__",
        method="GET",
        parameters=[
            {"name": "date", "type": "string", "required": True,  # ISO date YYYY-MM-DD
             "description": "The date to check availability for (YYYY-MM-DD)"},
        ],
    ),
    VoiceTool(
        name="book_calcom_appointment",
        description="Book an appointment via Cal.com.",
        url="__calcom__",
        method="POST",
        parameters=[
            {"name": "name", "type": "string", "required": True},
            {"name": "email", "type": "string", "required": True},
            {"name": "start", "type": "string", "required": True,
             "description": "ISO 8601 datetime e.g. 2025-06-10T10:00:00Z"},
            {"name": "notes", "type": "string", "required": False},
        ],
    ),
    VoiceTool(
        name="check_gcal_availability",
        description="Check Google Calendar free/busy slots for a given time window.",
        url="__gcal__",
        method="GET",
        parameters=[
            {"name": "date", "type": "string", "required": True,
             "description": "ISO date YYYY-MM-DD to check"},
        ],
    ),
    VoiceTool(
        name="book_gcal_appointment",
        description="Create a Google Calendar event.",
        url="__gcal__",
        method="POST",
        parameters=[
            {"name": "summary", "type": "string", "required": True},
            {"name": "start", "type": "string", "required": True,
             "description": "ISO 8601 datetime e.g. 2025-06-10T10:00:00Z"},
            {"name": "end", "type": "string", "required": True},
            {"name": "attendee_email", "type": "string", "required": False},
            {"name": "description", "type": "string", "required": False},
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

    async def execute(self, tool: VoiceTool, arguments: dict, agent_integrations: dict | None = None) -> dict:
        """
        Call the external API described by *tool* with *arguments*.
        Returns the parsed JSON response or an error dict.
        agent_integrations: the agent.integrations dict (contains calcom/gcal keys)
        """
        # Built-in tools handled locally
        if tool.name == "web_search":
            return await self._execute_web_search(arguments)

        if tool.name in ("check_calcom_availability", "book_calcom_appointment"):
            return await self._execute_calcom(tool.name, arguments, agent_integrations or {})

        if tool.name in ("check_gcal_availability", "book_gcal_appointment"):
            return await self._execute_gcal(tool.name, arguments, agent_integrations or {})

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

    async def _execute_calcom(self, action: str, arguments: dict, agent_integrations: dict) -> dict:
        """
        Execute Cal.com v1 API calls for availability checking and booking.
        Reads: agent_integrations.calcom.apiKey + agent_integrations.calcom.eventTypeId
        """
        calcom_cfg = agent_integrations.get("calcom", {})
        api_key = calcom_cfg.get("apiKey", "")
        event_type_id = calcom_cfg.get("eventTypeId", "")
        base = "https://api.cal.com/v1"

        if not api_key:
            return {"error": "Cal.com API key not configured for this agent"}

        try:
            async with httpx.AsyncClient(timeout=12) as client:
                if action == "check_calcom_availability":
                    date = arguments.get("date", "")
                    params = {"apiKey": api_key, "dateFrom": date, "dateTo": date}
                    if event_type_id:
                        params["eventTypeId"] = event_type_id
                    resp = await client.get(f"{base}/slots", params=params)
                    if resp.status_code == 200:
                        slots_data = resp.json()
                        # Flatten slots into a readable list
                        all_slots: list[str] = []
                        for day_slots in slots_data.get("slots", {}).values():
                            for slot in day_slots:
                                all_slots.append(slot.get("time", ""))
                        return {"available_slots": all_slots, "date": date}
                    return {"error": f"Cal.com returned {resp.status_code}", "body": resp.text[:200]}

                elif action == "book_calcom_appointment":
                    booking_payload = {
                        "eventTypeId": int(event_type_id) if event_type_id else None,
                        "start": arguments.get("start", ""),
                        "responses": {
                            "name": arguments.get("name", ""),
                            "email": arguments.get("email", ""),
                            "notes": arguments.get("notes", ""),
                        },
                        "timeZone": "UTC",
                        "language": "en",
                    }
                    resp = await client.post(
                        f"{base}/bookings",
                        params={"apiKey": api_key},
                        json=booking_payload,
                    )
                    if resp.status_code in (200, 201):
                        data = resp.json()
                        return {
                            "booking_id": data.get("uid"),
                            "status": data.get("status"),
                            "start": data.get("startTime"),
                            "end": data.get("endTime"),
                        }
                    return {"error": f"Cal.com booking failed ({resp.status_code})", "body": resp.text[:300]}
        except Exception as exc:
            logger.warning("[voice_tools] Cal.com error: %s", exc)
            return {"error": str(exc)}
        return {"error": "unknown action"}

    async def _execute_gcal(self, action: str, arguments: dict, agent_integrations: dict) -> dict:
        """
        Execute Google Calendar API calls via service account or OAuth2 credentials.
        Reads: agent_integrations.gcal.credentialsJson (service account JSON string)
               agent_integrations.gcal.calendarId (default "primary")
        """
        gcal_cfg = agent_integrations.get("gcal", {})
        credentials_json = gcal_cfg.get("credentialsJson", "")
        calendar_id = gcal_cfg.get("calendarId", "primary")

        if not credentials_json:
            return {"error": "Google Calendar credentials not configured for this agent"}

        try:
            import json as _json

            creds_dict = _json.loads(credentials_json) if isinstance(credentials_json, str) else credentials_json

            def _build_service():
                from google.oauth2 import service_account  # type: ignore
                from googleapiclient.discovery import build  # type: ignore
                scopes = ["https://www.googleapis.com/auth/calendar"]
                creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
                return build("calendar", "v3", credentials=creds)

            loop = asyncio.get_event_loop()

            if action == "check_gcal_availability":
                date = arguments.get("date", "")
                time_min = f"{date}T00:00:00Z"
                time_max = f"{date}T23:59:59Z"

                def _freebusy():
                    svc = _build_service()
                    return svc.freebusy().query(body={
                        "timeMin": time_min,
                        "timeMax": time_max,
                        "items": [{"id": calendar_id}],
                    }).execute()

                data = await loop.run_in_executor(None, _freebusy)
                busy = data.get("calendars", {}).get(calendar_id, {}).get("busy", [])
                return {
                    "date": date,
                    "busy_slots": busy,
                    "available": len(busy) == 0,
                }

            elif action == "book_gcal_appointment":
                event_body = {
                    "summary": arguments.get("summary", "VoiceFlow Appointment"),
                    "description": arguments.get("description", ""),
                    "start": {"dateTime": arguments.get("start"), "timeZone": "UTC"},
                    "end": {"dateTime": arguments.get("end"), "timeZone": "UTC"},
                }
                attendee = arguments.get("attendee_email")
                if attendee:
                    event_body["attendees"] = [{"email": attendee}]

                def _create():
                    svc = _build_service()
                    return svc.events().insert(calendarId=calendar_id, body=event_body).execute()

                event = await loop.run_in_executor(None, _create)
                return {
                    "event_id": event.get("id"),
                    "html_link": event.get("htmlLink"),
                    "start": event.get("start", {}).get("dateTime"),
                }
        except ImportError:
            return {"error": "google-api-python-client not installed. Run: pip install google-api-python-client google-auth"}
        except Exception as exc:
            logger.warning("[voice_tools] GCal error: %s", exc)
            return {"error": str(exc)}
        return {"error": "unknown action"}

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


# ═══════════════════════════════════════════════════════════════════════════════
# Groq-compatible tool spec builder
# ═══════════════════════════════════════════════════════════════════════════════

def get_tools_for_agent(agent_integrations: dict | None = None) -> list[dict]:
    """
    Return a list of Groq/OpenAI-compatible function-call tool specs for
    the tools that are enabled in the given agent_integrations dict.

    Always included: web_search (if duckduckgo-search installed)
    Conditional on agent_integrations keys:
      - calcom.apiKey → check_calcom_availability, book_calcom_appointment
      - gcal.credentialsJson → check_gcal_availability, book_gcal_appointment

    The returned list can be passed directly to Groq's `tools` parameter.
    """
    integrations = agent_integrations or {}
    enabled_names: list[str] = []

    if _DDGS_AVAILABLE:
        enabled_names.append("web_search")

    if integrations.get("calcom", {}).get("apiKey"):
        enabled_names += ["check_calcom_availability", "book_calcom_appointment"]

    if integrations.get("gcal", {}).get("credentialsJson"):
        enabled_names += ["check_gcal_availability", "book_gcal_appointment"]

    tools_spec: list[dict] = []
    for name in enabled_names:
        tool = TOOL_REGISTRY.get(name)
        if not tool:
            continue
        required = [p["name"] for p in tool.parameters if p.get("required")]
        properties = {}
        for p in tool.parameters:
            prop: dict = {"type": p.get("type", "string")}
            if p.get("description"):
                prop["description"] = p["description"]
            properties[p["name"]] = prop
        tools_spec.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        })
    return tools_spec
