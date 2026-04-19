"""
E2E test verifying that campaign contact variables flow correctly through the pipeline:

campaign_worker → outbound TwiML → stream parameters → contact_variables in RAG context

Tests:
1. Outbound TwiML contains stream parameters for contact variables
2. Contact variables are injected into the system prompt
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_outbound_twiml_contains_contact_vars():
    """
    voice_outbound builds TwiML with contact variable stream parameters.
    """
    from app.routes.voice_twilio_stream import voice_outbound

    # Mock agent
    mock_agent = MagicMock()
    mock_agent.id = "agent-outbound-1"
    mock_agent.tenantId = "tenant-1"

    # Mock contact with variables
    mock_contact = MagicMock()
    mock_contact.name = "Rahul"
    mock_contact.variables = {"loan_amount": "50000", "due_date": "2026-05-01"}

    mock_request = MagicMock()
    mock_request.form = AsyncMock(return_value={
        "AnsweredBy": "human",
        "CallSid": "CA_test_outbound",
    })
    mock_request.query_params = {"contact_id": "contact-test-1"}
    mock_request.headers.get = lambda k, d="": {
        "host": "test.example.com",
        "x-forwarded-proto": "https",
    }.get(k, d)

    with patch("app.routes.voice_twilio_stream.AsyncSessionLocal") as mock_session_class:
        session_ctx = AsyncMock()
        session_ctx.__aenter__ = AsyncMock(return_value=session_ctx)
        session_ctx.__aexit__ = AsyncMock(return_value=False)

        def _execute_side_effect(query):
            result = MagicMock()
            # First call: agent lookup; second call: contact lookup
            if not hasattr(_execute_side_effect, "call_count"):
                _execute_side_effect.call_count = 0
            _execute_side_effect.call_count += 1
            if _execute_side_effect.call_count == 1:
                result.scalar_one_or_none.return_value = mock_agent
            else:
                result.scalar_one_or_none.return_value = mock_contact
            return result

        session_ctx.execute = AsyncMock(side_effect=_execute_side_effect)
        mock_session_class.return_value = session_ctx

        response = await voice_outbound("agent-outbound-1", mock_request)

    assert response.media_type == "application/xml"
    twiml = response.body.decode()
    # Verify contact variables appear as stream parameters
    assert "Rahul" in twiml or "name" in twiml
    assert "loan_amount" in twiml or "50000" in twiml


@pytest.mark.asyncio
async def test_outbound_machine_answered_hangs_up():
    """Outbound call answered by machine returns <Hangup> TwiML."""
    from app.routes.voice_twilio_stream import voice_outbound

    mock_request = MagicMock()
    mock_request.form = AsyncMock(return_value={
        "AnsweredBy": "machine_start",
        "CallSid": "CA_machine_test",
    })
    mock_request.query_params = {}

    response = await voice_outbound("agent-1", mock_request)
    assert response.media_type == "application/xml"
    twiml = response.body.decode()
    assert "Hangup" in twiml or "hangup" in twiml.lower()


@pytest.mark.asyncio
async def test_contact_vars_in_system_prompt():
    """
    Contact variables injected via assemble_context appear in the system prompt.
    """
    from app.services.rag_service import build_system_prompt

    # Build a minimal context dict with contact_variables (simulating assemble_context output)
    context = {
        "globalRules": "Be helpful.",
        "tenantName": None,
        "tenantIndustry": None,
        "tenantSettings": {},
        "policyRules": [],
        "brandVoice": None,
        "allowedTopics": [],
        "restrictedTopics": [],
        "agentName": "TestAgent",
        "agentRole": None,
        "agentDescription": None,
        "personalityTraits": [],
        "responseTone": None,
        "behaviorRules": [],
        "escalationTriggers": [],
        "knowledgeBoundaries": [],
        "customInstructions": None,
        "escalationRules": [],
        "fewShotExamples": [],
        "contact_variables": {
            "name": "Rahul",
            "loan_amount": "50000",
            "due_date": "2026-05-01",
        },
    }

    prompt = build_system_prompt(context)
    assert "Rahul" in prompt
    assert "50000" in prompt or "loan_amount" in prompt
