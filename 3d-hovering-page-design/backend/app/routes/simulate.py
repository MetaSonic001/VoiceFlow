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


@router.post("/{agent_id}/adversarial")
async def generate_adversarial(
    agent_id: str,
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Auto-generate adversarial test scenarios for an agent using LLM red-teaming.
    Returns injection/edge_case/stress scenarios ready for use in /simulate/{agent_id}.

    Optionally pass {"run": true} to immediately run the scenarios and return a report.
    """
    agent_res = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id)
    )
    agent = agent_res.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    body = await request.json()
    count = min(int(body.get("count", 10)), 30)
    run_immediately = bool(body.get("run", False))

    tenant_res = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    groq_key = settings.GROQ_API_KEY
    if tenant and tenant.settings:
        enc = tenant.settings.get("groqApiKey")
        if enc:
            decrypted = decrypt_safe(enc)
            if decrypted and decrypted.startswith("gsk_"):
                groq_key = decrypted

    from app.services.simulation_service import generate_adversarial_scenarios, run_simulation

    scenarios = await generate_adversarial_scenarios(
        agent_description=agent.description or agent.name,
        system_prompt=agent.systemPrompt or "",
        groq_key=groq_key,
        count=count,
    )

    if not run_immediately:
        return JSONResponse({"scenarios": scenarios, "count": len(scenarios)})

    report = await run_simulation(
        db=db,
        tenant_id=auth.tenant_id,
        agent_id=agent_id,
        scenarios=scenarios,
        groq_key=groq_key,
        session_prefix=f"adversarial-{agent_id[:8]}",
    )
    return JSONResponse({
        "agentId": report.agent_id,
        "summary": report.summary,
        "stats": {
            "total": report.total,
            "passed": report.passed,
            "failed": report.failed,
            "passRate": round(report.passed / report.total, 3) if report.total else 0,
            "avgScore": round(report.avg_score, 3),
        },
        "results": [
            {
                "utterance": r.utterance,
                "response": r.response[:300],
                "passed": r.passed,
                "score": round(r.score, 3),
                "failureReasons": r.failure_reasons,
                "tags": r.tags,
            }
            for r in report.results
        ],
    })


@router.post("/{agent_id}/gate")
async def simulation_gate(
    agent_id: str,
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    CI/CD gate check: run simulation and return pass/fail with threshold evaluation.
    Use this endpoint in deployment pipelines before activating a prompt update.

    Body: same as POST /{agent_id} plus optional thresholds:
    {
      "scenarios": [...],
      "pass_rate_threshold": 0.80,
      "avg_score_threshold": 0.65,
      "max_latency_ms": 4000
    }
    Returns: {"gate_passed": bool, "reason": str, "report": {...}}
    """
    agent_res = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id)
    )
    agent = agent_res.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    body = await request.json()
    scenarios = body.get("scenarios", [])
    if not scenarios:
        raise HTTPException(status_code=400, detail="scenarios are required")

    tenant_res = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    groq_key = settings.GROQ_API_KEY
    if tenant and tenant.settings:
        enc = tenant.settings.get("groqApiKey")
        if enc:
            decrypted = decrypt_safe(enc)
            if decrypted and decrypted.startswith("gsk_"):
                groq_key = decrypted

    from app.services.simulation_service import run_simulation, check_simulation_gate

    report = await run_simulation(
        db=db,
        tenant_id=auth.tenant_id,
        agent_id=agent_id,
        scenarios=scenarios,
        groq_key=groq_key,
        session_prefix=f"gate-{agent_id[:8]}",
    )

    gate_passed, reason = await check_simulation_gate(
        report,
        pass_rate_threshold=float(body.get("pass_rate_threshold", 0.80)),
        avg_score_threshold=float(body.get("avg_score_threshold", 0.65)),
        max_latency_ms=float(body.get("max_latency_ms", 4000)),
    )

    status_code = 200 if gate_passed else 422
    return JSONResponse(
        {
            "gate_passed": gate_passed,
            "reason": reason,
            "report": {
                "total": report.total,
                "passed": report.passed,
                "passRate": round(report.passed / report.total, 3) if report.total else 0,
                "avgScore": round(report.avg_score, 3),
                "avgLatencyMs": round(report.avg_latency_ms, 1),
                "summary": report.summary,
            },
        },
        status_code=status_code,
    )

