"""All secondary dashboard page views."""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.api_client import get_client
import logging

logger = logging.getLogger(__name__)


@login_required
def analytics(request):
    client = get_client(request)
    overview = {}
    agents = []
    try:
        overview = client.get_analytics_overview(time_range=request.GET.get("range", "7d"))
    except Exception:
        pass
    try:
        agents = client.get_agents(limit=50).get("agents", [])
    except Exception:
        pass
    return render(request, "dashboard/analytics.html", {"overview": overview, "agents": agents})


@login_required
def calls(request):
    import json
    client = get_client(request)
    logs = []
    try:
        data = client.get_call_logs(page=int(request.GET.get("page", 1)))
        logs = data.get("logs", data.get("callLogs", []))
    except Exception:
        pass
    return render(request, "dashboard/calls.html", {"logs": json.dumps(logs)})


@login_required
def knowledge(request):
    client = get_client(request)
    documents = []
    company_profile = {}
    chunks = []
    try:
        documents = client.get_knowledge_base().get("documents", [])
    except Exception:
        pass
    try:
        company_profile = client.get_company_profile()
    except Exception:
        pass
    try:
        chunks = client.get_company_knowledge().get("chunks", [])
    except Exception:
        pass
    return render(request, "dashboard/knowledge.html", {
        "documents": documents, "company_profile": company_profile, "chunks": chunks,
    })


@login_required
def settings_page(request):
    client = get_client(request)
    settings_data = {}
    twilio_status = {}
    groq_status = {}
    try:
        settings_data = client.get_settings()
    except Exception:
        pass
    try:
        twilio_status = client.get_twilio_credential_status()
    except Exception:
        pass
    try:
        groq_status = client.get_groq_key_status()
    except Exception:
        pass
    return render(request, "dashboard/settings.html", {
        "settings_data": settings_data, "twilio_status": twilio_status, "groq_status": groq_status,
    })


@login_required
def billing(request):
    client = get_client(request)
    usage = {}
    try:
        usage = client.get_usage_stats()
    except Exception:
        pass
    return render(request, "dashboard/billing.html", {"usage": usage})


@login_required
def system(request):
    client = get_client(request)
    health = {}
    try:
        health = client.get_system_health()
    except Exception:
        pass
    return render(request, "dashboard/system.html", {"health": health})


@login_required
def users(request):
    import json
    client = get_client(request)
    users_list = []
    try:
        users_list = client.get_users().get("users", [])
    except Exception:
        pass
    return render(request, "dashboard/users.html", {"users_list": json.dumps(users_list)})


@login_required
def retraining(request):
    client = get_client(request)
    examples = []
    stats = {}
    try:
        examples = client.get_retraining_examples().get("examples", [])
    except Exception:
        pass
    try:
        stats = client.get_retraining_stats()
    except Exception:
        pass
    return render(request, "dashboard/retraining.html", {"examples": examples, "stats": stats})


@login_required
def widget(request):
    client = get_client(request)
    agents = []
    try:
        agents = client.get_agents(limit=50).get("agents", [])
    except Exception:
        pass
    return render(request, "dashboard/widget.html", {"agents": agents})


@login_required
def api_docs(request):
    from django.conf import settings as django_settings
    backend_url = django_settings.BACKEND_API_URL.rstrip("/")
    return render(request, "dashboard/api_docs.html", {"swagger_url": f"{backend_url}/docs"})


@login_required
def notifications(request):
    client = get_client(request)
    notif_data = {}
    try:
        notif_data = client.get_notifications()
    except Exception:
        pass
    return render(request, "dashboard/notifications.html", {
        "notifications": notif_data.get("notifications", []),
        "unread_count": notif_data.get("unreadCount", 0),
    })


@login_required
def audit(request):
    import json as _json
    client = get_client(request)
    audit_data = {}
    try:
        audit_data = client.get_audit_logs(limit=200)
    except Exception:
        pass
    logs = audit_data.get("logs", [])
    return render(request, "dashboard/audit.html", {
        "logs": logs,
        "logs_json": _json.dumps(logs, default=str),
        "total": audit_data.get("total", 0),
    })


@login_required
def backup(request):
    return render(request, "dashboard/backup.html")


@login_required
def reports(request):
    import json
    client = get_client(request)
    pipeline_list = []
    try:
        pipeline_list = client.get_reports().get("pipelines", [])
    except Exception:
        pass
    return render(request, "dashboard/reports.html", {"reports": json.dumps(pipeline_list)})


@login_required
def integrations(request):
    client = get_client(request)
    integrations_list = []
    # Build integration status from real credential checks
    try:
        twilio_status = client.get_twilio_credential_status()
        twilio_connected = twilio_status.get("configured", False)
    except Exception:
        twilio_connected = False
    try:
        groq_status = client.get_groq_key_status()
        groq_connected = groq_status.get("configured", False)
    except Exception:
        groq_connected = False

    integrations_list = [
        {"name": "Twilio", "description": "Phone calls, SMS, and WhatsApp messaging.", "color": "green",
         "status": "connected" if twilio_connected else "Not connected"},
        {"name": "Groq", "description": "LLM inference for agent conversations.", "color": "blue",
         "status": "connected" if groq_connected else "Not connected"},
        {"name": "Slack", "description": "Team notifications and alerts.", "color": "purple",
         "status": "Not connected", "coming_soon": True},
        {"name": "WhatsApp", "description": "WhatsApp Business messaging channel.", "color": "green",
         "status": "Not connected", "coming_soon": True},
    ]
    return render(request, "dashboard/integrations.html", {"integrations": integrations_list})


@login_required
def pipelines(request):
    import json
    client = get_client(request)
    pipeline_list = []
    try:
        pipeline_list = client.list_pipelines().get("pipelines", [])
    except Exception:
        pass
    return render(request, "dashboard/pipelines.html", {"pipelines": json.dumps(pipeline_list)})


@login_required
def data_explorer(request):
    return render(request, "dashboard/data_explorer.html")


@login_required
def brands(request):
    import json
    client = get_client(request)
    brands_list = []
    try:
        result = client.get_brands()
        brands_list = result if isinstance(result, list) else result.get("brands", [])
    except Exception:
        pass
    return render(request, "dashboard/brands.html", {"brands": json.dumps(brands_list)})


@login_required
def campaigns(request):
    """Campaigns page — campaign cards with HTMX live stats."""
    return render(request, "dashboard/campaigns.html")


@login_required
def webhooks(request):
    """Webhook endpoints management page."""
    return render(request, "dashboard/webhooks.html")


@login_required
def agent_builder(request):
    """Visual flow builder for an agent."""
    agent_id = request.GET.get("agent_id", "")
    return render(request, "agents/builder.html", {"agent_id": agent_id})
