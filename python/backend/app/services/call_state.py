"""
Call State Machine — Patent Claim 8.

Each active call has a state stored in Redis:
  call_state:{call_sid} → JSON {"state": "speaking", "agent_id": "...", "tenant_id": "..."}

Valid transitions
-----------------
  idle       → listening
  listening  → thinking  | listening (restart)
  thinking   → speaking  | listening (abort)
  speaking   → listening
  any        → listening  (interruption — always allowed)
"""
from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger("voiceflow.call_state")

# TTL for call-state Redis key (2 hours)
_STATE_TTL = 7200


class CallState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


# States each state can transition INTO (excluding the universal → LISTENING rule)
_VALID_TRANSITIONS: dict[CallState, set[CallState]] = {
    CallState.IDLE: {CallState.LISTENING},
    CallState.LISTENING: {CallState.THINKING, CallState.LISTENING},
    CallState.THINKING: {CallState.SPEAKING, CallState.LISTENING},
    CallState.SPEAKING: {CallState.LISTENING},
}


class CallStateManager:
    """Manage per-call state in Redis."""

    def __init__(self, redis_client) -> None:
        self.redis = redis_client

    # ── Key helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _key(call_sid: str) -> str:
        return f"call_state:{call_sid}"

    # ── CRUD ─────────────────────────────────────────────────────────────────

    async def create(self, call_sid: str, agent_id: str, tenant_id: str) -> None:
        """Initialise call state in Redis with TTL=2h."""
        data = json.dumps({
            "state": CallState.IDLE.value,
            "agent_id": agent_id,
            "tenant_id": tenant_id,
        })
        await self.redis.setex(self._key(call_sid), _STATE_TTL, data)
        logger.info("[call_state] created call=%s agent=%s", call_sid, agent_id)

    async def get(self, call_sid: str) -> CallState:
        """Return the current state; defaults to IDLE if not found."""
        raw = await self.redis.get(self._key(call_sid))
        if not raw:
            return CallState.IDLE
        try:
            data = json.loads(raw)
            return CallState(data.get("state", CallState.IDLE.value))
        except (json.JSONDecodeError, ValueError):
            return CallState.IDLE

    async def transition(self, call_sid: str, new_state: CallState) -> bool:
        """
        Validate and execute a state transition.
        Returns True if the transition was applied; False if it was rejected.

        Transition rules:
          • Any → LISTENING  is always allowed (supports barge-in).
          • Other transitions follow _VALID_TRANSITIONS.
        """
        current = await self.get(call_sid)

        # Universal rule: any state → LISTENING
        if new_state == CallState.LISTENING:
            await self._set_state(call_sid, new_state)
            logger.debug("[call_state] %s → %s (call=%s)", current, new_state, call_sid)
            return True

        allowed = _VALID_TRANSITIONS.get(current, set())
        if new_state not in allowed:
            logger.warning(
                "[call_state] rejected %s → %s (call=%s)", current, new_state, call_sid
            )
            return False

        await self._set_state(call_sid, new_state)
        logger.debug("[call_state] %s → %s (call=%s)", current, new_state, call_sid)
        return True

    async def is_interruptible(self, call_sid: str) -> bool:
        """Return True if the call is currently in SPEAKING state (can be barged in on)."""
        return (await self.get(call_sid)) == CallState.SPEAKING

    async def delete(self, call_sid: str) -> None:
        """Remove the call-state key from Redis."""
        await self.redis.delete(self._key(call_sid))
        logger.info("[call_state] deleted call=%s", call_sid)

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _set_state(self, call_sid: str, state: CallState) -> None:
        """Update the state field in-place, preserving agent_id/tenant_id."""
        key = self._key(call_sid)
        raw = await self.redis.get(key)
        if raw:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}
        data["state"] = state.value
        await self.redis.setex(key, _STATE_TTL, json.dumps(data))
