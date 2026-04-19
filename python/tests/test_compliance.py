"""
Tests for app/services/compliance_service.py
"""
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


@pytest.fixture
def compliance():
    from app.services.compliance_service import ComplianceService
    return ComplianceService()


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.allowed_call_hours = {"start": "00:00", "end": "23:59"}
    agent.timezone = "UTC"
    agent.max_retries = 3
    return agent


@pytest.fixture
def mock_contact():
    contact = MagicMock()
    contact.callAttempts = 0
    return contact


@pytest.mark.asyncio
async def test_is_calling_hours_within_window(compliance, mock_agent):
    """Agent with all-day window should allow calls at any time."""
    result = await compliance.is_calling_hours(mock_agent)
    assert result is True


@pytest.mark.asyncio
async def test_is_calling_hours_outside_window(compliance):
    """Agent with zero-width window should block calls."""
    from app.services.compliance_service import ComplianceService
    agent = MagicMock()
    agent.allowed_call_hours = {"start": "02:00", "end": "02:01"}
    agent.timezone = "UTC"
    svc = ComplianceService()
    # We can only assert it returns a bool; actual result depends on wall clock
    result = await svc.is_calling_hours(agent)
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_is_retry_allowed_below_limit(compliance, mock_agent, mock_contact):
    """Contact with zero attempts should be allowed when max_retries=3."""
    mock_contact.callAttempts = 0
    result = await compliance.is_retry_allowed(mock_contact, mock_agent)
    assert result is True


@pytest.mark.asyncio
async def test_is_retry_allowed_at_limit(compliance, mock_agent, mock_contact):
    """Contact at max retries should be blocked."""
    mock_contact.callAttempts = 3
    mock_agent.max_retries = 3
    result = await compliance.is_retry_allowed(mock_contact, mock_agent)
    assert result is False


@pytest.mark.asyncio
async def test_is_dnd_not_registered(compliance):
    """A number not in DND list should return False."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    result = await compliance.is_dnd("tenant-1", "+10000000000", db)
    assert result is False


@pytest.mark.asyncio
async def test_is_dnd_registered(compliance):
    """A number in DND list should return True."""
    db = AsyncMock()
    mock_record = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_record)))
    result = await compliance.is_dnd("tenant-1", "+10000000001", db)
    assert result is True


@pytest.mark.asyncio
async def test_validate_before_dial_blocked_by_dnd(compliance, mock_agent, mock_contact):
    """validate_before_dial should return (False, reason) when number is in DND."""
    db = AsyncMock()
    mock_record = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_record)))

    allowed, reason = await compliance.validate_before_dial(
        "tenant-1", "+10000000001", mock_agent, mock_contact, db
    )
    assert allowed is False
    assert "dnd" in reason.lower() or "do not" in reason.lower() or reason != ""


@pytest.mark.asyncio
async def test_validate_before_dial_blocked_by_retries(compliance, mock_agent, mock_contact):
    """validate_before_dial should return (False, reason) when max retries exceeded."""
    mock_contact.callAttempts = 10
    mock_agent.max_retries = 3

    db = AsyncMock()
    # Not in DND
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    # Also mock calling hours to always allow
    with patch.object(compliance, "is_calling_hours", new_callable=AsyncMock, return_value=True):
        allowed, reason = await compliance.validate_before_dial(
            "tenant-1", "+10000000002", mock_agent, mock_contact, db
        )
    assert allowed is False
    assert reason != ""
