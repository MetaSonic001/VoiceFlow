"""
Stateful workflow engine for guided conversations (qualification trees, branching, slots).

Works with agent.flowDefinition JSON from the flow builder. Persists per-session state in Redis
so phone and chat sessions advance monotonically through nodes across turns.

Supported node types (extends flow_engine patterns):
  start, greeting, knowledge, condition, api_call, human_transfer, end  — builder defaults
  collect      — capture a named slot from user text (regex patterns optional)
  instruction  — LLM directive only; advances after one assistant reply

Edges: { "from", "to", "if": "yes"|"no"|keyword, "label": ... }
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("voiceflow.workflow_runtime")

_MAX_HOPS = 80


async def _audit_workflow_node(
    tenant_id: str,
    agent_id: str,
    session_id: str,
    node_id: str,
    slot_keys: list[str],
) -> None:
    try:
        from app.services.audit_service import record_session_audit_event

        await record_session_audit_event(
            tenant_id,
            session_id,
            agent_id,
            "call_audit.workflow.blocking_node",
            details={"node_id": node_id, "slot_keys": slot_keys},
        )
    except Exception:
        logger.debug("[workflow] audit event failed", exc_info=True)

# Default extraction patterns when author omits them
_DEFAULT_SLOT_PATTERNS: dict[str, list[str]] = {
    "phone": [
        r"(?i)(?:phone|mobile|number|call me at)[:\s]+([\d\+\-\s\(\)]{8,})",
        r"(?i)\b(\+?\d[\d\-\s]{8,}\d)\b",
    ],
    "email": [r"(?i)\b([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})\b"],
    "age": [r"(?i)\b(?:age|i am|i'm)\s*[:\s]*(\d{1,3})\b", r"(?i)\b(\d{1,3})\s*(?:years old|yo)\b"],
}


_STATE_TTL_SECONDS = 86400  # align with conversation Redis TTL


def _state_key(tenant_id: str, agent_id: str, session_id: str) -> str:
    return f"workflow:{tenant_id}:{agent_id}:{session_id}"


async def load_state(tenant_id: str, agent_id: str, session_id: str) -> Optional[dict]:
    from app.services.rag_service import get_redis

    r = await get_redis()
    if not r:
        return None
    try:
        raw = await r.get(_state_key(tenant_id, agent_id, session_id))
        if raw:
            return json.loads(raw)
    except Exception:
        logger.exception("[workflow] load_state failed")
    return None


async def save_state(tenant_id: str, agent_id: str, session_id: str, state: dict) -> None:
    from app.services.rag_service import get_redis

    r = await get_redis()
    if not r:
        return
    try:
        await r.set(_state_key(tenant_id, agent_id, session_id), json.dumps(state), ex=_STATE_TTL_SECONDS)
    except Exception:
        logger.exception("[workflow] save_state failed")


async def clear_state(tenant_id: str, agent_id: str, session_id: str) -> None:
    from app.services.rag_service import get_redis

    r = await get_redis()
    if not r:
        return
    try:
        await r.delete(_state_key(tenant_id, agent_id, session_id))
    except Exception:
        pass


def _norm_flow(flow_definition: dict | None) -> tuple[dict[str, dict], dict[str, list[tuple[str, Any]]]]:
    if not flow_definition:
        return {}, {}
    nodes_list = flow_definition.get("nodes") or []
    nodes = {n["id"]: n for n in nodes_list if n.get("id")}
    edges: dict[str, list[tuple[str, Any]]] = {}
    for edge in flow_definition.get("edges") or []:
        src = edge.get("from", "")
        dst = edge.get("to", "")
        condition = edge.get("if")
        if condition is None:
            lab = edge.get("label")
            if lab in ("yes", "no"):
                condition = lab
        edges.setdefault(src, []).append((dst, condition))
    return nodes, edges


def _find_start_id(nodes: dict[str, dict]) -> str:
    for nid, n in nodes.items():
        if n.get("type") == "start":
            return nid
    return "start" if "start" in nodes else next(iter(nodes), "start")


def _pick_unconditional(edges_map: dict, node_id: str) -> Optional[str]:
    for target, cond in edges_map.get(node_id, []):
        if cond is None:
            return target
    cands = edges_map.get(node_id, [])
    return cands[0][0] if cands else None


def _pick_condition_branch(
    node: dict,
    edges_map: dict,
    nodes: dict[str, dict],
    slots: dict[str, str],
    user_lower: str,
) -> Optional[str]:
    """Resolve condition node — yes/no edges or keyword edges."""
    nid = node["id"]
    candidates = edges_map.get(nid, [])
    field_name = (node.get("field") or "").strip()

    haystack = user_lower
    if field_name and field_name in slots:
        haystack = f"{user_lower} {str(slots[field_name]).lower()}"

    # yes / no — keyword presence
    yes_tgt = no_tgt = None
    keyword_targets: list[tuple[str, str]] = []
    for target, cond in candidates:
        if cond is None:
            continue
        cs = str(cond).lower()
        if cs == "yes":
            yes_tgt = target
        elif cs == "no":
            no_tgt = target
        else:
            keyword_targets.append((target, cs))

    if yes_tgt or no_tgt:
        # crude intent: affirmative / negative
        yes_signals = ("yes", "yeah", "yep", "sure", "interested", "ok", "okay", "please", "haan", "हाँ")
        no_signals = ("no", "nope", "not", "don't", "dont", "nah", "not interested")
        if any(s in haystack for s in yes_signals) and yes_tgt:
            return yes_tgt
        if any(s in haystack for s in no_signals) and no_tgt:
            return no_tgt

    for target, kw in keyword_targets:
        if kw and kw in haystack:
            return target

    # substring match on edge keywords (legacy flow_engine style)
    for target, cond in candidates:
        if cond is None:
            continue
        cs = str(cond).lower()
        if cs not in ("yes", "no") and cs and cs in haystack:
            return target

    # fallback: first unconditional
    return _pick_unconditional(edges_map, nid)


def _extract_slot(node: dict, user_message: str) -> Optional[str]:
    slot = (node.get("slot") or node.get("field") or "").strip()
    if not slot:
        return None
    patterns = node.get("patterns")
    if isinstance(patterns, str):
        patterns = [patterns]
    if not patterns:
        patterns = _DEFAULT_SLOT_PATTERNS.get(slot.lower(), [])

    for p in patterns:
        try:
            m = re.search(p, user_message.strip())
            if m:
                return (m.group(m.lastindex or 1) if m.lastindex else m.group(0)).strip()
        except re.error:
            continue

    # Short single-line utterance → whole text as value (name-like)
    msg = user_message.strip()
    if msg and len(msg) <= 120 and "\n" not in msg:
        # Avoid capturing obvious questions as names
        if not msg.endswith("?") and slot.lower() in ("name", "full_name", "fullname"):
            return msg
        if slot.lower() in ("notes", "detail", "details", "description"):
            return msg

    return None


def _node_advances_after_reply(node: dict) -> bool:
    if node.get("advanceAfterReply") is True:
        return True
    if node.get("advanceAfterReply") is False:
        return False
    t = node.get("type", "")
    return t in ("greeting", "knowledge", "instruction", "api_call", "human_transfer")


def _directive_for_node(node: dict, slots: dict[str, str]) -> str:
    """Build LLM instruction text for the current blocking node."""
    t = node.get("type", "")
    parts: list[str] = []

    def interp(s: str) -> str:
        out = s
        for k, v in slots.items():
            out = out.replace("{{" + k + "}}", str(v))
        out = out.replace("{{name}}", slots.get("name", slots.get("full_name", "")))
        return out

    if t == "greeting":
        parts.append(interp(node.get("text") or "Greet the caller warmly and briefly ask how you can help."))
    elif t == "knowledge":
        hint = node.get("text") or ""
        parts.append(
            "Answer using the knowledge base context when relevant. "
            + (interp(hint) if hint else "Respond helpfully to the user's question.")
        )
    elif t == "instruction":
        parts.append(interp(node.get("text") or node.get("prompt") or "Follow the conversation naturally."))
    elif t == "collect":
        ask = interp(node.get("ask") or node.get("text") or "")
        slot = node.get("slot") or node.get("field") or "value"
        parts.append(
            f"Your immediate priority is to obtain: **{slot}**. "
            + (ask or f"Ask the user for this information clearly and politely.")
        )
        if slots:
            parts.append(f"Facts already collected this session: {json.dumps(slots)}")
    elif t == "condition":
        parts.append(
            node.get("text")
            or "Use the user's answer to branch logically (yes/no or intent). Reply briefly and clearly."
        )
    elif t == "api_call":
        parts.append(f"When appropriate, the scenario expects tool use: `{node.get('tool', '')}`.")
    elif t == "human_transfer":
        parts.append(node.get("text") or "Let the caller know you will transfer them to a specialist.")
    elif t == "end":
        parts.append(node.get("text") or "Conclude politely.")
    else:
        parts.append(node.get("text") or "")

    text = "\n".join(p for p in parts if p)
    return text.strip()


@dataclass
class WorkflowTurnResult:
    directive: str = ""
    slots: dict[str, str] = field(default_factory=dict)
    active: bool = False
    response_node_id: Optional[str] = None
    advance_after_reply: bool = False


async def before_llm_turn(
    *,
    tenant_id: str,
    agent_id: str,
    session_id: str,
    flow_definition: dict | None,
    user_message: str,
    workflow_enabled: bool,
) -> WorkflowTurnResult:
    """
    Run state machine before the LLM call. Updates Redis state.
    Returns guidance text to inject into the system prompt.
    """
    out = WorkflowTurnResult()
    if not workflow_enabled or not flow_definition:
        return out

    nodes, edges_map = _norm_flow(flow_definition)
    if not nodes:
        return out

    state = await load_state(tenant_id, agent_id, session_id)
    if not state:
        state = {"node_id": _find_start_id(nodes), "slots": {}}

    node_id = state.get("node_id") or _find_start_id(nodes)
    slots: dict[str, str] = dict(state.get("slots") or {})

    user_lower = user_message.strip().lower()

    hops = 0
    while hops < _MAX_HOPS:
        hops += 1
        node = nodes.get(node_id)
        if not node:
            logger.warning("[workflow] missing node %s", node_id)
            break

        nt = node.get("type", "")

        if nt == "end":
            out.directive = _directive_for_node(node, slots)
            out.active = True
            out.response_node_id = node_id
            out.advance_after_reply = False
            state = {"node_id": node_id, "slots": slots}
            await save_state(tenant_id, agent_id, session_id, state)
            out.slots = slots
            await _audit_workflow_node(tenant_id, agent_id, session_id, node_id, list(slots.keys()))
            return out

        if nt == "start":
            nxt = _pick_unconditional(edges_map, node_id)
            if not nxt:
                break
            node_id = nxt
            continue

        if nt == "condition":
            target = _pick_condition_branch(node, edges_map, nodes, slots, user_lower)
            if target:
                node_id = target
                continue
            # Stay — need clarification
            out.directive = _directive_for_node(node, slots)
            out.active = True
            out.response_node_id = node_id
            out.advance_after_reply = False
            state = {"node_id": node_id, "slots": slots}
            await save_state(tenant_id, agent_id, session_id, state)
            out.slots = slots
            await _audit_workflow_node(tenant_id, agent_id, session_id, node_id, list(slots.keys()))
            return out

        if nt == "collect":
            slot_name = (node.get("slot") or node.get("field") or "").strip()
            if slot_name and slot_name not in slots and user_message.strip():
                val = _extract_slot(node, user_message)
                if val:
                    slots[slot_name] = val
                    nxt = _pick_unconditional(edges_map, node_id)
                    if nxt:
                        node_id = nxt
                        continue
            # Blocking until slot filled
            if slot_name and slot_name not in slots:
                out.directive = _directive_for_node(node, slots)
                out.active = True
                out.response_node_id = node_id
                out.advance_after_reply = False
                state = {"node_id": node_id, "slots": slots}
                await save_state(tenant_id, agent_id, session_id, state)
                out.slots = slots
                await _audit_workflow_node(tenant_id, agent_id, session_id, node_id, list(slots.keys()))
                return out
            nxt = _pick_unconditional(edges_map, node_id)
            if nxt:
                node_id = nxt
                continue
            break

        # Transient nodes: emit directive then advance after assistant reply
        if nt in ("greeting", "knowledge", "instruction"):
            out.directive = _directive_for_node(node, slots)
            out.active = True
            out.response_node_id = node_id
            out.advance_after_reply = _node_advances_after_reply(node)
            state = {"node_id": node_id, "slots": slots, "_await_reply": out.advance_after_reply}
            await save_state(tenant_id, agent_id, session_id, state)
            out.slots = slots
            await _audit_workflow_node(tenant_id, agent_id, session_id, node_id, list(slots.keys()))
            return out

        if nt == "api_call":
            out.directive = _directive_for_node(node, slots)
            out.active = True
            out.response_node_id = node_id
            out.advance_after_reply = True
            state = {"node_id": node_id, "slots": slots, "_await_reply": True}
            await save_state(tenant_id, agent_id, session_id, state)
            out.slots = slots
            await _audit_workflow_node(tenant_id, agent_id, session_id, node_id, list(slots.keys()))
            return out

        if nt == "human_transfer":
            out.directive = _directive_for_node(node, slots)
            out.active = True
            out.response_node_id = node_id
            out.advance_after_reply = True
            state = {"node_id": node_id, "slots": slots, "_await_reply": True}
            await save_state(tenant_id, agent_id, session_id, state)
            out.slots = slots
            await _audit_workflow_node(tenant_id, agent_id, session_id, node_id, list(slots.keys()))
            return out

        # Unknown / legacy: try unconditional advance
        nxt = _pick_unconditional(edges_map, node_id)
        if nxt:
            node_id = nxt
            continue
        break

    # Fallback directive
    out.slots = slots
    return out


async def after_llm_turn(
    *,
    tenant_id: str,
    agent_id: str,
    session_id: str,
    flow_definition: dict | None,
    workflow_enabled: bool,
    response_node_id: Optional[str],
) -> None:
    """Advance graph after assistant message when node was transient."""
    if not workflow_enabled or not flow_definition or not response_node_id:
        return

    nodes, edges_map = _norm_flow(flow_definition)
    node = nodes.get(response_node_id)
    if not node:
        return

    if not _node_advances_after_reply(node):
        # Still clear await flag if set
        state = await load_state(tenant_id, agent_id, session_id)
        if state:
            state.pop("_await_reply", None)
            await save_state(tenant_id, agent_id, session_id, state)
        return

    nxt = _pick_unconditional(edges_map, response_node_id)
    if nxt:
        try:
            from app.services.audit_service import record_session_audit_event

            await record_session_audit_event(
                tenant_id,
                session_id,
                agent_id,
                "call_audit.workflow.advance",
                details={"from_node": response_node_id, "to_node": nxt},
            )
        except Exception:
            logger.debug("[workflow] advance audit failed", exc_info=True)

        state = await load_state(tenant_id, agent_id, session_id) or {"slots": {}}
        slots = dict(state.get("slots") or {})
        await save_state(
            tenant_id,
            agent_id,
            session_id,
            {"node_id": nxt, "slots": slots},
        )
    else:
        await clear_state(tenant_id, agent_id, session_id)


def workflow_should_run(
    agent_prefs: dict | None,
    flow_definition: dict | None,
) -> bool:
    """Honor llmPreferences.workflowEnabled — default True when graph non-empty."""
    if not flow_definition:
        return False
    nodes = flow_definition.get("nodes") or []
    if not nodes:
        return False
    prefs = agent_prefs or {}
    if prefs.get("workflowEnabled") is False:
        return False
    return True
