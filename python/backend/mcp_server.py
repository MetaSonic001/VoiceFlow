"""
VoiceFlow MCP Server — FastMCP-based Model Context Protocol server.

Exposes VoiceFlow capabilities as MCP tools usable from Claude Desktop, Cursor,
and any MCP-compatible client. Mirrors OmniDimension's MCP server offering.

Tools exposed:
  create_agent          — create an AI agent from a description or full config
  make_call             — initiate an outbound call via an agent
  get_call_summary      — retrieve call transcript + analysis for a call
  search_knowledge_base — semantic search over an agent's knowledge base
  get_analytics         — agent performance stats
  run_simulation        — run test scenarios against an agent
  list_agents           — list all agents for a tenant

Usage (install server):
  pip install fastmcp
  python mcp_server.py            # starts stdio MCP server
  fastmcp run mcp_server.py       # alternative

Configure in Claude Desktop ~/.config/claude_desktop_config.json:
  {
    "mcpServers": {
      "voiceflow": {
        "command": "python",
        "args": ["/path/to/python/backend/mcp_server.py"],
        "env": {
          "VOICEFLOW_API_URL": "http://localhost:8040",
          "VOICEFLOW_TENANT_ID": "your-tenant-id",
          "VOICEFLOW_USER_ID": "your-user-id"
        }
      }
    }
  }
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

import httpx

try:
    from fastmcp import FastMCP
except ImportError:
    raise ImportError(
        "fastmcp is required for the MCP server. Install it with: pip install fastmcp"
    )

# ── Config ─────────────────────────────────────────────────────────────────────

API_URL = os.getenv("VOICEFLOW_API_URL", "http://localhost:8040")
TENANT_ID = os.getenv("VOICEFLOW_TENANT_ID", "")
USER_ID = os.getenv("VOICEFLOW_USER_ID", "")

_HEADERS = {
    "x-tenant-id": TENANT_ID,
    "x-user-id": USER_ID,
    "Content-Type": "application/json",
}

mcp = FastMCP(
    "VoiceFlow",
    instructions=(
        "VoiceFlow is an AI voice agent platform. "
        "Use these tools to create agents, make calls, "
        "search knowledge bases, and analyze call performance. "
        "Always provide tenant_id and user_id when creating resources."
    ),
)


# ── HTTP helper ────────────────────────────────────────────────────────────────

def _url(path: str) -> str:
    return f"{API_URL.rstrip('/')}/{path.lstrip('/')}"


async def _get(path: str, params: dict | None = None) -> Any:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(_url(path), headers=_HEADERS, params=params)
        resp.raise_for_status()
        return resp.json()


async def _post(path: str, body: dict) -> Any:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(_url(path), headers=_HEADERS, json=body)
        resp.raise_for_status()
        return resp.json()


# ── MCP Tools ──────────────────────────────────────────────────────────────────

@mcp.tool()
async def create_agent(
    description: str,
    name: Optional[str] = None,
    voice_type: str = "female",
    create_immediately: bool = True,
) -> dict:
    """
    Create a VoiceFlow AI agent from a plain-language description.
    The LLM auto-fills all configuration fields from the description.

    Args:
        description: Plain-English description of the agent.
                     E.g. "A friendly sales agent for our SaaS that books demo calls"
        name: Optional override for the agent name (LLM will generate one if not given)
        voice_type: "male" or "female"
        create_immediately: If True, creates and returns an agent_id immediately.
                           If False, returns the config for review without creating.

    Returns:
        Agent config dict. Includes agentId if create_immediately=True.
    """
    body: dict = {"prompt": description, "create": create_immediately}
    result = await _post("/api/agents/generate-from-prompt", body)
    if name and create_immediately and result.get("agentId"):
        # Update the name if overridden
        agent_id = result["agentId"]
        await _post(f"/api/agents/{agent_id}", {"name": name})
        result["name"] = name
    return result


@mcp.tool()
async def list_agents(search: Optional[str] = None) -> list[dict]:
    """
    List all AI agents for the configured tenant.

    Args:
        search: Optional filter by agent name

    Returns:
        List of agents with id, name, status, totalCalls, successRate.
    """
    params = {}
    if search:
        params["search"] = search
    data = await _get("/api/agents/", params or None)
    agents = data.get("agents", [])
    return [
        {
            "id": a["id"],
            "name": a["name"],
            "status": a["status"],
            "totalCalls": a.get("totalCalls", 0),
            "successRate": a.get("successRate"),
            "channels": a.get("channels"),
        }
        for a in agents
    ]


@mcp.tool()
async def make_call(
    agent_id: str,
    to_phone: str,
    campaign_name: Optional[str] = None,
    contact_variables: Optional[dict] = None,
) -> dict:
    """
    Initiate an outbound call from a VoiceFlow agent to a phone number.

    Creates a single-contact campaign and starts it immediately.

    Args:
        agent_id: The VoiceFlow agent ID to make the call
        to_phone: E.164 phone number to call (e.g. +919876543210)
        campaign_name: Optional name for the campaign record
        contact_variables: Optional dict of variables injected into the agent context
                          (e.g. {"name": "Rahul", "product": "Premium Plan"})

    Returns:
        {"campaignId": "...", "status": "started", "contactsQueued": 1}
    """
    # Create campaign
    camp = await _post("/api/campaigns/", {
        "agentId": agent_id,
        "name": campaign_name or f"MCP call to {to_phone}",
    })
    campaign_id = camp["id"]

    # Upload single contact as CSV
    import io
    csv_content = "phone,name\n"
    name = (contact_variables or {}).get("name", "")
    csv_content += f"{to_phone},{name}\n"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            _url(f"/api/campaigns/{campaign_id}/contacts/upload"),
            headers={k: v for k, v in _HEADERS.items() if k != "Content-Type"},
            files={"file": ("contacts.csv", csv_content.encode(), "text/csv")},
        )
        resp.raise_for_status()

    # Start campaign
    start_result = await _post(f"/api/campaigns/{campaign_id}/start", {})
    return {
        "campaignId": campaign_id,
        "status": start_result.get("status", "started"),
        "contactsQueued": 1,
        "to": to_phone,
    }


@mcp.tool()
async def get_call_summary(call_log_id: str) -> dict:
    """
    Retrieve the transcript and AI analysis for a completed call.

    Args:
        call_log_id: The call log ID (returned in call events or from analytics)

    Returns:
        Dict with transcript (array of turns), analysis (sentiment, intent, summary,
        coachingInsights, goalAchieved, leadData), duration_seconds.
    """
    data = await _get(f"/api/logs/{call_log_id}")
    return {
        "id": data.get("id"),
        "agentId": data.get("agentId"),
        "callerPhone": data.get("callerPhone"),
        "durationSeconds": data.get("durationSeconds"),
        "transcript": json.loads(data["transcript"]) if isinstance(data.get("transcript"), str) else data.get("transcript", []),
        "analysis": data.get("analysis", {}),
        "startedAt": data.get("startedAt"),
    }


@mcp.tool()
async def search_knowledge_base(
    agent_id: str,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Semantic + BM25 hybrid search over an agent's knowledge base.

    Args:
        agent_id: The agent whose knowledge base to search
        query: Natural language search query (supports any language if multilingual embeddings enabled)
        top_k: Maximum number of results to return (1-20)

    Returns:
        List of matching chunks with content, source, and relevance score.
    """
    top_k = max(1, min(20, top_k))
    data = await _post("/api/rag/query", {
        "agentId": agent_id,
        "query": query,
        "topK": top_k,
        "sessionId": "mcp-search",
    })
    sources = data.get("sources", [])
    return [
        {
            "content": s.get("snippet", s.get("content", "")),
            "source": s.get("source", ""),
            "score": s.get("score", 0),
        }
        for s in sources
    ]


