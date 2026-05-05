"""
/api/simulate routes — agent scenario testing.

POST /api/simulate/{agent_id}
  Run a batch of test scenarios through the full RAG pipeline.
  Returns a SimulationReport with per-scenario pass/fail, LLM judge scores, latency.

This mirrors OmniDimension's Simulation API but tests the full pipeline:
  retrieval → policy scoring → prompt assembly → LLM → response
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Agent, Tenant
from app.services.credentials import decrypt_safe
from app.config import settings

logger = logging.getLogger("voiceflow.simulate")
router = APIRouter()


@router.post("/{agent_id}")
async def run_agent_simulation(
    agent_id: str,
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Run automated scenario testing against an agent.

    Request body:
    {
      "scenarios": [
        {
          "utterance": "What are your business hours?",
          "expected_intent": "hours inquiry",
          "expected_keywords": ["hours", "open"],
          "must_not_contain": ["I don't know"],
          "tags": ["faq", "hours"]
        }
      ]
    }

    Returns a full SimulationReport with:
    - Per-scenario: response, latency_ms, score (0–1), pass/fail, LLM judge feedback
    - Summary: overall pass rate, avg score, avg latency, improvement suggestions
    """
    # Verify agent belongs to this tenant
    agent_res = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id)
    )
    agent = agent_res.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    body = await request.json()
    scenarios = body.get("scenarios", [])
    if not scenarios:
        raise HTTPException(status_code=400, detail="scenarios array is required")
    if len(scenarios) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 scenarios per simulation run")

    # Resolve Groq key for LLM judge
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    groq_key = settings.GROQ_API_KEY
    if tenant and tenant.settings:
        enc = tenant.settings.get("groqApiKey")
        if enc:
            decrypted = decrypt_safe(enc)
            if decrypted and decrypted.startswith("gsk_"):
                groq_key = decrypted

    from app.services.simulation_service import run_simulation

    report = await run_simulation(
        db=db,
        tenant_id=auth.tenant_id,
        agent_id=agent_id,
        scenarios=scenarios,
        groq_key=groq_key,
        session_prefix=f"sim-{agent_id[:8]}",
    )

    return JSONResponse({
        "agentId": report.agent_id,
        "tenantId": report.tenant_id,
        "summary": report.summary,
        "stats": {
            "total": report.total,
            "passed": report.passed,
            "failed": report.failed,
            "passRate": round(report.passed / report.total, 3) if report.total else 0,
            "avgScore": round(report.avg_score, 3),
            "avgLatencyMs": round(report.avg_latency_ms, 1),
        },
        "results": [
            {
                "utterance": r.utterance,
                "response": r.response,
                "latencyMs": r.latency_ms,
                "passed": r.passed,
                "score": round(r.score, 3),
                "failureReasons": r.failure_reasons,
                "judgeFeedback": r.judge_feedback,
                "tags": r.tags,
            }
            for r in report.results
        ],
    })
