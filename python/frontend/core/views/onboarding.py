from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.api_client import get_client
import logging

logger = logging.getLogger(__name__)


@login_required
def flow(request):
    """7-step onboarding wizard."""
    client = get_client(request)
    templates = []
    try:
        data = client.get_agent_templates()
        templates = data.get("templates", [])
    except Exception:
        templates = []
    return render(request, "onboarding/flow.html", {
        "templates": templates,
    })
