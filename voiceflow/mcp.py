"""
voiceflow.mcp — expose a VoiceAgent's tools as an MCP server.

Usage:
    from voiceflow import VoiceAgent
    from voiceflow.mcp import build_mcp_server

    agent = VoiceAgent(name="Support Bot", ...)
    mcp = build_mcp_server(agent)   # returns a FastMCP instance

    if __name__ == "__main__":
        mcp.run()                   # stdio transport (Claude Desktop)
        # or: mcp.run(transport="streamable-http", port=8080)
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from voiceflow.agent import VoiceAgent

logger = logging.getLogger("voiceflow.mcp")


def build_mcp_server(agent: "VoiceAgent", name: str | None = None):
    """
    Build a FastMCP server that exposes all registered @voice_tool functions
    from the given VoiceAgent.  Returns the FastMCP instance — call .run() to start.
    """
    try:
        from fastmcp import FastMCP
    except ImportError:
        raise ImportError("fastmcp is required: pip install fastmcp")

    from voiceflow.tools import execute_tool

    server_name = name or f"{agent.name} MCP Server"
    mcp = FastMCP(server_name)

    registered = 0
    for fn_name, fn in agent._tools.items():
        schema = fn._voice_tool_schema  # set by @voice_tool decorator

        # Build a dynamic async wrapper that MCP can call
        def _make_handler(func, fn_schema):
            params = fn_schema.get("parameters", {}).get("properties", {})
            required = fn_schema.get("parameters", {}).get("required", [])

            async def _handler(**kwargs: Any) -> str:
                try:
                    result = await execute_tool(func, kwargs)
                    return str(result)
                except Exception as exc:
                    logger.error("[MCP tool %s] error: %s", func.__name__, exc)
                    return f"Error: {exc}"

            _handler.__name__ = fn_name
            _handler.__doc__ = fn_schema.get("description", "")
            return _handler

        handler = _make_handler(fn, schema)
        mcp.tool(name=fn_name, description=schema.get("description", ""))(handler)
        registered += 1

    # -- MCP Resource: agent info
    @mcp.resource("voiceflow://agent/info")
    def agent_info() -> str:
        return (
            f"Agent: {agent.name}\n"
            f"System Prompt: {agent.system_prompt[:500]}...\n"
            f"Tools: {list(agent._tools.keys())}\n"
        )

    # -- MCP Prompt: improve agent
    @mcp.prompt("improve_agent_prompt")
    def improve_prompt() -> str:
        return (
            f"Here is the current system prompt for the voice agent '{agent.name}':\n\n"
            f"{agent.system_prompt}\n\n"
            "Please suggest 3 concrete improvements to make this agent:\n"
            "1. More empathetic and natural-sounding\n"
            "2. Better at handling objections\n"
            "3. More concise (reduce speech latency)\n"
        )

    logger.info("[voiceflow.mcp] registered %d tools on MCP server '%s'", registered, server_name)
    return mcp
