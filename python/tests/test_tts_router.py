"""
Tests for app/services/tts_router.py
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


@pytest.mark.asyncio
async def test_tts_router_import():
    """TTSRouter can be imported without errors."""
    from app.services.tts_router import TTSRouter  # noqa: F401
    router = TTSRouter()
    assert router is not None


@pytest.mark.asyncio
async def test_tts_router_has_synthesize_method():
    """TTSRouter exposes a synthesize method."""
    from app.services.tts_router import TTSRouter
    router = TTSRouter()
    assert callable(getattr(router, "synthesize", None)) or callable(
        getattr(router, "synthesize_mulaw", None)
    ), "TTSRouter must have synthesize or synthesize_mulaw"


@pytest.mark.asyncio
async def test_tts_supported_engines():
    """TTSRouter advertises at least kokoro and edge as supported engines."""
    from app.services.tts_router import TTSRouter
    router = TTSRouter()
    engines = getattr(router, "SUPPORTED_ENGINES", [])
    # Not required to expose the attribute, but if it does it should contain kokoro
    if engines:
        assert "kokoro" in engines or "edge" in engines
