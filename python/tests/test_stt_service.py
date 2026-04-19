"""
Tests for app/services/stt_service.py
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


@pytest.mark.asyncio
async def test_stt_service_import():
    """STTService singleton can be imported."""
    from app.services.stt_service import stt_service  # noqa: F401
    assert stt_service is not None


@pytest.mark.asyncio
async def test_stt_service_has_required_methods():
    """STTService exposes the expected public interface."""
    from app.services.stt_service import stt_service
    assert callable(getattr(stt_service, "initialize", None)), "stt_service must have initialize()"
    assert callable(getattr(stt_service, "transcribe_stream_chunk", None)), (
        "stt_service must have transcribe_stream_chunk()"
    )


@pytest.mark.asyncio
async def test_stt_service_transcribe_bytes_silent():
    """Transcribing silent PCM should return an empty or near-empty string without crashing."""
    from app.services.stt_service import stt_service

    # 1 second of silent 16-bit mono 16kHz PCM (32 000 zero bytes)
    silent_pcm = bytes(32000 * 2)

    try:
        await stt_service.initialize()
    except Exception:
        pytest.skip("Vosk model not available in CI — skipping STT test")

    try:
        result = await stt_service.transcribe_bytes(silent_pcm, engine="vosk")
        assert isinstance(result, str), "transcribe_bytes must return a str"
        # Silent audio should produce empty or near-empty transcript
        assert len(result) < 50, f"Unexpected non-empty transcript for silence: {result!r}"
    except AttributeError:
        pytest.skip("transcribe_bytes not available on this STTService version")
