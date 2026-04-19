"""
Tests for JWT auth and Twilio signature validation.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import jwt as pyjwt
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


def _make_token(payload: dict, secret: str = "test-secret") -> str:
    return pyjwt.encode(payload, secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_get_current_user_valid_token():
    """Valid JWT returns an AuthContext with correct tenant/user IDs."""
    from app.auth import get_current_user, AuthContext

    token = _make_token({
        "sub": "user-123",
        "tenant_id": "tenant-456",
        "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
    }, secret="test-secret")

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    with patch("app.auth.settings") as mock_settings:
        mock_settings.JWT_SECRET = "test-secret"
        with patch("app.auth._ensure_tenant_and_user", new_callable=AsyncMock):
            result = await get_current_user(credentials=credentials, db=mock_db)

    assert result.user_id == "user-123"
    assert result.tenant_id == "tenant-456"


@pytest.mark.asyncio
async def test_get_current_user_expired_token():
    """Expired JWT raises HTTP 401."""
    from app.auth import get_current_user

    token = _make_token({
        "sub": "user-123",
        "tenant_id": "tenant-456",
        "exp": (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp(),
    }, secret="test-secret")

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    mock_db = AsyncMock()

    with patch("app.auth.settings") as mock_settings:
        mock_settings.JWT_SECRET = "test-secret"
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=credentials, db=mock_db)

    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    """Invalid JWT raises HTTP 401."""
    from app.auth import get_current_user

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not.a.valid.token")
    mock_db = AsyncMock()

    with patch("app.auth.settings") as mock_settings:
        mock_settings.JWT_SECRET = "test-secret"
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=credentials, db=mock_db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_no_credentials():
    """Missing Authorization header raises HTTP 401."""
    from app.auth import get_current_user

    mock_db = AsyncMock()
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=None, db=mock_db)

    assert exc_info.value.status_code == 401


def test_twilio_signature_validation_skips_when_no_creds():
    """Signature validation returns True when Twilio creds are not configured."""
    from app.routes.voice_twilio_stream import _validate_twilio_signature

    mock_request = MagicMock()
    mock_request.headers.get = lambda k, d="": d
    mock_request.url.path = "/api/voice/inbound/agent-1"

    with patch("app.routes.voice_twilio_stream.settings") as mock_settings:
        mock_settings.TWILIO_ACCOUNT_SID = None
        mock_settings.TWILIO_AUTH_TOKEN = None
        result = _validate_twilio_signature(mock_request, {})

    assert result is True


def test_twilio_signature_validation_invalid_sig():
    """Invalid Twilio signature returns False when creds are configured."""
    from app.routes.voice_twilio_stream import _validate_twilio_signature

    mock_request = MagicMock()
    mock_request.headers = {
        "x-forwarded-proto": "https",
        "host": "test.example.com",
        "X-Twilio-Signature": "bad-signature",
    }
    mock_request.headers.get = lambda k, d="": mock_request.headers.get(k, d)
    mock_request.url.path = "/api/voice/inbound/agent-1"

    with patch("app.routes.voice_twilio_stream.settings") as mock_settings:
        mock_settings.TWILIO_ACCOUNT_SID = "ACtest123"
        mock_settings.TWILIO_AUTH_TOKEN = "authtoken123"
        with patch("twilio.request_validator.RequestValidator.validate", return_value=False):
            result = _validate_twilio_signature(mock_request, {"CallSid": "CA123"})

    assert result is False
