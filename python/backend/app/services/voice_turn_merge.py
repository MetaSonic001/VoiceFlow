"""
Merge adjacent STT segments when the caller pauses mid-thought (semantic incomplete).

If faster-whisper ends a segment at a short silence but the text looks incomplete,
we hold the text and merge the next segment after the caller resumes speaking.
If no continuation arrives within ~1.5s, we flush anyway (cutoff recovery).

Also exposes clear_turn_merge() — call on barge-in / buffer reset so stale merges
do not attach to the next utterance.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Awaitable, Callable

from app.services.semantic_vad import is_turn_complete

logger = logging.getLogger("voiceflow.turn_merge")

_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
_pending: dict[str, str] = {}
_timers: dict[str, asyncio.Task] = {}
_FLUSH_TIMEOUT_S = 1.45
_MAX_MERGED_CHARS = 420


async def integrate_user_text(
    call_sid: str,
    segment: str,
    *,
    on_complete: Callable[[str], Awaitable[None]],
    timeout_s: float = _FLUSH_TIMEOUT_S,
) -> None:
    """
    Merge *segment* with any held incomplete text for this call.

    When the merged text looks like a complete turn (or is long enough), calls
    ``on_complete(merged)`` immediately. Otherwise stores pending text and
    schedules *on_complete* after ``timeout_s`` unless more speech arrives.
    """
    key = call_sid or "_anon"
    segment = (segment or "").strip()
    if not segment:
        return

    flush_immediately: str | None = None
    old_timer = None

    async with _locks[key]:
        base = _pending.pop(key, "")
        merged = f"{base} {segment}".strip() if base else segment

        old_timer = _timers.pop(key, None)
        if old_timer and not old_timer.done():
            old_timer.cancel()

        complete = await is_turn_complete(merged)
        if complete or len(merged) >= _MAX_MERGED_CHARS:
            flush_immediately = merged
        else:
            _pending[key] = merged

    if old_timer and not old_timer.done():
        try:
            await old_timer
        except asyncio.CancelledError:
            pass

    if flush_immediately is not None:
        await on_complete(flush_immediately)
        return

    async def _delayed() -> None:
        try:
            await asyncio.sleep(timeout_s)
            text_to_flush: str | None = None
            async with _locks[key]:
                text_to_flush = _pending.pop(key, None)
                _timers.pop(key, None)
            if text_to_flush:
                logger.debug("[turn_merge] timeout flush call=%s len=%d", key, len(text_to_flush))
                await on_complete(text_to_flush)
        except asyncio.CancelledError:
            pass

    async with _locks[key]:
        _timers[key] = asyncio.create_task(_delayed())


def clear_turn_merge(call_sid: str) -> None:
    """Cancel pending merge state (barge-in, new utterance reset, hangup)."""
    key = call_sid or "_anon"
    _pending.pop(key, None)
    t = _timers.pop(key, None)
    if t and not t.done():
        t.cancel()
