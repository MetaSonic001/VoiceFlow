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


@mcp.tool()
async def update_agent_from_prompt(
    agent_id: str,
    revision_prompt: str,
    apply: bool = True,
) -> dict:
    """
    Revise an existing agent's configuration using a plain-language instruction.
    Only the fields that need to change are updated; manually set fields are preserved.

    Args:
        agent_id: The agent to revise
        revision_prompt: Describe what should change.
                        E.g. "make it more formal and add insurance query handling"
        apply: If True, immediately applies the changes to the agent. Default True.

    Returns:
        Dict with "delta" (changed fields) and "applied" (bool).
    """
    data = await _post("/api/agents/generate-from-prompt/revise", {
        "agent_id": agent_id,
        "revision_prompt": revision_prompt,
        "apply": apply,
    })
    return data


@mcp.tool()
async def add_knowledge_document(
    agent_id: str,
    content: str,
    title: str = "",
    source_url: str = "",
) -> dict:
    """
    Add a document to an agent's knowledge base.
    The document is chunked, embedded, and indexed for RAG automatically.

    Args:
        agent_id: The agent whose knowledge base to update
        content: The document text content (UTF-8)
        title: Optional document title
        source_url: Optional source URL for attribution

    Returns:
        {"documentId": "...", "status": "processing", "chunkCount": N}
    """
    data = await _post("/api/ingestion/ingest", {
        "agentId": agent_id,
        "content": content,
        "title": title,
        "sourceUrl": source_url,
    })
    return data


@mcp.tool()
async def get_call_coaching_report(agent_id: str) -> dict:
    """
    Get the AI Call Coach report for an agent — pending coaching cards, avg impact score,
    approved cards, and specific suggested prompt improvements.

    Args:
        agent_id: The agent to get coaching data for

    Returns:
        {"total": N, "pending": N, "approved": N, "avg_impact_score": 0.75, "cards": [...]}
    """
    data = await _get(f"/api/coaching/agents/{agent_id}/report")
    return data


@mcp.tool()
async def get_latency_stats(agent_id: str) -> dict:
    """
    Get P50/P95/P99 latency breakdown for an agent: STT, RAG, LLM, TTS, total.
    Useful for identifying bottlenecks in the conversation pipeline.

    Args:
        agent_id: The agent to query latency stats for

    Returns:
        Per-component latency percentiles with sample counts.
    """
    from app.services.latency_tracker import get_agent_latency_stats
    return get_agent_latency_stats(agent_id)


# ── MCP Resources (read-only data exposed to LLM context) ─────────────────────

@mcp.resource("voiceflow://agents")
async def resource_list_agents() -> str:
    """Resource: all agents as formatted text for LLM context injection."""
    data = await _get("/api/agents/", {"limit": "50"})
    agents = data.get("agents", [])
    if not agents:
        return "No agents configured."
    lines = [f"VoiceFlow Agents ({len(agents)} total):\n"]
    for a in agents:
        lines.append(
            f"  [{a['id']}] {a['name']} — status={a['status']} "
            f"calls={a.get('totalCalls', 0)} success={a.get('successRate', 'N/A')}%"
        )
    return "\n".join(lines)


@mcp.resource("voiceflow://analytics/overview")
async def resource_analytics_overview() -> str:
    """Resource: high-level analytics for the last 7 days."""
    try:
        data = await _get("/api/analytics/overview", {"timeRange": "7d"})
        return (
            f"VoiceFlow Analytics (7d):\n"
            f"  Total calls: {data.get('totalInteractions', 0)}\n"
            f"  Success rate: {data.get('successRate', 'N/A')}%\n"
            f"  Avg call duration: {data.get('avgResponseTime', 'N/A')}\n"
            f"  Active agents: {data.get('activeAgents', 0)}\n"
        )
    except Exception as exc:
        return f"Analytics unavailable: {exc}"


@mcp.resource("voiceflow://config")
async def resource_platform_config() -> str:
    """Resource: current platform configuration summary."""
    return (
        f"VoiceFlow MCP Configuration:\n"
        f"  API URL: {API_URL}\n"
        f"  Tenant ID: {TENANT_ID}\n"
        f"  Capabilities: STT(Whisper+Sarvam), TTS(Kokoro+Sarvam), "
        f"RAG(ChromaDB+BM25), LLM(Groq), CRM(HubSpot+Salesforce), "
        f"IVR, Recording, LiveTransfer, Simulation\n"
    )


# ── MCP Prompts (templated instructions for common workflows) ─────────────────

@mcp.prompt()
def prompt_weekly_call_summary(agent_id: str, week: str = "this week") -> str:
    """Prompt template: summarise a week's calls for an agent."""
    return (
        f"Using the VoiceFlow tools, retrieve the call analytics for agent {agent_id} "
        f"for {week}. Then get the 5 most recent call summaries for that agent. "
        f"Produce a concise plain-English weekly summary covering: "
        f"call volume trend, success rate, top caller intents, "
        f"most common failure modes, and 1-2 actionable improvement suggestions."
    )


@mcp.prompt()
def prompt_simulate_edge_cases(agent_id: str, use_case: str) -> str:
    """Prompt template: generate and run edge-case simulation for an agent."""
    return (
        f"For VoiceFlow agent {agent_id} (use case: {use_case}), "
        f"generate 10 adversarial test scenarios using the run_simulation tool. "
        f"Focus on: injection attempts, callers who give incomplete information, "
        f"callers who switch language mid-conversation, and emotionally frustrated callers. "
        f"Run the simulation, report pass rates, and suggest 3 specific prompt improvements "
        f"for any failures."
    )


@mcp.prompt()
def prompt_onboard_new_agent(business_description: str) -> str:
    """Prompt template: full agent onboarding from scratch."""
    return (
        f"Create a complete AI voice agent for: {business_description}\n\n"
        f"Steps:\n"
        f"1. Use create_agent to create the agent config from the description above\n"
        f"2. Use generate FAQs (generate-from-prompt/faqs) to get starter knowledge\n"
        f"3. Add each FAQ as a knowledge document using add_knowledge_document\n"
        f"4. Generate and run a simulation suite using run_simulation\n"
        f"5. Report the agent ID, simulation results, and any issues to address before going live"
    )


@mcp.prompt()
def prompt_improve_agent(agent_id: str, problem_description: str) -> str:
    """Prompt template: diagnose and fix a specific agent problem."""
    return (
        f"VoiceFlow agent {agent_id} has this reported problem: {problem_description}\n\n"
        f"Diagnose and fix it:\n"
        f"1. Get the agent's coaching report using get_call_coaching_report\n"
        f"2. Search the knowledge base for relevant content on the problem topic\n"
        f"3. Review the latest call analytics\n"
        f"4. Apply a targeted fix using update_agent_from_prompt — describe only what to change\n"
        f"5. Run a focused simulation to verify the fix addresses the problem\n"
        f"6. Confirm the gate passed and report what was changed"
    )


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()

