"""
voiceflow.plugins.telephony — Telephony plugin base class and built-in implementations.

Available implementations:
  TwilioTelephony       — Twilio (REST + TwiML)
  WebSocketTelephony    — raw WebSocket stream (browser / softphone)
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger("voiceflow.telephony")


class TelephonyPlugin(ABC):
    """Minimal telephony interface required by VoiceAgent."""

    @abstractmethod
    async def make_call(self, to: str, from_: str, webhook_url: str) -> str:
        """Initiate outbound call. Returns a call_sid / session id."""
        ...

    @abstractmethod
    async def hangup(self, call_sid: str) -> None:
        """Terminate an ongoing call."""
        ...

    @abstractmethod
    async def transfer(self, call_sid: str, to: str) -> None:
        """Transfer an ongoing call to another number."""
        ...


class TwilioTelephony(TelephonyPlugin):
    """
    Twilio REST API telephony.
    Install extras: pip install voiceflow[twilio]
    """

    def __init__(self, account_sid: str, auth_token: str, default_from: str = ""):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.default_from = default_from
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from twilio.rest import Client
                self._client = Client(self.account_sid, self.auth_token)
            except ImportError:
                raise ImportError("twilio is required: pip install voiceflow[twilio]")
        return self._client

    async def make_call(self, to: str, from_: str, webhook_url: str) -> str:
        import asyncio
        client = self._get_client()
        from_ = from_ or self.default_from
        call = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.calls.create(to=to, from_=from_, url=webhook_url),
        )
        logger.info("[TwilioTelephony] initiated call %s → %s", from_, to)
        return call.sid

    async def hangup(self, call_sid: str) -> None:
        import asyncio
        client = self._get_client()
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.calls(call_sid).update(status="completed"),
        )
        logger.info("[TwilioTelephony] hung up %s", call_sid)

    async def transfer(self, call_sid: str, to: str) -> None:
        import asyncio
        client = self._get_client()
        twiml = f'<Response><Dial>{to}</Dial></Response>'
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.calls(call_sid).update(twiml=twiml),
        )
        logger.info("[TwilioTelephony] transferred %s → %s", call_sid, to)


class WebSocketTelephony(TelephonyPlugin):
    """
    WebSocket-based telephony for browser / softphone testing.
    No outbound calling — simulates a session using a ws connection.
    """

    def __init__(self):
        self._sessions: dict[str, object] = {}

    async def make_call(self, to: str, from_: str, webhook_url: str) -> str:
        import uuid
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {"to": to, "from": from_, "webhook_url": webhook_url}
        logger.info("[WebSocketTelephony] created session %s", session_id)
        return session_id

    async def hangup(self, call_sid: str) -> None:
        ws = self._sessions.pop(call_sid, None)
        if ws and hasattr(ws, "close"):
            try:
                await ws.close()
            except Exception:
                pass
        logger.info("[WebSocketTelephony] closed session %s", call_sid)

    async def transfer(self, call_sid: str, to: str) -> None:
        session = self._sessions.get(call_sid, {})
        if isinstance(session, dict):
            session["transferred_to"] = to
        logger.info("[WebSocketTelephony] transfer %s → %s (session update only)", call_sid, to)
