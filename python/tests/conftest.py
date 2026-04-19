"""
Shared pytest fixtures for VoiceFlow backend tests.

Provides:
- event_loop        : single asyncio event loop for the whole test session
- test_db           : in-memory SQLite async session (isolated from dev DB)
- mock_twilio_client: MagicMock that patches TwilioRestClient
- mock_kokoro       : mock for TTSRouter.synthesize returning fake WAV bytes
"""
import asyncio
import sys
import os
import io
import struct
import wave
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Make sure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# ── Event loop ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── In-memory test database ───────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def test_db():
    """
    Provide an async SQLAlchemy session backed by an in-memory SQLite database.
    All tables are created fresh; the fixture is isolated from the dev database.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    from app.models import Base  # noqa: F401 — registers all ORM classes

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ── Twilio mock ───────────────────────────────────────────────────────────────

@pytest.fixture
def mock_twilio_client():
    """Return a MagicMock that replaces the Twilio REST client."""
    mock = MagicMock()
    mock.calls.create = MagicMock(return_value=MagicMock(sid="CA_test_sid"))
    mock.messages.create = MagicMock(return_value=MagicMock(sid="SM_test_sid"))
    with patch("twilio.rest.Client", return_value=mock):
        yield mock


# ── Kokoro TTS mock ───────────────────────────────────────────────────────────

def _make_fake_wav(duration_ms: int = 100, sample_rate: int = 22050) -> bytes:
    """Generate a minimal valid WAV file of silence."""
    num_samples = int(sample_rate * duration_ms / 1000)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{num_samples}h", *([0] * num_samples)))
    return buf.getvalue()


@pytest.fixture
def mock_kokoro():
    """Patch TTSRouter.synthesize to return a fake WAV without calling Kokoro."""
    fake_wav = _make_fake_wav()
    with patch(
        "app.services.tts_router.TTSRouter._synthesize_kokoro",
        new_callable=AsyncMock,
        return_value=fake_wav,
    ) as m:
        yield m

