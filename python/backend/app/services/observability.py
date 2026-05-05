"""
Observability Service — structured tracing for every LLM, STT, TTS, and RAG call.

Uses OpenTelemetry-compatible trace format.  Traces are:
  1. Streamed to Langfuse (self-hostable, open-source) when LANGFUSE_SECRET_KEY is set
  2. Emitted as structured JSON logs otherwise (works without any external service)

Every trace captures:
  - span_type: stt | rag_retrieval | llm | tts | tool_call | full_turn
  - tenant_id, agent_id, call_log_id, session_id
  - latency_ms: wall clock
  - token counts (input / output / total) for LLM spans
  - retrieval scores for RAG spans
  - error info if the span failed

Usage:
  from app.services.observability import trace_span

  async with trace_span("llm", tenant_id=..., agent_id=...) as span:
      span["model"] = "llama-3.3-70b-versatile"
      response = await llm_call(...)
      span["output_tokens"] = response.usage.completion_tokens

pip install langfuse   (optional — falls back to JSON logging)
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional

logger = logging.getLogger("voiceflow.observability")

_LANGFUSE_AVAILABLE = False

try:
    from langfuse import Langfuse  # type: ignore
    _LANGFUSE_AVAILABLE = True
except ImportError:
    pass

from app.config import settings


def _get_langfuse() -> Optional[Any]:
    """Lazy singleton Langfuse client."""
    key = getattr(settings, "LANGFUSE_SECRET_KEY", None)
    pk = getattr(settings, "LANGFUSE_PUBLIC_KEY", None)
    host = getattr(settings, "LANGFUSE_HOST", "https://cloud.langfuse.com")
    if not _LANGFUSE_AVAILABLE or not key:
        return None
    try:
        return Langfuse(secret_key=key, public_key=pk or "", host=host)
    except Exception:
        return None


def _log_trace(event: dict) -> None:
    """Emit trace as structured JSON to the logger."""
    try:
        logger.info("[trace] %s", json.dumps(event))
    except Exception:
        pass


@asynccontextmanager
async def trace_span(
    span_type: str,
    tenant_id: str = "",
    agent_id: str = "",
    call_log_id: str = "",
    session_id: str = "",
    **initial_attrs: Any,
) -> AsyncGenerator[dict, None]:
    """
    Context manager that measures latency and emits a trace event.

    Usage:
      async with trace_span("llm", tenant_id=...) as span:
          span["model"] = "llama-3.3-70b"
          span["input_tokens"] = 500
          result = await chat(...)
          span["output_tokens"] = result.usage.completion_tokens

    On exit, span is automatically enriched with latency_ms and flushed.
    """
    start = time.monotonic()
    span: dict[str, Any] = {
        "span_type": span_type,
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "call_log_id": call_log_id,
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error": None,
        **initial_attrs,
    }
    try:
        yield span
    except Exception as exc:
        span["error"] = str(exc)
        raise
    finally:
        span["latency_ms"] = round((time.monotonic() - start) * 1000, 1)
        _emit_span(span)


def _emit_span(span: dict) -> None:
    """Emit span to Langfuse or JSON logger."""
    lf = _get_langfuse()
    if lf:
        try:
            # Map to Langfuse generation (for LLM spans) or span (for others)
            if span["span_type"] == "llm":
                lf.generation(
                    name=span.get("model", "llm"),
                    trace_id=span.get("call_log_id") or span.get("session_id"),
                    input=span.get("input_preview"),
                    output=span.get("output_preview"),
                    usage={
                        "input": span.get("input_tokens", 0),
                        "output": span.get("output_tokens", 0),
                        "total": span.get("total_tokens", 0),
                    },
                    metadata={k: v for k, v in span.items() if k not in ("input_preview", "output_preview")},
                )
            else:
                lf.span(
                    name=span["span_type"],
                    trace_id=span.get("call_log_id") or span.get("session_id"),
                    metadata=span,
                )
            lf.flush()
        except Exception as exc:
            logger.debug("[observability] Langfuse emit failed: %s", exc)
            _log_trace(span)
    else:
        _log_trace(span)


def record_latency(component: str, latency_ms: float, **tags: Any) -> None:
    """
    One-shot latency recording without a context manager.
    Used where the operation is sync or the span pattern is inconvenient.
    """
    _emit_span({"span_type": component, "latency_ms": latency_ms, **tags})
