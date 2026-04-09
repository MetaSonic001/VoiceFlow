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
    client = get_client(request)
    logs = []
    try:
        data = client.get_call_logs(page=int(request.GET.get("page", 1)))
        logs = data.get("logs", data.get("callLogs", []))
    except Exception:
        pass
    return render(request, "dashboard/calls.html", {"logs": logs})


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
    metrics = {}
    try:
        metrics = client.get_system_metrics()
    except Exception:
        pass
    return render(request, "dashboard/system.html", {"metrics": metrics})


@login_required
def users(request):
    client = get_client(request)
    users_list = []
    try:
        users_list = client.get_users().get("users", [])
    except Exception:
        pass
    return render(request, "dashboard/users.html", {"users_list": users_list})


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
    return render(request, "dashboard/api_docs.html")


@login_required
def notifications(request):
    return render(request, "dashboard/notifications.html")


@login_required
def audit(request):
    return render(request, "dashboard/audit.html")


@login_required
def backup(request):
    return render(request, "dashboard/backup.html")


@login_required
def reports(request):
    return render(request, "dashboard/reports.html")


@login_required
def integrations(request):
    return render(request, "dashboard/integrations.html")


@login_required
def pipelines(request):
    client = get_client(request)
    pipeline_list = []
    try:
        pipeline_list = client.list_pipelines().get("pipelines", [])
    except Exception:
        pass
    return render(request, "dashboard/pipelines.html", {"pipelines": pipeline_list})
