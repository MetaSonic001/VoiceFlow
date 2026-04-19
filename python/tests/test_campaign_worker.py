"""
Tests for app/services/campaign_worker.py
"""
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


@pytest.fixture
def worker():
    from app.services.campaign_worker import CampaignWorker
    return CampaignWorker()


@pytest.mark.asyncio
async def test_campaign_worker_import():
    """CampaignWorker can be imported without errors."""
    from app.services.campaign_worker import CampaignWorker
    w = CampaignWorker()
    assert w is not None


@pytest.mark.asyncio
async def test_enqueue_campaign_no_contacts(worker):
    """enqueue_campaign with no pending contacts should not error."""
    db = AsyncMock()
    # Simulate empty result from DB
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)

    # Also mock the campaign fetch
    mock_campaign_result = MagicMock()
    mock_campaign = MagicMock()
    mock_campaign.id = "camp-1"
    mock_campaign.agentId = "agent-1"
    mock_campaign.tenantId = "tenant-1"
    mock_campaign_result.scalar_one_or_none.return_value = mock_campaign
    db.execute = AsyncMock(side_effect=[mock_campaign_result, mock_result])

    mock_redis = AsyncMock()
    mock_redis.lpush = AsyncMock(return_value=0)
    mock_redis.expire = AsyncMock()

    with patch("app.services.campaign_worker.aioredis.Redis", return_value=mock_redis):
        try:
            await worker.enqueue_campaign("camp-1", db)
        except Exception as exc:
            pytest.fail(f"enqueue_campaign raised unexpectedly: {exc}")


@pytest.mark.asyncio
async def test_handle_amd_result_human(worker):
    """handle_amd_result with 'human' should not raise."""
    db = AsyncMock()
    mock_contact_result = MagicMock()
    mock_contact = MagicMock()
    mock_contact.callAttempts = 1
    mock_contact.status = "dialing"
    mock_contact_result.scalar_one_or_none.return_value = mock_contact

    mock_campaign_result = MagicMock()
    mock_campaign = MagicMock()
    mock_campaign.totalCalls = 0
    mock_campaign.answeredCalls = 0
    mock_campaign_result.scalar_one_or_none.return_value = mock_campaign

    db.execute = AsyncMock(side_effect=[mock_contact_result, mock_campaign_result])
    db.commit = AsyncMock()

    with patch("app.services.campaign_worker.AsyncSessionLocal") as mock_session_cls:
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        try:
            await worker.handle_amd_result("CA123", "human", "camp-1")
        except Exception as exc:
            pytest.fail(f"handle_amd_result raised unexpectedly: {exc}")


@pytest.mark.asyncio
async def test_handle_amd_result_machine(worker):
    """handle_amd_result with 'machine_end_beep' should not raise."""
    db = AsyncMock()
    mock_contact_result = MagicMock()
    mock_contact = MagicMock()
    mock_contact.callAttempts = 1
    mock_contact.status = "dialing"
    mock_contact_result.scalar_one_or_none.return_value = mock_contact

    mock_campaign_result = MagicMock()
    mock_campaign = MagicMock()
    mock_campaign.totalCalls = 1
    mock_campaign.answeredCalls = 0
    mock_campaign_result.scalar_one_or_none.return_value = mock_campaign

    db.execute = AsyncMock(side_effect=[mock_contact_result, mock_campaign_result])
    db.commit = AsyncMock()

    with patch("app.services.campaign_worker.AsyncSessionLocal") as mock_session_cls:
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        try:
            await worker.handle_amd_result("CA456", "machine_end_beep", "camp-1")
        except Exception as exc:
            pytest.fail(f"handle_amd_result raised unexpectedly: {exc}")
