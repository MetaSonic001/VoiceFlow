"""
Proxy endpoints for browser JS / HTMX to talk to the FastAPI backend.
Every endpoint requires login and injects tenant headers automatically.
"""
import json
from django.http import JsonResponse, HttpResponse
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
        audio_bytes = get_client(request).synthesize_tts(
            text=data.get("text", ""), voice_id=data.get("voiceId", ""),
        )
        return HttpResponse(audio_bytes, content_type="audio/mpeg")
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def voice_presets(request):
    try:
        return JsonResponse(get_client(request).get_preset_voices())
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


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
    try:
        result = get_client(request).upload_document((f.name, f.read(), f.content_type))
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


# ── Settings ───────────────────────────────────────────────────────────

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


# ── Analytics / Call Logs / Retraining / System / Users / Billing ──────

@login_required
def analytics_overview(request):
    try:
        return JsonResponse(get_client(request).get_analytics_overview(
            time_range=request.GET.get("range", "7d"),
            agent_id=request.GET.get("agentId", ""),
        ))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def call_logs_api(request):
    try:
        return JsonResponse(get_client(request).get_call_logs(
            page=int(request.GET.get("page", 1)),
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
