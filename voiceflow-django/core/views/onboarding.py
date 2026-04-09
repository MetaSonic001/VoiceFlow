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
        templates = [
            {"id": "customer-support", "name": "Customer Support", "description": "Handle customer inquiries and resolve issues", "persona": "You are a helpful and professional customer support agent."},
            {"id": "cold-calling", "name": "Cold Calling", "description": "Outbound sales and lead generation", "persona": "You are a persuasive and friendly sales agent."},
            {"id": "appointment-booking", "name": "Appointment Booking", "description": "Schedule and manage appointments", "persona": "You are an efficient appointment scheduling assistant."},
            {"id": "lead-qualification", "name": "Lead Qualification", "description": "Qualify and score inbound leads", "persona": "You are a knowledgeable lead qualification specialist."},
            {"id": "hr-helpdesk", "name": "HR Helpdesk", "description": "Answer HR and employee queries", "persona": "You are a helpful HR assistant."},
            {"id": "sales-followup", "name": "Sales Follow-up", "description": "Follow up with prospects after initial contact", "persona": "You are a persistent and courteous sales follow-up agent."},
        ]
    return render(request, "onboarding/flow.html", {
        "templates": templates,
    })
