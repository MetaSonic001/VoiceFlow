"""
Proxy endpoints for browser JS / HTMX to talk to the FastAPI backend.
Every endpoint requires login and injects tenant headers automatically.
"""
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from core.api_client import get_client
import logging

logger = logging.getLogger(__name__)


def _json_body(request):
    try:
        return json.loads(request.body)
    except Exception:
        return {}


# ── Agents ─────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET", "POST"])
def agents_list(request):
    client = get_client(request)
    if request.method == "POST":
        data = _json_body(request)
        try:
            result = client.create_agent(data)
            return JsonResponse(result, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    try:
        result = client.get_agents(
            page=int(request.GET.get("page", 1)),
            limit=int(request.GET.get("limit", 20)),
        )
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def agent_detail_api(request, agent_id):
    client = get_client(request)
    try:
        if request.method == "PUT":
            return JsonResponse(client.update_agent(agent_id, _json_body(request)))
        if request.method == "DELETE":
            client.delete_agent(agent_id)
            return JsonResponse({"ok": True})
        return JsonResponse(client.get_agent(agent_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def agent_activate(request, agent_id):
    try:
        return JsonResponse(get_client(request).activate_agent(agent_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def agent_pause(request, agent_id):
    try:
        return JsonResponse(get_client(request).pause_agent(agent_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def agent_deploy(request, agent_id):
    try:
        return JsonResponse(get_client(request).deploy_agent(agent_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── Chat / Audio / TTS ─────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def chat_send(request):
    data = _json_body(request)
    try:
        result = get_client(request).chat(
            agent_id=data.get("agentId", ""),
            message=data.get("message", ""),
            session_id=data.get("sessionId", ""),
        )
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def audio_send(request):
    audio = request.FILES.get("audio")
    if not audio:
        return JsonResponse({"error": "No audio file"}, status=400)
    try:
        result = get_client(request).send_audio(
            agent_id=request.POST.get("agentId", ""),
            session_id=request.POST.get("sessionId", ""),
            audio_bytes=audio.read(),
            filename=audio.name,
        )
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def tts_synthesize(request):
    data = _json_body(request)
    try:
        result = get_client(request).synthesize_tts(
            text=data.get("text", ""), voice_id=data.get("voiceId", ""),
        )
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def tts_preview(request):
    data = _json_body(request)
    try:
        result = get_client(request).preview_voice(voice_id=data.get("voiceId", "preset-aria"))
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def voice_presets(request):
    try:
        return JsonResponse(get_client(request).get_preset_voices())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def voice_token(request):
    """Generate a short-lived JWT for the WebSocket voice live endpoint."""
    import jwt as pyjwt
    from datetime import datetime, timezone, timedelta
    from django.conf import settings as django_settings

    tenant_id = getattr(request, "tenant_id", "")
    user_id = str(request.user.id) if request.user.is_authenticated else ""

    # Use the same JWT secret the backend uses
    jwt_secret = getattr(django_settings, "BACKEND_JWT_SECRET", "dev-secret")
    payload = {
        "userId": user_id,
        "tenantId": tenant_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token = pyjwt.encode(payload, jwt_secret, algorithm="HS256")
    return JsonResponse({"token": token})


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def voice_clone(request):
    audio = request.FILES.get("audio")
    if not audio:
        return JsonResponse({"error": "No audio file"}, status=400)
    try:
        result = get_client(request).clone_voice(audio.read(), audio.name)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def voice_clone_preview(request):
    data = _json_body(request)
    try:
        result = get_client(request).clone_preview(data.get("cloneId", ""), data.get("text", ""))
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ── Onboarding ─────────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def onboarding_company(request):
    try:
        return JsonResponse(get_client(request).save_company_profile(_json_body(request)))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def onboarding_knowledge(request):
    try:
        return JsonResponse(get_client(request).upload_knowledge(**_json_body(request)))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def onboarding_agent_config(request):
    try:
        return JsonResponse(get_client(request).save_agent_config(_json_body(request)))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── Knowledge ──────────────────────────────────────────────────────────

@login_required
def knowledge_list(request):
    try:
        return JsonResponse(get_client(request).get_knowledge_base())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def company_profile(request):
    try:
        return JsonResponse(get_client(request).get_company_profile())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def company_knowledge(request):
    try:
        return JsonResponse(get_client(request).get_company_knowledge())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def document_upload(request):
    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"error": "No file"}, status=400)
    agent_id = request.POST.get("agentId", "")
    try:
        result = get_client(request).upload_document((f.name, f.read(), f.content_type), agent_id=agent_id)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def document_ingest_url(request):
    data = _json_body(request)
    try:
        return JsonResponse(get_client(request).trigger_url_ingestion(data.get("url", "")))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["DELETE"])
def document_delete(request, doc_id):
    try:
        get_client(request).delete_document(doc_id)
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── Knowledge Base (per-agent, with when_to_use) ───────────────────────

@login_required
@require_http_methods(["GET"])
def kb_list(request, agent_id):
    """List all KB attachments for an agent with document details."""
    try:
        return JsonResponse(get_client(request).kb_list(agent_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def kb_ingest_file(request):
    """Upload a file and attach it to an agent's KB."""
    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"error": "No file provided"}, status=400)
    agent_id    = request.POST.get("agentId", "")
    when_to_use = request.POST.get("whenToUse", "")
    try:
        result = get_client(request).kb_ingest_file(f.read(), f.name, agent_id, when_to_use)
        return JsonResponse(result, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def kb_ingest_url(request):
    """Scrape a URL and attach it to an agent's KB."""
    data        = _json_body(request)
    agent_id    = data.get("agentId", "")
    url         = data.get("url", "")
    when_to_use = data.get("whenToUse", "")
    try:
        result = get_client(request).kb_ingest_url(agent_id, url, when_to_use)
        return JsonResponse(result, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def kb_ingest_text(request):
    """Ingest pasted text and attach it to an agent's KB."""
    data        = _json_body(request)
    agent_id    = data.get("agentId", "")
    text        = data.get("text", "")
    title       = data.get("title", "")
    when_to_use = data.get("whenToUse", "")
    try:
        result = get_client(request).kb_ingest_text(agent_id, text, title, when_to_use)
        return JsonResponse(result, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def kb_attach(request):
    """Attach an existing document to an agent's KB."""
    try:
        return JsonResponse(get_client(request).kb_attach(_json_body(request)), status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["PATCH", "DELETE"])
def kb_update_attachment(request, att_id):
    """Update when_to_use (PATCH) or detach (DELETE) a KB attachment."""
    try:
        if request.method == "DELETE":
            return JsonResponse(get_client(request).kb_delete_attachment(att_id))
        return JsonResponse(get_client(request).kb_update_attachment(att_id, _json_body(request)))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def kb_test_query(request):
    """Run a test query through the full RAG pipeline and return debug info."""
    data     = _json_body(request)
    agent_id = data.get("agentId", "")
    query    = data.get("query", "")
    try:
        return JsonResponse(get_client(request).kb_test_query(agent_id, query))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@login_required
@require_http_methods(["GET", "PUT"])
def settings_api(request):
    client = get_client(request)
    try:
        if request.method == "PUT":
            return JsonResponse(client.update_settings(_json_body(request)))
        return JsonResponse(client.get_settings())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST", "DELETE"])
def twilio_credentials(request):
    client = get_client(request)
    try:
        if request.method == "DELETE":
            client.delete_twilio_credentials()
            return JsonResponse({"ok": True})
        return JsonResponse(client.save_twilio_credentials(_json_body(request)))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST", "DELETE"])
def groq_api_key(request):
    client = get_client(request)
    try:
        if request.method == "DELETE":
            client.delete_groq_api_key()
            return JsonResponse({"ok": True})
        return JsonResponse(client.save_groq_api_key(_json_body(request)))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def all_key_statuses(request):
    try:
        return JsonResponse(get_client(request).get_all_key_statuses())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def _byok_provider_view(save_fn_name: str, delete_fn_name: str):
    """Return a view function for a generic BYOK provider."""
    @login_required
    @require_http_methods(["POST", "DELETE"])
    def _view(request):
        client = get_client(request)
        try:
            if request.method == "DELETE":
                getattr(client, delete_fn_name)()
                return JsonResponse({"ok": True})
            return JsonResponse(getattr(client, save_fn_name)(_json_body(request)))
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return _view


openai_api_key    = _byok_provider_view("save_openai_api_key",    "delete_openai_api_key")
anthropic_api_key = _byok_provider_view("save_anthropic_api_key", "delete_anthropic_api_key")
gemini_api_key    = _byok_provider_view("save_gemini_api_key",    "delete_gemini_api_key")
elevenlabs_api_key = _byok_provider_view("save_elevenlabs_api_key", "delete_elevenlabs_api_key")
sarvam_api_key    = _byok_provider_view("save_sarvam_api_key",    "delete_sarvam_api_key")
deepgram_api_key  = _byok_provider_view("save_deepgram_api_key",  "delete_deepgram_api_key")
assemblyai_api_key = _byok_provider_view("save_assemblyai_api_key", "delete_assemblyai_api_key")
truecaller_api_key = _byok_provider_view("save_truecaller_api_key", "delete_truecaller_api_key")


# ── Analytics / Call Logs / Retraining / System / Users / Billing ──────

@login_required
def analytics_overview(request):
    try:
        return JsonResponse(get_client(request).get_analytics_overview(
            time_range=request.GET.get("timeRange", request.GET.get("range", "7d")),
            agent_id=request.GET.get("agentId", ""),
        ))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def analytics_resolution_stats(request):
    try:
        return JsonResponse(get_client(request)._get(
            "/analytics/resolution-stats",
            params={"timeRange": request.GET.get("timeRange", "7d"), "agentId": request.GET.get("agentId", "")},
        ))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def analytics_top_intents(request):
    try:
        return JsonResponse(get_client(request)._get(
            "/analytics/top-intents",
            params={"timeRange": request.GET.get("timeRange", "7d"), "limit": request.GET.get("limit", "10"), "agentId": request.GET.get("agentId", "")},
        ))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def analytics_failure_modes(request):
    try:
        return JsonResponse(get_client(request)._get(
            "/analytics/failure-modes",
            params={"timeRange": request.GET.get("timeRange", "7d"), "agentId": request.GET.get("agentId", "")},
        ))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def analytics_cost_estimate(request):
    try:
        return JsonResponse(get_client(request)._get(
            "/analytics/cost-estimate",
            params={"timeRange": request.GET.get("timeRange", "7d"), "agentId": request.GET.get("agentId", "")},
        ))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def analytics_sentiment_trend(request):
    try:
        return JsonResponse(get_client(request)._get(
            "/analytics/sentiment-trend",
            params={"timeRange": request.GET.get("timeRange", "7d"), "agentId": request.GET.get("agentId", "")},
        ))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def analytics_handle_time(request):
    try:
        return JsonResponse(get_client(request)._get(
            "/analytics/handle-time-histogram",
            params={"timeRange": request.GET.get("timeRange", "7d"), "agentId": request.GET.get("agentId", "")},
        ))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def analytics_campaign_roi(request):
    try:
        return JsonResponse(get_client(request)._get(
            "/analytics/campaign-roi",
            params={"timeRange": request.GET.get("timeRange", "30d")},
        ))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def analytics_export_csv(request):
    import requests as req_lib
    try:
        client = get_client(request)
        params = {"timeRange": request.GET.get("timeRange", "7d")}
        if request.GET.get("agentId"):
            params["agentId"] = request.GET["agentId"]
        resp = req_lib.get(
            client._url("/analytics/export.csv"),
            headers=client._headers(),
            params=params,
            timeout=30,
        )
        from django.http import HttpResponse
        return HttpResponse(
            resp.content,
            content_type="text/csv",
            headers={"Content-Disposition": resp.headers.get("Content-Disposition", "attachment; filename=calls.csv")},
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def call_logs_api(request):
    try:
        return JsonResponse(get_client(request).get_call_logs(
            page=int(request.GET.get("page", 1)),
            agent_id=request.GET.get("agentId", ""),
            search=request.GET.get("search", ""),
        ))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
def retraining_api(request):
    client = get_client(request)
    try:
        if request.method == "POST":
            return JsonResponse(client.update_retraining_example(
                _json_body(request).get("id", ""), _json_body(request),
            ))
        return JsonResponse(client.get_retraining_examples(
            page=int(request.GET.get("page", 1)),
            status=request.GET.get("status", ""),
        ))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def retraining_trigger(request):
    try:
        return JsonResponse(get_client(request).trigger_retraining_pipeline())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def system_metrics(request):
    try:
        return JsonResponse(get_client(request).get_system_metrics())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def users_api(request):
    client = get_client(request)
    try:
        if request.method == "POST":
            return JsonResponse(client.create_backend_user(_json_body(request)), status=201)
        return JsonResponse(client.get_users())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def billing_usage(request):
    try:
        return JsonResponse(get_client(request).get_usage_stats())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def billing_calculator(request):
    """Proxy the no-auth billing calculator to FastAPI. Auth not required (public pricing page)."""
    from django.conf import settings as dj_settings
    import httpx as _httpx
    fastapi_url = getattr(dj_settings, "FASTAPI_URL", "http://localhost:8040")
    params = {
        "calls_per_day": request.GET.get("calls_per_day", "50"),
        "avg_duration_seconds": request.GET.get("avg_duration_seconds", "120"),
        "plan_type": request.GET.get("plan_type", "mcp"),
        "days_per_month": request.GET.get("days_per_month", "26"),
    }
    try:
        with _httpx.Client(timeout=10) as client:
            resp = client.get(f"{fastapi_url}/api/billing/calculator", params=params)
        return JsonResponse(resp.json(), status=resp.status_code)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def pipelines_api(request):
    client = get_client(request)
    try:
        if request.method == "POST":
            return JsonResponse(client.create_pipeline(_json_body(request)), status=201)
        return JsonResponse(client.list_pipelines())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def pipeline_trigger(request):
    client = get_client(request)
    try:
        data = _json_body(request)
        return JsonResponse(client.trigger_pipeline(data.get("pipeline_id", "")))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def reports_api(request):
    client = get_client(request)
    try:
        if request.method == "POST":
            return JsonResponse(client.generate_report(_json_body(request)))
        return JsonResponse(client.get_reports())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ── Notifications ──────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def notifications_api(request):
    client = get_client(request)
    try:
        return JsonResponse(client.get_notifications())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def notification_read(request, notif_id):
    client = get_client(request)
    try:
        return JsonResponse(client.mark_notification_read(notif_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def notifications_read_all(request):
    client = get_client(request)
    try:
        return JsonResponse(client.mark_all_notifications_read())
    except AttributeError:
        # Fallback: direct call
        return JsonResponse(client._post("/api/notifications/read-all"))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── System Health ──────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def system_health(request):
    client = get_client(request)
    try:
        return JsonResponse(client.get_system_health())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def system_health_check(request):
    """Alias endpoint for system page JS refresh."""
    return system_health(request)


# ── Call log flag ──────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def call_log_flag(request, log_id):
    client = get_client(request)
    try:
        return JsonResponse(client.flag_for_retraining(log_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── Retraining example update ─────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def retraining_update(request, example_id):
    client = get_client(request)
    try:
        return JsonResponse(client.update_retraining_example(example_id, _json_body(request)))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── User management ───────────────────────────────────────────────────

@login_required
@require_http_methods(["PUT", "DELETE"])
def user_detail_api(request, user_id):
    client = get_client(request)
    try:
        if request.method == "DELETE":
            client.delete_backend_user(user_id)
            return JsonResponse({"ok": True})
        return JsonResponse(client.update_backend_user(user_id, _json_body(request)))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── Data Explorer ──────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def data_explorer_overview(request):
    try:
        return JsonResponse(get_client(request).get_data_overview())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def data_explorer_postgres(request):
    try:
        return JsonResponse(get_client(request).get_data_postgres())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def data_explorer_chromadb(request):
    try:
        return JsonResponse(get_client(request).get_data_chromadb())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def data_explorer_redis(request):
    try:
        return JsonResponse(get_client(request).get_data_redis())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ── Audit ──────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def audit_api(request):
    try:
        limit = int(request.GET.get("limit", 50))
        offset = int(request.GET.get("offset", 0))
        return JsonResponse(get_client(request).get_audit_logs(limit=limit, offset=offset))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ── Brands ─────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET", "POST"])
def brands_api(request):
    client = get_client(request)
    try:
        if request.method == "POST":
            result = client.create_brand(_json_body(request))
            return JsonResponse(result, status=201)
        brands = client.get_brands()
        return JsonResponse({"brands": brands} if isinstance(brands, list) else brands)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def brand_detail_api(request, brand_id):
    client = get_client(request)
    try:
        if request.method == "PUT":
            return JsonResponse(client.update_brand(brand_id, _json_body(request)))
        if request.method == "DELETE":
            client.delete_brand(brand_id)
            return JsonResponse({"ok": True})
        return JsonResponse(client.get_brand(brand_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── Campaigns ──────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET", "POST"])
def campaigns_api(request):
    client = get_client(request)
    try:
        if request.method == "POST":
            return JsonResponse(client._post("/api/campaigns/", json=_json_body(request)), status=201)
        return JsonResponse(client._get("/api/campaigns/"))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET", "DELETE"])
def campaign_detail_api(request, campaign_id):
    client = get_client(request)
    try:
        if request.method == "DELETE":
            client._delete(f"/api/campaigns/{campaign_id}")
            return JsonResponse({"ok": True})
        return JsonResponse(client._get(f"/api/campaigns/{campaign_id}"))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def campaign_upload_contacts(request, campaign_id):
    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"error": "No CSV file"}, status=400)
    client = get_client(request)
    try:
        result = client._post(
            f"/api/campaigns/{campaign_id}/contacts/upload",
            files={"file": (f.name, f.read(), "text/csv")},
        )
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def campaign_start(request, campaign_id):
    try:
        return JsonResponse(get_client(request)._post(f"/api/campaigns/{campaign_id}/start"))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def campaign_pause(request, campaign_id):
    try:
        return JsonResponse(get_client(request)._post(f"/api/campaigns/{campaign_id}/pause"))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def campaign_stats(request, campaign_id):
    try:
        return JsonResponse(get_client(request)._get(f"/api/campaigns/{campaign_id}/stats"))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ── Webhooks ───────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET", "POST"])
def webhooks_api(request):
    client = get_client(request)
    try:
        if request.method == "POST":
            return JsonResponse(client._post("/api/webhooks/", json=_json_body(request)), status=201)
        return JsonResponse(client._get("/api/webhooks/"))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def webhook_detail_api(request, webhook_id):
    try:
        get_client(request)._delete(f"/api/webhooks/{webhook_id}")
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── A/B Testing ────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def ab_variants_api(request):
    try:
        return JsonResponse(get_client(request)._get("/api/ab-testing/variants"))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def ab_create_variant(request, agent_id):
    try:
        data = _json_body(request)
        return JsonResponse(
            get_client(request)._post(f"/api/ab-testing/{agent_id}/variant", json=data),
            status=201,
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def ab_results(request, test_id):
    try:
        return JsonResponse(get_client(request)._get(f"/api/ab-testing/{test_id}/results"))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ── DND Registry ──────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET", "POST"])
def dnd_api(request):
    client = get_client(request)
    try:
        if request.method == "POST":
            return JsonResponse(client._post("/api/dnd/", json=_json_body(request)), status=201)
        return JsonResponse(client._get("/api/dnd/"))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def dnd_delete(request, number_id):
    try:
        get_client(request)._delete(f"/api/dnd/{number_id}")
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def dnd_bulk(request):
    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"error": "No file"}, status=400)
    client = get_client(request)
    try:
        result = client._post(
            "/api/dnd/bulk",
            files={"file": (f.name, f.read(), "text/csv")},
        )
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── IVR Trees ─────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET", "POST"])
def ivr_list(request):
    client = get_client(request)
    try:
        if request.method == "POST":
            return JsonResponse(client.create_ivr_tree(_json_body(request)), status=201)
        return JsonResponse(client.list_ivr_trees())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def ivr_detail(request, tree_id):
    client = get_client(request)
    try:
        if request.method == "PUT":
            return JsonResponse(client.update_ivr_tree(tree_id, _json_body(request)))
        if request.method == "DELETE":
            client.delete_ivr_tree(tree_id)
            return JsonResponse({"ok": True})
        return JsonResponse(client.get_ivr_tree(tree_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── Call Recordings ───────────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def recordings_list(request):
    client = get_client(request)
    try:
        return JsonResponse(client.list_recordings(
            page=int(request.GET.get("page", 1)),
            limit=int(request.GET.get("limit", 20)),
            agent_id=request.GET.get("agent_id", ""),
            search=request.GET.get("search", ""),
        ))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET", "DELETE"])
def recording_detail(request, recording_id):
    client = get_client(request)
    try:
        if request.method == "DELETE":
            client.delete_recording(recording_id)
            return JsonResponse({"ok": True})
        return JsonResponse(client.get_recording(recording_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def recording_download(request, recording_id):
    try:
        return JsonResponse(get_client(request).get_recording_download_url(recording_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── Contacts (OmniCRM) ────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def contacts_import_csv(request):
    """Upload CSV to bulk-import/upsert contacts."""
    try:
        import requests as _req
        from django.conf import settings as _settings
        client = get_client(request)
        files = {"file": (request.FILES["file"].name, request.FILES["file"].read(), "text/csv")}
        # Strip Content-Type so requests can set multipart boundary correctly
        headers = {k: v for k, v in client._headers.items() if k.lower() != "content-type"}
        r = _req.post(
            f"{_settings.BACKEND_API_URL}/api/contacts/import/",
            files=files,
            headers=headers,
            timeout=60,
        )
        return JsonResponse(r.json(), status=r.status_code)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def contacts_list(request):
    client = get_client(request)
    try:
        if request.method == "POST":
            return JsonResponse(client.create_contact(_json_body(request)), status=201)
        return JsonResponse(client.list_contacts(
            page=int(request.GET.get("page", 1)),
            limit=int(request.GET.get("limit", 25)),
            search=request.GET.get("search", ""),
            intent_level=request.GET.get("intent_level", ""),
        ))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def contact_detail(request, contact_id):
    client = get_client(request)
    try:
        if request.method == "PUT":
            return JsonResponse(client.update_contact(contact_id, _json_body(request)))
        if request.method == "DELETE":
            client.delete_contact(contact_id)
            return JsonResponse({"ok": True})
        return JsonResponse(client.get_contact(contact_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def contact_note(request, contact_id):
    try:
        data = _json_body(request)
        return JsonResponse(get_client(request).add_contact_note(contact_id, data.get("note", "")))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── Coaching Cards ────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def coaching_from_recording(request):
    """Create a coaching card (bad) or few-shot example (good) from a recording review."""
    try:
        import json as _json
        body = _json.loads(request.body)
        return JsonResponse(get_client(request)._post("/coaching/from-recording", body), status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def coaching_list(request):
    client = get_client(request)
    try:
        return JsonResponse(client.list_coaching_cards(
            agent_id=request.GET.get("agent_id", ""),
            status=request.GET.get("status", "pending"),
        ))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def coaching_detail(request, card_id):
    try:
        return JsonResponse(get_client(request).get_coaching_card(card_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def coaching_approve(request, card_id):
    try:
        return JsonResponse(get_client(request).approve_coaching_card(card_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def coaching_reject(request, card_id):
    try:
        return JsonResponse(get_client(request).reject_coaching_card(card_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def coaching_report(request, agent_id):
    try:
        return JsonResponse(get_client(request).get_coaching_report(agent_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def agent_revise(request, agent_id):
    """POST /api/agents/{agent_id}/revise — per-prompt revision with diff preview."""
    try:
        import json as _json
        body = _json.loads(request.body)
        return JsonResponse(get_client(request)._post(f"/agents/{agent_id}/revise", body))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ── Prompt-to-Agent 2.0 ──────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def agent_preview_from_prompt(request):
    """Extract intent + generate full structured config (no DB write)."""
    import json as _json
    try:
        body = _json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    try:
        return JsonResponse(get_client(request).preview_agent_from_prompt(body))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def agent_create_from_preview(request):
    """Create agent from confirmed preview config + auto-simulate."""
    import json as _json
    try:
        body = _json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    try:
        return JsonResponse(get_client(request).create_agent_from_preview(body), status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def agent_versions_list(request, agent_id):
    try:
        return JsonResponse(get_client(request).list_agent_versions(agent_id), safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def agent_version_save(request, agent_id):
    import json as _json
    try:
        body = _json.loads(request.body or b"{}")
    except Exception:
        body = {}
    try:
        return JsonResponse(get_client(request).save_agent_version(agent_id, body), status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def agent_version_restore(request, agent_id, version_id):
    try:
        return JsonResponse(get_client(request).restore_agent_version(agent_id, version_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def agent_revision_diff(request, agent_id):
    import json as _json
    try:
        body = _json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    try:
        return JsonResponse(get_client(request).get_revision_diff(agent_id, body))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def agent_auto_simulate(request, agent_id):
    import json as _json
    try:
        body = _json.loads(request.body or b"{}")
    except Exception:
        body = {}
    try:
        return JsonResponse(get_client(request).auto_simulate_agent(agent_id, body))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ── Agent Telephony & WhatsApp ────────────────────────────────────────────────

@login_required
@require_http_methods(["PUT"])
def agent_telephony(request, agent_id):
    """Update telephony provider and TTS settings for an agent."""
    try:
        return JsonResponse(get_client(request).update_agent_telephony(agent_id, _json_body(request)))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def agent_whatsapp(request, agent_id):
    """Configure WhatsApp channel for an agent."""
    try:
        return JsonResponse(get_client(request).configure_agent_whatsapp(agent_id, _json_body(request)))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── Simulation Endpoints ──────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def agent_simulate(request, agent_id):
    """Run simulation scenarios for an agent."""
    try:
        return JsonResponse(get_client(request).run_agent_simulation(agent_id, _json_body(request)))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def agent_simulate_adversarial(request, agent_id):
    """Generate adversarial simulation scenarios for an agent."""
    try:
        return JsonResponse(get_client(request).run_adversarial_simulation(agent_id, _json_body(request)))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── Agent Templates ───────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def templates_list(request):
    """List available agent templates."""
    try:
        return JsonResponse(get_client(request).list_templates(), safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── Voice Library ─────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def voice_catalog(request):
    """Full voice catalog with optional filter params."""
    try:
        params = {k: v for k, v in request.GET.items() if v}
        return JsonResponse(get_client(request).get_voice_catalog(**params))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def voice_preview_api(request):
    """Generate a cached voice preview clip."""
    try:
        return JsonResponse(get_client(request).get_voice_preview(_json_body(request)))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["GET", "POST"])
def voice_clones(request):
    """List clones (GET) or upload a new clone (POST multipart)."""
    client = get_client(request)
    try:
        if request.method == "GET":
            return JsonResponse(client.list_voice_clones())
        # POST — multipart file upload
        audio = request.FILES.get("audio")
        if not audio:
            return JsonResponse({"error": "No audio file in request"}, status=400)
        return JsonResponse(
            client.upload_voice_clone(
                audio_data=audio.read(),
                filename=audio.name or "recording.mp3",
                name=request.POST.get("name", "My Clone"),
                language=request.POST.get("language", "en-IN"),
            ),
            status=201,
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def voice_clone_preview_stream(request, clone_id):
    """Stream the reference audio for playback in the browser."""
    import httpx
    from django.http import StreamingHttpResponse
    from django.conf import settings as django_settings
    backend = getattr(django_settings, "BACKEND_API_URL", "http://127.0.0.1:8040").rstrip("/")
    headers = get_client(request)._headers()
    try:
        resp = httpx.get(f"{backend}/api/voices/clones/{clone_id}/preview", headers=headers, timeout=15)
        content_type = resp.headers.get("content-type", "audio/mpeg")
        return StreamingHttpResponse(resp.iter_bytes(), content_type=content_type)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=502)


@login_required
@require_http_methods(["DELETE"])
def voice_clone_delete(request, clone_id):
    """Delete a cloned voice."""
    try:
        return JsonResponse(get_client(request).delete_voice_clone(clone_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── Integrations proxy ────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET", "PUT"])
def integrations_get(request, agent_id):
    import json as _json
    if request.method == "PUT":
        try:
            body = _json.loads(request.body)
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        try:
            return JsonResponse(get_client(request).save_integrations(agent_id, body))
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    try:
        return JsonResponse(get_client(request).get_integrations(agent_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# kept for backward-compat — URL pattern routes PUT to integrations_get above
@login_required
@require_http_methods(["PUT"])
def integrations_save(request, agent_id):
    import json as _json
    try:
        body = _json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    try:
        return JsonResponse(get_client(request).save_integrations(agent_id, body))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def integrations_test(request, agent_id, int_type):
    try:
        return JsonResponse(get_client(request).test_integration(agent_id, int_type))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["DELETE"])
def integrations_remove(request, agent_id, int_type):
    try:
        return JsonResponse(get_client(request).remove_integration(agent_id, int_type))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["GET", "PUT"])
def integrations_variables(request, agent_id):
    import json as _json
    client = get_client(request)
    try:
        if request.method == "GET":
            return JsonResponse(client.get_integration_variables(agent_id))
        body = _json.loads(request.body)
        return JsonResponse(client.save_integration_variables(agent_id, body))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def integrations_run_delivery(request, agent_id, call_log_id):
    try:
        return JsonResponse(get_client(request).run_delivery(agent_id, call_log_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── Phone Numbers Shop ─────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def phone_numbers_search(request):
    try:
        return JsonResponse(get_client(request).search_phone_numbers(
            country=request.GET.get("country", "US"),
            number_type=request.GET.get("number_type", "local"),
            area_code=request.GET.get("area_code", ""),
            provider=request.GET.get("provider", "twilio"),
        ))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def phone_numbers_owned(request):
    try:
        return JsonResponse(get_client(request).list_owned_phone_numbers())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def phone_numbers_purchase(request):
    try:
        body = _json_body(request)
        return JsonResponse(get_client(request).purchase_phone_number(
            body.get("phone_number", ""), body.get("provider", "twilio")
        ), status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["DELETE"])
def phone_number_release(request, number_id):
    try:
        return JsonResponse(get_client(request).release_phone_number(number_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def phone_number_assign(request, phone_encoded):
    try:
        body = _json_body(request)
        return JsonResponse(get_client(request).assign_phone_number(phone_encoded, body.get("agent_id", "")))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def phone_number_unassign(request, phone_encoded):
    try:
        return JsonResponse(get_client(request).unassign_phone_number(phone_encoded))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── Live Call Monitor ──────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def live_monitor_calls(request):
    try:
        return JsonResponse(get_client(request).list_live_calls())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def live_monitor_takeover(request, call_sid):
    try:
        body = _json_body(request)
        return JsonResponse(get_client(request).live_monitor_takeover(
            call_sid, body.get("transfer_to", ""), body.get("whisper_message", "")
        ))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def live_monitor_end(request, call_sid):
    try:
        return JsonResponse(get_client(request).live_monitor_end(call_sid))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def live_monitor_note(request, call_sid):
    try:
        body = _json_body(request)
        return JsonResponse(get_client(request).live_monitor_note(call_sid, body.get("note", "")))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def live_monitor_whisper(request, call_sid):
    try:
        body = _json_body(request)
        return JsonResponse(get_client(request).live_monitor_whisper(call_sid, body.get("hint", "")))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── Speaker Verification (Voice Biometrics) ───────────────────────────────────

@login_required
@require_http_methods(["GET"])
def speaker_verification_list(request):
    try:
        return JsonResponse(get_client(request).list_voiceprints())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def speaker_verification_enroll(request):
    """Enroll a voiceprint — expects multipart/form-data with audio file."""
    try:
        client = get_client(request)
        audio_file = request.FILES.get("audio")
        if not audio_file:
            return JsonResponse({"error": "No audio file provided."}, status=400)
        phone_number = request.POST.get("phone_number", "")
        contact_id = request.POST.get("contact_id") or None
        label = request.POST.get("label") or None
        sample_rate = int(request.POST.get("sample_rate", 16000))
        result = client.enroll_voiceprint(
            audio_file=audio_file,
            phone_number=phone_number,
            contact_id=contact_id,
            label=label,
            sample_rate=sample_rate,
        )
        return JsonResponse(result, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def speaker_verification_verify(request):
    """Verify audio against stored voiceprints — multipart/form-data."""
    try:
        client = get_client(request)
        audio_file = request.FILES.get("audio")
        if not audio_file:
            return JsonResponse({"error": "No audio file provided."}, status=400)
        phone_number = request.POST.get("phone_number", "")
        sample_rate = int(request.POST.get("sample_rate", 16000))
        result = client.verify_voiceprint(
            audio_file=audio_file,
            phone_number=phone_number,
            sample_rate=sample_rate,
        )
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["DELETE"])
def speaker_verification_delete(request, voiceprint_id):
    try:
        return JsonResponse(get_client(request).delete_voiceprint(voiceprint_id))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── Background Ambient Sound ──────────────────────────────────────────────────

@login_required
def background_sound_types(request):
    try:
        return JsonResponse(get_client(request)._get("/api/background-sound/types"))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def background_sound_config(request, agent_id):
    try:
        client = get_client(request)
        if request.method == "PUT":
            import json as _json
            body = _json.loads(request.body)
            return JsonResponse(client._put(f"/api/background-sound/{agent_id}", json=body))
        return JsonResponse(client._get(f"/api/background-sound/{agent_id}"))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ── SIP Trunking ──────────────────────────────────────────────────────────────

@login_required
def sip_trunks_list(request):
    try:
        client = get_client(request)
        if request.method == "POST":
            import json as _json
            return JsonResponse(client._post("/api/sip-trunking/trunks", json=_json.loads(request.body)))
        return JsonResponse(client._get("/api/sip-trunking/trunks"))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def sip_trunk_detail(request, trunk_id):
    try:
        client = get_client(request)
        if request.method == "DELETE":
            return JsonResponse(client._delete(f"/api/sip-trunking/trunks/{trunk_id}"))
        return JsonResponse(client._get(f"/api/sip-trunking/trunks/{trunk_id}"))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def sip_trunk_test(request, trunk_id):
    try:
        return JsonResponse(get_client(request)._post(f"/api/sip-trunking/trunks/{trunk_id}/test", json={}))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def sip_webhook_uri(request, agent_id):
    try:
        return JsonResponse(get_client(request)._get(f"/api/sip-trunking/webhook-uri/{agent_id}"))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ── Widget (public endpoints — no login_required) ─────────────────────────────

def widget_embed_js(request, agent_id):
    """Proxy the embeddable JS widget file; passes branding query params to backend."""
    import requests as _req
    from django.http import HttpResponse
    from django.conf import settings as _settings
    qs = request.GET.urlencode()
    url = f"{_settings.BACKEND_API_URL}/api/widget/{agent_id}/embed.js"
    if qs:
        url += "?" + qs
    try:
        r = _req.get(url, timeout=10)
        return HttpResponse(r.content, content_type="application/javascript", status=r.status_code)
    except Exception as e:
        return HttpResponse(f"console.error('VoiceFlow proxy error');", content_type="application/javascript", status=502)


def widget_sessions(request, agent_id):
    """Create a new widget chat session — public."""
    try:
        import json as _json
        import requests as _req
        from django.conf import settings as _settings
        body = _json.loads(request.body) if request.body else {}
        r = _req.post(f"{_settings.BACKEND_API_URL}/api/widget/{agent_id}/sessions", json=body, timeout=10)
        return JsonResponse(r.json(), status=r.status_code)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=502)


def widget_session_message(request, agent_id, session_id):
    """Send a chat message in a widget session — public."""
    try:
        import json as _json
        import requests as _req
        from django.conf import settings as _settings
        body = _json.loads(request.body) if request.body else {}
        r = _req.post(
            f"{_settings.BACKEND_API_URL}/api/widget/{agent_id}/sessions/{session_id}/message",
            json=body, timeout=30,
        )
        return JsonResponse(r.json(), status=r.status_code)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=502)


def widget_call_request(request, agent_id):
    """Request a callback from the widget — public."""
    try:
        import json as _json
        import requests as _req
        from django.conf import settings as _settings
        body = _json.loads(request.body) if request.body else {}
        r = _req.post(f"{_settings.BACKEND_API_URL}/api/widget/{agent_id}/call-request", json=body, timeout=10)
        return JsonResponse(r.json(), status=r.status_code)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=502)


# ── CRM Integration Settings ──────────────────────────────────────────────────

@login_required
@require_http_methods(["GET", "POST"])
def crm_field_mapping(request):
    """GET/POST the CRM field mapping config for this tenant."""
    try:
        client = get_client(request)
        if request.method == "POST":
            return JsonResponse(client._post("/crm/field-mapping", _json_body(request)))
        return JsonResponse(client._get("/crm/field-mapping"))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def crm_lookup(request):
    """Look up enriched contact data by phone number from the connected CRM."""
    try:
        phone = request.GET.get("phone", "")
        return JsonResponse(get_client(request)._get("/crm/lookup", params={"phone": phone}))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST", "DELETE"])
def crm_connect_hubspot(request):
    """BYOK: save (POST) or remove (DELETE) a HubSpot Private App token."""
    try:
        client = get_client(request)
        if request.method == "DELETE":
            return JsonResponse(client._delete("/crm/connect/hubspot"))
        return JsonResponse(client._post("/crm/connect/hubspot", _json_body(request)))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST", "DELETE"])
def crm_connect_salesforce(request):
    """BYOK: save (POST) or remove (DELETE) Salesforce access token + instance URL."""
    try:
        client = get_client(request)
        if request.method == "DELETE":
            return JsonResponse(client._delete("/crm/connect/salesforce"))
        return JsonResponse(client._post("/crm/connect/salesforce", _json_body(request)))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


