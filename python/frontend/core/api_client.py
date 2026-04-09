"""
HTTP client for talking to the FastAPI backend.
Mirrors the Next.js api-client.ts — every method calls the backend with
tenant/user headers and returns parsed JSON.
"""
import httpx
from django.conf import settings

TIMEOUT = 30.0


class BackendClient:
    def __init__(self, tenant_id: str = "", user_id: str = ""):
        self.base = settings.BACKEND_API_URL.rstrip("/")
        self.tenant_id = tenant_id
        self.user_id = user_id

    @property
    def _headers(self):
        return {
            "x-tenant-id": self.tenant_id,
            "x-user-id": self.user_id,
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self.base}/{path.lstrip('/')}"

    # ── helpers ────────────────────────────────────────────────────────
    def _get(self, path, params=None):
        with httpx.Client(timeout=TIMEOUT) as c:
            r = c.get(self._url(path), headers=self._headers, params=params)
            r.raise_for_status()
            return r.json()

    def _post(self, path, json=None, data=None, files=None):
        headers = {k: v for k, v in self._headers.items() if k != "Content-Type"} if files else self._headers
        with httpx.Client(timeout=TIMEOUT) as c:
            r = c.post(self._url(path), headers=headers, json=json, data=data, files=files)
            r.raise_for_status()
            if r.status_code == 204:
                return {}
            return r.json()

    def _put(self, path, json=None):
        with httpx.Client(timeout=TIMEOUT) as c:
            r = c.put(self._url(path), headers=self._headers, json=json)
            r.raise_for_status()
            if r.status_code == 204:
                return {}
            return r.json()

    def _patch(self, path, json=None):
        with httpx.Client(timeout=TIMEOUT) as c:
            r = c.patch(self._url(path), headers=self._headers, json=json)
            r.raise_for_status()
            if r.status_code == 204:
                return {}
            return r.json()

    def _delete(self, path):
        with httpx.Client(timeout=TIMEOUT) as c:
            r = c.delete(self._url(path), headers=self._headers)
            r.raise_for_status()
            if r.status_code == 204:
                return {}
            try:
                return r.json()
            except Exception:
                return {}

    # ── Onboarding ─────────────────────────────────────────────────────
    def save_company_profile(self, data: dict):
        return self._post("/onboarding/company", json=data)

    def create_agent(self, data: dict):
        return self._post("/api/agents/", json=data)

    def upload_knowledge(self, files=None, websites=None, faq_text="", agent_id=""):
        payload = {"websites": websites or [], "faqText": faq_text}
        if agent_id:
            payload["agentId"] = agent_id
        return self._post("/onboarding/knowledge", json=payload)

    def upload_document(self, file_tuple, agent_id: str = ""):
        data = {"agentId": agent_id} if agent_id else {}
        return self._post("/api/documents/upload", files={"file": file_tuple}, data=data)

    def configure_voice(self, data: dict):
        return self._post("/onboarding/voice", json=data)

    def save_agent_config(self, data: dict):
        return self._post("/onboarding/agent-config", json=data)

    def setup_channels(self, data: dict):
        return self._post("/onboarding/channels", json=data)

    def deploy_agent(self, agent_id: str):
        return self._post(f"/api/agents/{agent_id}/activate")

    def get_deployment_status(self, agent_id: str):
        return self._get(f"/api/agents/{agent_id}")

    # ── Agents ─────────────────────────────────────────────────────────
    def get_agents(self, page=1, limit=20):
        return self._get("/api/agents/", params={"page": page, "limit": limit})

    def get_agent(self, agent_id: str):
        return self._get(f"/api/agents/{agent_id}")

    def update_agent(self, agent_id: str, data: dict):
        return self._put(f"/api/agents/{agent_id}", json=data)

    def delete_agent(self, agent_id: str):
        return self._delete(f"/api/agents/{agent_id}")

    def activate_agent(self, agent_id: str):
        return self._post(f"/api/agents/{agent_id}/activate")

    def pause_agent(self, agent_id: str):
        return self._post(f"/api/agents/{agent_id}/pause")

    def get_agent_templates(self):
        return self._get("/api/templates/")

    # ── Runner / Chat / Audio ──────────────────────────────────────────
    def chat(self, agent_id: str, message: str, session_id: str):
        return self._post("/api/runner/chat", json={
            "agentId": agent_id, "message": message, "sessionId": session_id,
        })

    def send_audio(self, agent_id: str, session_id: str, audio_bytes: bytes, filename: str = "audio.webm"):
        return self._post("/api/runner/audio", data={
            "agentId": agent_id, "sessionId": session_id,
        }, files={"audio": (filename, audio_bytes, "audio/webm")})

    # ── Voice / TTS ────────────────────────────────────────────────────
    def get_preset_voices(self):
        return self._get("/api/tts/preset-voices")

    def clone_voice(self, audio_bytes: bytes, filename: str = "sample.webm"):
        return self._post("/api/tts/clone-voice", files={"audio": (filename, audio_bytes, "audio/webm")})

    def synthesize_tts(self, text: str, voice_id: str = ""):
        """Returns JSON dict with audioUrl from TTS service."""
        return self._post("/api/tts/synthesise", json={"text": text, "voiceId": voice_id})

    def preview_voice(self, voice_id: str):
        """Generate a preview audio clip for a voice."""
        return self._post("/api/tts/preview", json={"voiceId": voice_id})

    # ── Knowledge Base (proxied to onboarding/documents) ───────────────
    def get_knowledge_base(self):
        return self._get("/api/documents/", params={"limit": 100})

    def get_company_profile(self):
        return self._get("/onboarding/company")

    def get_company_knowledge(self):
        return self._get("/onboarding/company-knowledge")

    def delete_company_knowledge(self, chunk_id: str):
        return self._delete(f"/onboarding/company-knowledge/{chunk_id}")

    def trigger_url_ingestion(self, url: str):
        return self._post("/api/ingestion/start", json={"urls": [url]})

    def get_ingestion_status(self, job_id: str):
        return self._get(f"/api/ingestion/status/{job_id}")

    def delete_document(self, doc_id: str):
        return self._delete(f"/api/documents/{doc_id}")

    # ── Analytics ──────────────────────────────────────────────────────
    def get_analytics_overview(self, time_range="7d", agent_id=""):
        params = {"timeRange": time_range}
        if agent_id:
            params["agentId"] = agent_id
        return self._get("/analytics/overview", params=params)

    def get_analytics_metrics(self, time_range="7d"):
        return self._get("/analytics/metrics-chart", params={"timeRange": time_range})

    # ── Call Logs ──────────────────────────────────────────────────────
    def get_call_logs(self, page=1, limit=20, agent_id="", search=""):
        params = {"page": page, "limit": limit}
        if agent_id:
            params["agentId"] = agent_id
        if search:
            params["search"] = search
        return self._get("/api/logs/", params=params)

    def get_call_log(self, log_id: str):
        return self._get(f"/api/logs/{log_id}")

    def rate_call_log(self, log_id: str, rating: int):
        return self._patch(f"/api/logs/{log_id}/rating", json={"rating": rating})

    def flag_for_retraining(self, log_id: str):
        return self._post(f"/api/logs/{log_id}/flag")

    # ── Retraining ─────────────────────────────────────────────────────
    def get_retraining_examples(self, page=1, limit=20, status=""):
        params = {"page": page, "limit": limit}
        if status:
            params["status"] = status
        return self._get("/api/retraining/", params=params)

    def get_retraining_stats(self):
        return self._get("/api/retraining/stats")

    def update_retraining_example(self, example_id: str, data: dict):
        return self._patch(f"/api/retraining/{example_id}", json=data)

    def delete_retraining_example(self, example_id: str):
        return self._delete(f"/api/retraining/{example_id}")

    def trigger_retraining_pipeline(self):
        return self._post("/api/retraining/process")

    # ── Settings ───────────────────────────────────────────────────────
    def get_settings(self):
        return self._get("/api/settings/")

    def update_settings(self, data: dict):
        return self._put("/api/settings/", json=data)

    def save_twilio_credentials(self, data: dict):
        return self._post("/api/settings/twilio", json=data)

    def get_twilio_credential_status(self):
        return self._get("/api/settings/twilio")

    def delete_twilio_credentials(self):
        return self._delete("/api/settings/twilio")

    def save_groq_api_key(self, data: dict):
        return self._post("/api/settings/groq", json=data)

    def get_groq_key_status(self):
        return self._get("/api/settings/groq")

    def delete_groq_api_key(self):
        return self._delete("/api/settings/groq")

    def get_twilio_numbers(self):
        return self._get("/twilio/numbers")

    # ── System / Groq Models ──────────────────────────────────────────
    def get_system_metrics(self):
        return self._get("/health")

    def get_groq_models(self):
        return self._get("/api/settings/groq/models")

    # ── Users ──────────────────────────────────────────────────────────
    def get_users(self):
        return self._get("/api/users/")

    def create_backend_user(self, data: dict):
        return self._post("/api/users/", json=data)

    def update_backend_user(self, user_id: str, data: dict):
        return self._put(f"/api/users/{user_id}", json=data)

    def delete_backend_user(self, user_id: str):
        return self._delete(f"/api/users/{user_id}")

    # ── Billing ────────────────────────────────────────────────────────
    def get_usage_stats(self):
        return self._get("/analytics/usage")

    # ── Pipelines ──────────────────────────────────────────────────────
    def list_pipelines(self):
        return self._get("/admin/pipelines")

    def create_pipeline(self, data: dict):
        return self._post("/admin/pipelines", json=data)

    def trigger_pipeline(self, pipeline_id: str):
        return self._post("/admin/pipelines/trigger", json={"pipeline_id": pipeline_id})

    def list_pipeline_agents(self):
        return self._get("/admin/pipeline_agents")

    # ── Reports ────────────────────────────────────────────────────────
    def generate_report(self, data: dict):
        return self._post("/admin/pipelines", json=data)

    def get_reports(self):
        return self._get("/admin/pipelines")

    # ── Notifications ──────────────────────────────────────────────────
    def get_notifications(self, unread_only=False):
        params = {"unread_only": "true"} if unread_only else {}
        return self._get("/api/notifications", params=params)

    def mark_notification_read(self, notif_id: str):
        return self._post(f"/api/notifications/{notif_id}/read")

    def mark_all_notifications_read(self):
        return self._post("/api/notifications/read-all")

    # ── Audit Log ──────────────────────────────────────────────────────
    def get_audit_logs(self, limit=50, offset=0):
        return self._get("/api/audit", params={"limit": limit, "offset": offset})

    # ── System Health ──────────────────────────────────────────────────
    def get_system_health(self):
        return self._get("/api/system/health")

    def get_system_health_check(self):
        """Alias used by system page refresh."""
        return self.get_system_health()

    # ── Voice Calls ────────────────────────────────────────────────────
    def get_voice_calls(self, agent_id: str):
        return self._get(f"/api/voice/calls/{agent_id}")


def get_client(request) -> BackendClient:
    """Build a BackendClient from the current Django request."""
    tenant_id = getattr(request, "tenant_id", "")
    user_id = str(request.user.id) if request.user.is_authenticated else ""
    return BackendClient(tenant_id=tenant_id, user_id=user_id)
