"""
IVR (Interactive Voice Response) Tree Service.

A visual-config routing layer that sits before the AI agent.
Callers hear a menu ("Press 1 for Sales, 2 for Support") and are routed
to the correct specialist agent based on DTMF input.

Tree format (stored as JSON in IVRTree.nodes):
[
  {
    "id": "root",
    "message": "Thank you for calling Acme. Press 1 for Sales, 2 for Support, 3 to repeat.",
    "timeout_seconds": 5,
    "max_retries": 2,
    "children": [
      {"id": "n1", "dtmf": "1", "label": "Sales", "agentId": "agent-uuid-1"},
      {"id": "n2", "dtmf": "2", "label": "Support", "agentId": "agent-uuid-2"},
      {"id": "n3", "dtmf": "3", "label": "Repeat",  "goto": "root"}
    ]
  }
]

The Twilio-facing route (/voice/ivr/{tree_id}) renders TwiML <Gather> menus
and delegates to voice_inbound_router when a leaf node (agentId) is reached.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import IVRTree, Agent

logger = logging.getLogger("voiceflow.ivr")


def _find_node(nodes: list[dict], node_id: str) -> Optional[dict]:
    """BFS search for a node by id in the tree."""
    stack = list(nodes)
    while stack:
        node = stack.pop(0)
        if node.get("id") == node_id:
            return node
        stack.extend(node.get("children", []))
    return None


def _find_node_by_dtmf(parent_node: dict, digit: str) -> Optional[dict]:
    """Return the child node matching a DTMF digit."""
    for child in parent_node.get("children", []):
        if str(child.get("dtmf", "")) == str(digit):
            return child
    return None


def render_gather_twiml(tree: IVRTree, node_id: str = "root", base_url: str = "") -> str:
    """
    Render a <Gather> TwiML response for an IVR node.
    base_url: the public URL prefix for the gather action webhook.
    """
    from twilio.twiml.voice_response import VoiceResponse, Gather

    nodes = tree.nodes or []
    node = _find_node(nodes, node_id) if node_id != "root" else (nodes[0] if nodes else None)
    if not node:
        vr = VoiceResponse()
        vr.say("Sorry, this menu is not configured. Goodbye.")
        vr.hangup()
        return str(vr)

    resp = VoiceResponse()
    message = node.get("message", "Please press a key.")
    timeout = int(node.get("timeout_seconds", 5))
    action_url = f"{base_url}/api/ivr/voice/{tree.id}/gather?node={node.get('id', 'root')}"

    gather = Gather(
        num_digits=1,
        action=action_url,
        timeout=timeout,
        input="dtmf",
    )
    gather.say(message)
    resp.append(gather)
    # Fallback if no input
    resp.redirect(action_url + "&timeout=1")
    return str(resp)


async def resolve_dtmf(
    tree: IVRTree,
    node_id: str,
    digit: str,
    db: AsyncSession,
    base_url: str = "",
) -> tuple[str, Optional[str]]:
    """
    Given the current node and a DTMF digit, return:
      (twiml_response, agent_id_or_none)

    If the matching child is a leaf (has agentId), returns (redirect_twiml, agent_id).
    If it's a goto, re-renders the target node.
    If not found, re-renders current node with error message.
    """
    from twilio.twiml.voice_response import VoiceResponse

    nodes = tree.nodes or []
    current_node = _find_node(nodes, node_id) or (nodes[0] if nodes else None)
    if not current_node:
        vr = VoiceResponse()
        vr.say("Configuration error. Goodbye.")
        vr.hangup()
        return str(vr), None

    child = _find_node_by_dtmf(current_node, digit)
    if not child:
        # Invalid input — replay current menu
        vr = VoiceResponse()
        vr.say("That option is not available. ")
        twiml = render_gather_twiml(tree, node_id=current_node["id"], base_url=base_url)
        return twiml, None

    # goto: re-render another node
    if child.get("goto"):
        return render_gather_twiml(tree, node_id=child["goto"], base_url=base_url), None

    # Sub-menu: render the child node
    if child.get("children"):
        return render_gather_twiml(tree, node_id=child["id"], base_url=base_url), None

    # Leaf → route to agent
    agent_id = child.get("agentId")
    if not agent_id:
        vr = VoiceResponse()
        vr.say("This department is currently unavailable. Goodbye.")
        vr.hangup()
        return str(vr), None

    # Verify agent exists
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        vr = VoiceResponse()
        vr.say("Routing failed. Goodbye.")
        vr.hangup()
        return str(vr), None

    vr = VoiceResponse()
    label = child.get("label", "the appropriate team")
    vr.say(f"Connecting you to {label}.")
    # Redirect to the agent's inbound handler — path param, not query param
    vr.redirect(f"{base_url}/api/voice/inbound/{agent_id}")
    return str(vr), agent_id
