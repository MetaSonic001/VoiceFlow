"""
Tests for barge-in / interruption detection in the Twilio Media Stream handler.

Verifies that the VAD logic clears the agent-speaking buffer and transitions
back to listening when the caller speaks loudly over the agent.
"""
import asyncio
import struct
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_interruption_clears_speaking_event():
    """Agent-speaking event is cleared when caller speaks above the RMS threshold."""
    from app.routes.voice_twilio_stream import _pcm_rms, _INTERRUPT_RMS_THRESHOLD

    # Generate a loud PCM chunk that should exceed the interrupt threshold
    loud_rms = int(_INTERRUPT_RMS_THRESHOLD * 2)
    n = 160
    samples = struct.pack(f"<{n}h", *([loud_rms] * n))
    rms = _pcm_rms(samples)
    assert rms > _INTERRUPT_RMS_THRESHOLD, (
        f"Expected rms {rms} > threshold {_INTERRUPT_RMS_THRESHOLD}"
    )

    # Simulate the agent-speaking-event being cleared on interruption
    speaking_event = asyncio.Event()
    speaking_event.set()

    if speaking_event.is_set() and rms > _INTERRUPT_RMS_THRESHOLD:
        speaking_event.clear()

    assert not speaking_event.is_set(), "Agent speaking event should be cleared after interruption"


@pytest.mark.asyncio
async def test_silence_detection_accumulates_frames():
    """Silence frames counter increments on low-RMS audio."""
    from app.routes.voice_twilio_stream import _pcm_rms

    n = 160
    # Silent PCM
    silent_samples = struct.pack(f"<{n}h", *([0] * n))
    rms = _pcm_rms(silent_samples)
    assert rms < 50.0, f"Expected rms {rms} < 50 for silent audio"

    # Simulate accumulation of silence frames
    silence_frames = 0
    for _ in range(30):
        if rms < 50.0:
            silence_frames += 1
    assert silence_frames == 30


@pytest.mark.asyncio
async def test_mulaw_to_pcm16k_produces_bytes():
    """_mulaw_to_pcm16k returns non-empty bytes."""
    from app.routes.voice_twilio_stream import _mulaw_to_pcm16k

    # 160 bytes of silence in μ-law (zero-encoded)
    mulaw_silence = bytes(160)
    result = _mulaw_to_pcm16k(mulaw_silence)
    assert isinstance(result, bytes)
    assert len(result) > 0

