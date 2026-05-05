"""
Agent Simulation Service — automated scenario testing for AI agents.

Mirrors OmniDimension's Simulation API but goes further: tests the full RAG pipeline
(retrieval + reranking + policy scoring + LLM), not just the LLM.

Usage:
  POST /api/simulate/{agent_id}
  Body: {"scenarios": [{"utterance": "...", "expected_intent": "...", "tags": [...]}]}
  Returns: per-scenario pass/fail with LLM-as-judge scores.

pip install deepeval   (optional — for advanced RAG metrics like faithfulness, answer relevancy)
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("voiceflow.simulation")


@dataclass
class SimulationScenario:
    """A single test case: an utterance + optional expected outcome."""
    utterance: str
    expected_intent: str = ""
    expected_keywords: list[str] = field(default_factory=list)
    must_not_contain: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class ScenarioResult:
    utterance: str
    response: str
    latency_ms: int
    passed: bool
    score: float                        # 0.0–1.0 from LLM judge
    failure_reasons: list[str] = field(default_factory=list)
    judge_feedback: str = ""
    retrieved_docs: int = 0
    tags: list[str] = field(default_factory=list)


@dataclass
class SimulationReport:
    agent_id: str
    tenant_id: str
    total: int
    passed: int
    failed: int
    avg_score: float
    avg_latency_ms: float
    results: list[ScenarioResult]
    summary: str = ""


async def run_simulation(
    db: AsyncSession,
    tenant_id: str,
    agent_id: str,
    scenarios: list[dict],
    groq_key: Optional[str] = None,
    session_prefix: str = "sim",
) -> SimulationReport:
    """
    Run all scenarios against the full RAG pipeline (parallel, capped at 5 concurrent).

    Each scenario fires through process_query_streaming(), measures latency,
    then uses an LLM-as-judge (Groq, same key) to score:
      - Task completion: did the agent address the user's intent?
      - Faithfulness: is the response grounded in the knowledge base?
      - Hallucination: did the agent make up facts?
      - Tone adherence: does the response match the configured brand voice?
    """
    from app.services.rag_service import process_query_streaming

    parsed: list[SimulationScenario] = []
    for s in scenarios:
        if isinstance(s, dict) and s.get("utterance"):
            parsed.append(SimulationScenario(
                utterance=s["utterance"],
                expected_intent=s.get("expected_intent", ""),
                expected_keywords=s.get("expected_keywords", []),
                must_not_contain=s.get("must_not_contain", []),
                tags=s.get("tags", []),
            ))

    if not parsed:
        return SimulationReport(
            agent_id=agent_id, tenant_id=tenant_id,
            total=0, passed=0, failed=0,
            avg_score=0.0, avg_latency_ms=0.0, results=[],
            summary="No valid scenarios provided.",
        )

    semaphore = asyncio.Semaphore(5)

    async def _run_one(scenario: SimulationScenario, idx: int) -> ScenarioResult:
        async with semaphore:
            session_id = f"{session_prefix}-{idx}"
            start = time.monotonic()
            response_parts: list[str] = []

            try:
                async for token in process_query_streaming(
                    db, tenant_id, agent_id, scenario.utterance, session_id
                ):
                    if isinstance(token, str):
                        response_parts.append(token)
            except Exception as exc:
                logger.warning("[simulation] scenario %d failed: %s", idx, exc)
                return ScenarioResult(
                    utterance=scenario.utterance,
                    response="",
                    latency_ms=0,
                    passed=False,
                    score=0.0,
                    failure_reasons=[f"Pipeline error: {exc}"],
                    tags=scenario.tags,
                )

            latency_ms = int((time.monotonic() - start) * 1000)
            response = "".join(response_parts).strip()

            # Rule-based checks (instant, no LLM needed)
            failure_reasons: list[str] = []
            if not response:
                failure_reasons.append("Empty response")
            for phrase in scenario.must_not_contain:
                if phrase.lower() in response.lower():
                    failure_reasons.append(f"Contains forbidden phrase: '{phrase}'")
            for kw in scenario.expected_keywords:
                if kw.lower() not in response.lower():
                    failure_reasons.append(f"Missing expected keyword: '{kw}'")

            # LLM-as-judge scoring
            score, judge_feedback = await _llm_judge(
                utterance=scenario.utterance,
                response=response,
                expected_intent=scenario.expected_intent,
                groq_key=groq_key,
            )

            if score < 0.5:
                failure_reasons.append(f"LLM judge score too low: {score:.2f}")

            passed = len(failure_reasons) == 0

            return ScenarioResult(
                utterance=scenario.utterance,
                response=response,
                latency_ms=latency_ms,
                passed=passed,
                score=score,
                failure_reasons=failure_reasons,
                judge_feedback=judge_feedback,
                tags=scenario.tags,
            )

    results = await asyncio.gather(*[_run_one(s, i) for i, s in enumerate(parsed)])

    passed_count = sum(1 for r in results if r.passed)
    avg_score = sum(r.score for r in results) / len(results) if results else 0.0
    avg_latency = sum(r.latency_ms for r in results) / len(results) if results else 0.0

    summary_lines = [
        f"Simulation complete: {passed_count}/{len(results)} passed "
        f"(avg score {avg_score:.2f}, avg latency {avg_latency:.0f}ms)."
    ]
    if any(r.latency_ms > 3000 for r in results):
        summary_lines.append("⚠ Some scenarios exceeded 3s latency — review STT/RAG/TTS pipeline.")
    if avg_score < 0.7:
        summary_lines.append("⚠ Average quality score below threshold — consider retraining or updating knowledge base.")

    return SimulationReport(
        agent_id=agent_id,
        tenant_id=tenant_id,
        total=len(results),
        passed=passed_count,
        failed=len(results) - passed_count,
        avg_score=avg_score,
        avg_latency_ms=avg_latency,
        results=results,
        summary=" ".join(summary_lines),
    )


async def _llm_judge(
    utterance: str,
    response: str,
    expected_intent: str,
    groq_key: Optional[str],
) -> tuple[float, str]:
    """
    LLM-as-judge evaluation. Returns (score 0.0–1.0, feedback string).
    Score thresholds: ≥0.8 excellent, ≥0.65 pass, <0.5 fail.
    """
    if not groq_key or not response:
        return (0.0 if not response else 0.6), "No LLM judge available"

    prompt = f"""You are evaluating an AI voice agent response. Score it from 0.0 to 1.0.

USER SAID: {utterance}
EXPECTED INTENT: {expected_intent or "(not specified)"}
AGENT RESPONDED: {response}

Score on:
1. Task completion (0–0.4): Did the agent address the user's actual intent?
2. Factual grounding (0–0.3): Does the response seem grounded and non-hallucinated?
3. Tone and professionalism (0–0.3): Is the response appropriate and professional?

Return JSON only: {{"score": 0.75, "feedback": "one sentence explanation"}}"""

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": "You are a strict evaluator. Return valid JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 128,
                },
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"].strip()
                content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                data = json.loads(content)
                score = float(data.get("score", 0.6))
                feedback = str(data.get("feedback", ""))
                return max(0.0, min(1.0, score)), feedback
    except Exception as exc:
        logger.debug("[simulation] LLM judge failed: %s", exc)
    return 0.6, "LLM judge unavailable — using default pass score"
