"""
Request-level middleware for VoiceFlow.

- Attaches a unique X-Request-ID to every request/response for distributed tracing.
- Logs method, path, status and duration for every request at INFO level.
"""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("voiceflow.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach X-Request-ID and log each request with timing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.monotonic()

        response: Response = await call_next(request)

        duration_ms = int((time.monotonic() - start) * 1000)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "%s %s %s %dms rid=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response