@mcp.tool()
async def get_analytics(
    agent_id: str,
    period: str = "7d",
) -> dict:
    """
    Get performance analytics for an agent.

    Args:
        agent_id: The agent ID
        period: Time period — "1d", "7d", "30d", "90d"

    Returns:
        Dict with totalCalls, answeredCalls, avgDuration, avgScore,
        sentimentBreakdown, topTopics, successRate.
    """
    data = await _get(f"/analytics/agents/{agent_id}", {"period": period})
    return data


@mcp.tool()
async def run_simulation(
    agent_id: str,
    scenarios: list[dict],
) -> dict:
    """
    Run automated test scenarios against an agent's full RAG pipeline.

    Args:
        agent_id: The agent to test
        scenarios: List of test cases. Each should have:
          - utterance: what the user says (required)
          - expected_intent: what the agent should address (optional)
          - expected_keywords: words that should appear in the response (optional)
          - must_not_contain: phrases the agent must NOT say (optional)
          - tags: categorisation tags (optional)

    Example scenarios:
      [
        {"utterance": "What are your hours?", "expected_keywords": ["hours", "open"]},
        {"utterance": "I want a refund", "must_not_contain": ["I don't know"]}
      ]

    Returns:
        SimulationReport with pass rate, avg score, per-scenario results, and KPIs.
    """
    data = await _post(f"/api/simulate/{agent_id}", {"scenarios": scenarios})
    return data


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
