"""
Tests for Twilio Media Stream WebSocket handler.

Mocks Twilio WebSocket messages and verifies correct behaviour.
"""
import asyncio
import base64
import json
import struct
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _pcm_chunk(rms: int = 0, n: int = 160) -> bytes:
    """Create a PCM chunk at the given RMS level."""
    val = min(32767, max(0, rms))
    return struct.pack(f"<{n}h", *([val] * n))


def _mulaw_silence(n: int = 160) -> bytes:
    """Return n bytes of μ-law silence."""
    return bytes(n)


def _make_media_event(payload_bytes: bytes) -> str:
    return json.dumps({
        "event": "media",
        "media": {"payload": base64.b64encode(payload_bytes).decode()},
    })


@pytest.mark.asyncio
async def test_ws_iter_yields_messages():
    """_ws_iter yields messages from the WebSocket until disconnect."""
    from app.routes.voice_twilio_stream import _ws_iter
    from fastapi import WebSocketDisconnect

    messages = ["msg1", "msg2", "msg3"]
    call_count = [0]

    async def mock_receive_text():
        if call_count[0] < len(messages):
            msg = messages[call_count[0]]
            call_count[0] += 1
            return msg
        raise WebSocketDisconnect()

    mock_ws = AsyncMock()
    mock_ws.receive_text = mock_receive_text

    result = []
    async for msg in _ws_iter(mock_ws):
        result.append(msg)

    assert result == messages


@pytest.mark.asyncio
async def test_pcm_rms_silent():
    """_pcm_rms returns zero for silent audio."""
    from app.routes.voice_twilio_stream import _pcm_rms
    result = _pcm_rms(bytes(320))  # 160 16-bit zero samples
    assert result == 0.0


@pytest.mark.asyncio
async def test_pcm_rms_loud():
    """_pcm_rms returns positive value for loud audio."""
    from app.routes.voice_twilio_stream import _pcm_rms
    loud = _pcm_chunk(rms=1000)
    result = _pcm_rms(loud)
    assert result > 900


@pytest.mark.asyncio
async def test_stream_mulaw_stops_on_interruption():
    """_stream_mulaw_to_twilio stops sending when speaking event is cleared."""
    from app.routes.voice_twilio_stream import _stream_mulaw_to_twilio

    mock_ws = AsyncMock()
    mock_ws.send_text = AsyncMock()

    speaking_event = asyncio.Event()
    speaking_event.set()

    # 10 frames of audio
    audio = bytes(160 * 10)

    # Clear the event after 3 frames
    original_send = mock_ws.send_text
    call_count = [0]

    async def send_and_interrupt(msg):
        call_count[0] += 1
        if call_count[0] == 3:
            speaking_event.clear()
        await original_send(msg)

    mock_ws.send_text = send_and_interrupt

    with patch("asyncio.sleep", new_callable=AsyncMock):
        await _stream_mulaw_to_twilio(mock_ws, "stream_sid_123", audio, speaking_event)

    # Should have stopped shortly after the event was cleared
    assert call_count[0] <= 5  # no more than a couple frames past the interruption


@pytest.mark.asyncio
async def test_inbound_returns_twiml_connect():
    """voice_inbound route returns TwiML with <Connect> when agent exists."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI

    # Build a minimal app with just the stream router
    app = FastAPI()

    mock_agent = MagicMock()
    mock_agent.id = "agent-test-123"
    mock_agent.tenantId = "tenant-test"
    mock_agent.configuration = None

    with patch(
        "app.routes.voice_twilio_stream.AsyncSessionLocal"
    ) as mock_session_class:
        session_ctx = AsyncMock()
        session_ctx.__aenter__ = AsyncMock(return_value=session_ctx)
        session_ctx.__aexit__ = AsyncMock(return_value=False)
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = mock_agent
        session_ctx.execute = AsyncMock(return_value=execute_result)
        mock_session_class.return_value = session_ctx

        from app.routes.voice_twilio_stream import handle_inbound_call

        mock_request = MagicMock()
        mock_request.headers.get = lambda k, d="": {"host": "test.example.com", "x-forwarded-proto": "https"}.get(k, d)

        response = await handle_inbound_call(mock_agent, mock_request)

    assert response.media_type == "application/xml"
    content = response.body.decode() if hasattr(response, "body") else str(response)
    assert "Stream" in content or "Connect" in content or "stream" in content.lower()
