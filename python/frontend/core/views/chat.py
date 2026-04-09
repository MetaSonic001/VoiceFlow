from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.api_client import get_client
import logging

logger = logging.getLogger(__name__)


@login_required
def agent_chat(request, agent_id):
    """Chat / talk with an agent (text + voice)."""
    client = get_client(request)
    agent = {}
    try:
        agent = client.get_agent(agent_id)
    except Exception as e:
        logger.warning("Failed to fetch agent %s: %s", agent_id, e)
    return render(request, "agents/chat.html", {"agent": agent})


@login_required
def voice_agent(request):
    """Dedicated voice agent page (Gemini-live style)."""
    client = get_client(request)
    agents = []
    try:
        data = client.get_agents(page=1, limit=50)
        agents = data.get("agents", [])
    except Exception:
        pass
    return render(request, "dashboard/voice_agent.html", {"agents": agents})
