"""
Latency Benchmarking & Auto-Optimization.

Measures and stores component latencies for every call turn:
  stt_ms     — STT processing time
  rag_ms     — RAG retrieval + BM25 + reranking time
  llm_ttft_ms — LLM time-to-first-token
  tts_ms     — TTS synthesis time
  total_ms   — end-to-end perceived latency

Auto-optimization rules (applied per-call when latency breaches thresholds):
  RAG > 300ms  → activate ANN-approximate search (skip exact BM25 rerank)
  TTS not cached → check phrase cache hit, serve from disk
  LLM > 2s TTFT → route to Groq llama-3.1-8b-instant (faster, lower quality)
  total > 3s    → log warning, increment slow_turn counter for the agent

Storage: Redis HASH `latency:{call_log_id}` with per-turn JSON list.
         Also kept in module-level ring buffer for the last 1000 turns per agent.

Usage:
  from app.services.latency_tracker import LatencyTracker
  tracker = LatencyTracker(call_log_id, agent_id, tenant_id)
  tracker.mark("stt_start")
  transcript = await stt(...)
  tracker.mark("stt_end")
  tracker.mark("rag_start")
  ...
  await tracker.flush()  # writes to Redis + evaluates auto-opt rules
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from typing import Any, Optional

logger = logging.getLogger("voiceflow.latency")

# In-memory ring buffer: agent_id → deque of turn latency dicts (last 200)
_agent_latency_ring: dict[str, deque] = {}

# Thresholds (ms)
_THRESHOLD_RAG = 300
_THRESHOLD_LLM_TTFT = 2000
_THRESHOLD_TOTAL = 3000


class LatencyTracker:
    """
    Per-turn latency tracker.  Instantiate at the start of each conversation turn.
    """

    def __init__(self, call_log_id: str, agent_id: str, tenant_id: str):
        self.call_log_id = call_log_id
        self.agent_id = agent_id
        self.tenant_id = tenant_id
        self._marks: dict[str, float] = {}
        self._attrs: dict[str, Any] = {}

    def mark(self, label: str) -> float:
        """Record current monotonic time for a label. Returns the timestamp."""
        t = time.monotonic()
        self._marks[label] = t
        return t

    def delta_ms(self, start_label: str, end_label: str) -> Optional[float]:
        """Compute elapsed ms between two marks."""
        start = self._marks.get(start_label)
        end = self._marks.get(end_label)
        if start is None or end is None:
            return None
        return round((end - start) * 1000, 1)

    def set(self, key: str, value: Any) -> None:
        """Set an arbitrary attribute (e.g. model name, cache_hit)."""
        self._attrs[key] = value

    def build_report(self) -> dict:
        stt_ms = self.delta_ms("stt_start", "stt_end")
        rag_ms = self.delta_ms("rag_start", "rag_end")
        llm_ms = self.delta_ms("llm_start", "llm_first_token")
        tts_ms = self.delta_ms("tts_start", "tts_end")
        total_ms = self.delta_ms("turn_start", "turn_end")
        return {
            "call_log_id": self.call_log_id,
            "agent_id": self.agent_id,
            "stt_ms": stt_ms,
            "rag_ms": rag_ms,
            "llm_ttft_ms": llm_ms,
            "tts_ms": tts_ms,
            "total_ms": total_ms,
            **self._attrs,
        }

    def evaluate_optimizations(self) -> list[str]:
        """
        Return a list of recommended auto-optimizations based on measured latency.
        The caller can apply these hints in the next turn.
        """
        report = self.build_report()
        hints: list[str] = []
        if report["rag_ms"] and report["rag_ms"] > _THRESHOLD_RAG:
            hints.append("use_ann_search")  # skip BM25 exact rerank
            logger.debug("[latency] RAG slow (%.0fms) → recommending ANN search", report["rag_ms"])
        if report["llm_ttft_ms"] and report["llm_ttft_ms"] > _THRESHOLD_LLM_TTFT:
            hints.append("use_fast_llm")   # route to llama-3.1-8b-instant
            logger.debug("[latency] LLM slow (%.0fms) → recommending fast model", report["llm_ttft_ms"])
        if report["total_ms"] and report["total_ms"] > _THRESHOLD_TOTAL:
            hints.append("slow_turn_alert")
            logger.warning("[latency] slow turn %.0fms agent=%s call=%s",
                           report["total_ms"], self.agent_id, self.call_log_id)
        return hints

    async def flush(self) -> dict:
        """
        Write this turn's latency report to the in-memory ring buffer and Redis.
        Returns the report dict.
        """
        report = self.build_report()

        # In-memory ring
        ring = _agent_latency_ring.setdefault(self.agent_id, deque(maxlen=200))
        ring.append(report)

        # Redis (best effort, don't block on failure)
        try:
            from app.config import settings
            import redis.asyncio as aioredis
            r = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=5,
                decode_responses=True,
            )
            key = f"latency:{self.call_log_id}"
            await r.rpush(key, json.dumps(report))
            await r.expire(key, 86400 * 7)  # 7 days
            await r.aclose()
        except Exception as exc:
            logger.debug("[latency] Redis flush failed: %s", exc)

        return report


def get_agent_latency_stats(agent_id: str) -> dict:
    """
    Compute P50/P95/P99 latency stats from the in-memory ring buffer.
    Returns dict with per-component percentiles.
    """
    ring = list(_agent_latency_ring.get(agent_id, []))
    if not ring:
        return {}

    def _pct(values: list[float], p: float) -> Optional[float]:
        if not values:
            return None
        idx = max(0, int(len(values) * p / 100) - 1)
        return sorted(values)[idx]

    def _stats(key: str) -> dict:
        vals = [r[key] for r in ring if r.get(key) is not None]
        return {
            "p50": _pct(vals, 50),
            "p95": _pct(vals, 95),
            "p99": _pct(vals, 99),
            "avg": round(sum(vals) / len(vals), 1) if vals else None,
            "sample_count": len(vals),
        }

    return {
        "stt_ms": _stats("stt_ms"),
        "rag_ms": _stats("rag_ms"),
        "llm_ttft_ms": _stats("llm_ttft_ms"),
        "tts_ms": _stats("tts_ms"),
        "total_ms": _stats("total_ms"),
    }
