"""
Flow Engine — executes a visual conversation flow graph.

Flow Definition JSON:
{
  "nodes": [
    {"id": "start", "type": "start"},
    {"id": "greet", "type": "greeting", "text": "Hello! How can I help?"},
    {"id": "check_intent", "type": "condition", "field": "intent",
                            "values": ["booking", "support"]},
    {"id": "book", "type": "api_call", "tool": "book_appointment"},
    {"id": "transfer", "type": "human_transfer", "number": "+91..."}
  ],
  "edges": [
    {"from": "start", "to": "greet"},
    {"from": "greet", "to": "check_intent"},
    {"from": "check_intent", "to": "book", "if": "booking"},
    {"from": "check_intent", "to": "transfer", "if": "support"}
  ]
}

Node types
----------
start          — entry point; no-op
greeting       — emit static text
knowledge      — query RAG pipeline for the user input
condition      — branch based on context field value or simple keyword match
api_call       — execute a named VoiceTool
human_transfer — emit a transfer signal with target number
end            — terminal node
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger("voiceflow.flow_engine")

_MAX_HOPS = 50  # guard against infinite loops in malformed flows


class FlowEngine:
    """Execute a JSON flow graph for a given user input + context."""

    async def execute(
        self,
        flow_definition: dict,
        context: dict,
        user_input: str,
    ) -> str:
        """
        Walk the flow graph from the 'start' node and return the final text response.

        context may contain:
          - tenant_id, agent_id, session_id  (for knowledge nodes)
          - db                               (SQLAlchemy AsyncSession)
          - intent                           (pre-detected intent string)
          - any other fields checked by condition nodes
        """
        nodes = {n["id"]: n for n in flow_definition.get("nodes", [])}
        # Build adjacency: node_id → list of (target_id, condition_value_or_None)
        edges: dict[str, list[tuple[str, Any]]] = {}
        for edge in flow_definition.get("edges", []):
            src = edge.get("from", "")
            dst = edge.get("to", "")
            condition = edge.get("if")  # None means unconditional
            edges.setdefault(src, []).append((dst, condition))

        # Find start node
        current_id: str = next(
            (n["id"] for n in flow_definition.get("nodes", []) if n.get("type") == "start"),
            "start",
        )

        output_parts: list[str] = []
        hops = 0

        while current_id and hops < _MAX_HOPS:
            hops += 1
            node = nodes.get(current_id)
            if not node:
                logger.warning("[flow_engine] node '%s' not found", current_id)
                break

            node_type = node.get("type", "")
            result_text, next_id = await self._execute_node(
                node=node,
                edges=edges,
                context=context,
                user_input=user_input,
            )

            if result_text:
                output_parts.append(result_text)

            if node_type == "end" or next_id is None:
                break

            current_id = next_id

        return " ".join(output_parts) if output_parts else "I'm here to help. Please tell me more."

    # ── Node executor ─────────────────────────────────────────────────────────

    async def _execute_node(
        self,
        node: dict,
        edges: dict,
        context: dict,
        user_input: str,
    ) -> tuple[str, str | None]:
        """
        Execute a single node.
        Returns (output_text, next_node_id).
        """
        node_id = node["id"]
        node_type = node.get("type", "")

        if node_type == "start":
            return "", self._pick_edge(edges, node_id, context, user_input, default_first=True)

        elif node_type == "greeting":
            text = node.get("text", "Hello!")
            # Substitute context variables
            text = self._interpolate(text, context)
            return text, self._pick_edge(edges, node_id, context, user_input, default_first=True)

        elif node_type == "knowledge":
            # Query the RAG pipeline
            response = await self._query_rag(node, context, user_input)
            return response, self._pick_edge(edges, node_id, context, user_input, default_first=True)

        elif node_type == "condition":
            # Choose the edge whose "if" value matches context[field] or user_input keywords
            field = node.get("field", "intent")
            field_value = str(context.get(field, user_input)).lower()
            candidates = edges.get(node_id, [])

            # Try exact match first
            for target_id, condition in candidates:
                if condition and condition.lower() in field_value:
                    return "", target_id

            # Unconditional fallback
            for target_id, condition in candidates:
                if condition is None:
                    return "", target_id

            # First edge as last-resort
            return "", candidates[0][0] if candidates else None

        elif node_type == "api_call":
            result_text = await self._execute_tool(node, context, user_input)
            return result_text, self._pick_edge(edges, node_id, context, user_input, default_first=True)

        elif node_type == "human_transfer":
            number = node.get("number", "")
            msg = node.get("text", f"Transferring you now.")
            context["_transfer_number"] = number
            return msg, None  # Terminal — caller handles the actual transfer

        elif node_type == "end":
            text = node.get("text", "")
            return text, None

        else:
            logger.warning("[flow_engine] unknown node type '%s'", node_type)
            return "", self._pick_edge(edges, node_id, context, user_input, default_first=True)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _pick_edge(
        self,
        edges: dict,
        node_id: str,
        context: dict,
        user_input: str,
        default_first: bool = False,
    ) -> str | None:
        """Return the first unconditional edge target (or None if no edges)."""
        candidates = edges.get(node_id, [])
        if not candidates:
            return None
        for target_id, condition in candidates:
            if condition is None:
                return target_id
        if default_first:
            return candidates[0][0]
        return None

    def _interpolate(self, text: str, context: dict) -> str:
        """Replace {{key}} placeholders with context values."""
        import re
        def replace(m):
            key = m.group(1).strip()
            return str(context.get(key, m.group(0)))
        return re.sub(r"\{\{([^}]+)\}\}", replace, text)

    async def _query_rag(self, node: dict, context: dict, user_input: str) -> str:
        """Call the RAG pipeline for a knowledge node."""
        from app.services.rag_service import process_query

        db = context.get("db")
        tenant_id = context.get("tenant_id", "")
        agent_id = context.get("agent_id", "")
        session_id = context.get("session_id", "default")
        query_override = node.get("query") or user_input

        if not db or not tenant_id:
            return "I don't have the information for that right now."

        try:
            result = await process_query(db, tenant_id, agent_id, query_override, session_id)
            return result.get("response", "")
        except Exception:
            logger.exception("[flow_engine] RAG query failed")
            return "I encountered an issue retrieving that information."

    async def _execute_tool(self, node: dict, context: dict, user_input: str) -> str:
        """Execute a named VoiceTool."""
        from app.services.voice_tools import TOOL_REGISTRY, VoiceToolExecutor

        tool_name = node.get("tool", "")
        tool_args = node.get("arguments", {})

        # Allow argument values to be interpolated from context
        resolved_args = {k: self._interpolate(str(v), context) for k, v in tool_args.items()}

        tool = TOOL_REGISTRY.get(tool_name)
        if not tool:
            return f"Tool '{tool_name}' is not available."

        executor = VoiceToolExecutor()
        try:
            result = await executor.execute(tool, resolved_args)
            if "error" in result:
                return f"I couldn't complete that action: {result['error']}"
            return node.get("success_text", "Done.")
        except Exception:
            logger.exception("[flow_engine] tool execution failed: %s", tool_name)
            return "I encountered an issue performing that action."


# Module-level singleton
flow_engine = FlowEngine()
