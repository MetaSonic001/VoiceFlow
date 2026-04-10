from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.api_client import get_client
import logging

logger = logging.getLogger(__name__)


@login_required
def index(request):
    """Main dashboard — agent list + metrics."""
    client = get_client(request)
    agents = []
    metrics = {}
    try:
        data = client.get_agents(page=1, limit=50)
        agents = data.get("agents", [])
    except Exception as e:
        logger.warning("Failed to fetch agents: %s", e)
    try:
        metrics = client.get_analytics_overview(time_range="7d")
    except Exception:
        pass
    return render(request, "dashboard/index.html", {
        "agents": agents,
        "metrics": metrics,
    })


@login_required
def agent_detail(request, agent_id):
    """Agent detail / settings page."""
    client = get_client(request)
    agent = {}
    models_list = []
    try:
        agent = client.get_agent(agent_id)
    except Exception as e:
        logger.warning("Failed to fetch agent %s: %s", agent_id, e)
    try:
        data = client.get_groq_models()
        models_list = data.get("models", [])
    except Exception:
        models_list = [
            {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B Versatile"},
            {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B Instant"},
        ]
    import json
    return render(request, "agents/detail.html", {
        "agent": agent,
        "agent_json": json.dumps(agent, default=str),
        "models_list": models_list,
    })
