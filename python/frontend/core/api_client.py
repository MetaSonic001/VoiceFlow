"""
HTTP client for talking to the FastAPI backend.
Mirrors the Next.js api-client.ts — every method calls the backend with
tenant/user headers and returns parsed JSON.
"""
import httpx
from django.conf import settings

TIMEOUT = 30.0


class BackendClient:
    def __init__(self, tenant_id: str = "", user_id: str = "", email: str = "", display_name: str = ""):
        self.base = settings.BACKEND_API_URL.rstrip("/")
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.email = email or ""
        self.display_name = display_name or ""

    @property
    def _headers(self):
        h = {
            "x-tenant-id": self.tenant_id,
            "x-user-id": self.user_id,
            "Content-Type": "application/json",
        }
        if self.email:
            h["x-user-email"] = self.email
        if self.display_name:
            h["x-user-name"] = self.display_name
        return h

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

    def clone_preview(self, clone_id: str, text: str):
        return self._post("/api/tts/clone-preview", json={"cloneId": clone_id, "text": text})

    def synthesize_tts(self, text: str, voice_id: str = ""):
        """Returns JSON dict with audioUrl from TTS service."""
        return self._post("/api/tts/synthesise", json={"text": text, "voiceId": voice_id})

    def preview_voice(self, voice_id: str):
        """Generate a preview audio clip for a voice."""
        return self._post("/api/tts/preview", json={"voiceId": voice_id})

    # ── Knowledge Base ─────────────────────────────────────────────────
    def get_knowledge_base(self):
        return self._get("/api/documents/", params={"limit": 100})

    # ── KB Attachments (per-agent, with when_to_use filtering) ─────────
    def kb_list(self, agent_id: str):
        return self._get(f"/api/kb/{agent_id}")

    def kb_attach(self, data: dict):
        return self._post("/api/kb/attach", json=data)

    def kb_ingest_file(self, file_bytes: bytes, filename: str, agent_id: str, when_to_use: str = ""):
        return self._post(
            "/api/kb/ingest-file",
            files={"file": (filename, file_bytes)},
            data={"agentId": agent_id, "whenToUse": when_to_use},
        )

    def kb_ingest_url(self, agent_id: str, url: str, when_to_use: str = ""):
        return self._post("/api/kb/ingest-url", json={"agentId": agent_id, "url": url, "whenToUse": when_to_use})

    def kb_ingest_text(self, agent_id: str, text: str, title: str = "", when_to_use: str = ""):
        return self._post("/api/kb/ingest-text", json={
            "agentId": agent_id, "text": text, "title": title, "whenToUse": when_to_use,
        })

    def kb_update_attachment(self, att_id: str, data: dict):
        return self._patch(f"/api/kb/attachments/{att_id}", json=data)

    def kb_delete_attachment(self, att_id: str):
        return self._delete(f"/api/kb/attachments/{att_id}")

    def kb_test_query(self, agent_id: str, query: str):
        return self._post("/api/kb/test-query", json={"agentId": agent_id, "query": query})

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

    def get_all_key_statuses(self):
        return self._get("/api/settings/keys/all")

    def save_openai_api_key(self, data: dict):
        return self._post("/api/settings/openai", json=data)

    def get_openai_key_status(self):
        return self._get("/api/settings/openai")

    def delete_openai_api_key(self):
        return self._delete("/api/settings/openai")

    def save_anthropic_api_key(self, data: dict):
        return self._post("/api/settings/anthropic", json=data)

    def get_anthropic_key_status(self):
        return self._get("/api/settings/anthropic")

    def delete_anthropic_api_key(self):
        return self._delete("/api/settings/anthropic")

    def save_gemini_api_key(self, data: dict):
        return self._post("/api/settings/gemini", json=data)

    def get_gemini_key_status(self):
        return self._get("/api/settings/gemini")

    def delete_gemini_api_key(self):
        return self._delete("/api/settings/gemini")

    def save_elevenlabs_api_key(self, data: dict):
        return self._post("/api/settings/elevenlabs", json=data)

    def get_elevenlabs_key_status(self):
        return self._get("/api/settings/elevenlabs")

    def delete_elevenlabs_api_key(self):
        return self._delete("/api/settings/elevenlabs")

    def save_sarvam_api_key(self, data: dict):
        return self._post("/api/settings/sarvam", json=data)

    def get_sarvam_key_status(self):
        return self._get("/api/settings/sarvam")

    def delete_sarvam_api_key(self):
        return self._delete("/api/settings/sarvam")

    def save_deepgram_api_key(self, data: dict):
        return self._post("/api/settings/deepgram", json=data)

    def get_deepgram_key_status(self):
        return self._get("/api/settings/deepgram")

    def delete_deepgram_api_key(self):
        return self._delete("/api/settings/deepgram")

    def save_assemblyai_api_key(self, data: dict):
        return self._post("/api/settings/assemblyai", json=data)

    def get_assemblyai_key_status(self):
        return self._get("/api/settings/assemblyai")

    def delete_assemblyai_api_key(self):
        return self._delete("/api/settings/assemblyai")

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

    # ── Data Explorer ──────────────────────────────────────────────────
    def get_data_overview(self):
        return self._get("/api/data-explorer/overview")

    def get_data_postgres(self):
        return self._get("/api/data-explorer/postgres")

    def get_data_chromadb(self):
        return self._get("/api/data-explorer/chromadb")

    def get_data_redis(self):
        return self._get("/api/data-explorer/redis")

    # ── Brands ─────────────────────────────────────────────────────────
    def get_brands(self):
        return self._get("/api/brands/")

    def get_brand(self, brand_id: str):
        return self._get(f"/api/brands/{brand_id}")

    def create_brand(self, data: dict):
        return self._post("/api/brands/", json=data)

    def update_brand(self, brand_id: str, data: dict):
        return self._put(f"/api/brands/{brand_id}", json=data)

    def delete_brand(self, brand_id: str):
        return self._delete(f"/api/brands/{brand_id}")

    # ── IVR Trees ──────────────────────────────────────────────────────
    def list_ivr_trees(self):
        return self._get("/api/ivr/")

    def get_ivr_tree(self, tree_id: str):
        return self._get(f"/api/ivr/{tree_id}")

    def create_ivr_tree(self, data: dict):
        return self._post("/api/ivr/", json=data)

    def update_ivr_tree(self, tree_id: str, data: dict):
        return self._put(f"/api/ivr/{tree_id}", json=data)

    def delete_ivr_tree(self, tree_id: str):
        return self._delete(f"/api/ivr/{tree_id}")

    # ── Call Recordings ────────────────────────────────────────────────
    def list_recordings(self, page=1, limit=20, agent_id="", search=""):
        params: dict = {"page": page, "limit": limit}
        if agent_id:
            params["agent_id"] = agent_id
        if search:
            params["search"] = search
        return self._get("/api/recordings/", params=params)

    def get_recording(self, recording_id: str):
        return self._get(f"/api/recordings/{recording_id}")

    def get_recording_download_url(self, recording_id: str):
        return self._get(f"/api/recordings/{recording_id}/download")

    def delete_recording(self, recording_id: str):
        return self._delete(f"/api/recordings/{recording_id}")

    # ── Contacts (OmniCRM) ─────────────────────────────────────────────
    def list_contacts(self, page=1, limit=25, search="", intent_level=""):
        params: dict = {"page": page, "limit": limit}
        if search:
            params["search"] = search
        if intent_level:
            params["intent_level"] = intent_level
        return self._get("/api/contacts/", params=params)

    def get_contact(self, contact_id: str):
        return self._get(f"/api/contacts/{contact_id}")

    def create_contact(self, data: dict):
        return self._post("/api/contacts/", json=data)

    def update_contact(self, contact_id: str, data: dict):
        return self._put(f"/api/contacts/{contact_id}", json=data)

    def delete_contact(self, contact_id: str):
        return self._delete(f"/api/contacts/{contact_id}")

    def add_contact_note(self, contact_id: str, note: str):
        return self._post(f"/api/contacts/{contact_id}/note", json={"note": note})

    # ── Coaching Cards ─────────────────────────────────────────────────
    def list_coaching_cards(self, agent_id="", status="pending"):
        params: dict = {}
        if agent_id:
            params["agent_id"] = agent_id
        if status:
            params["status"] = status
        return self._get("/api/coaching/", params=params)

    def get_coaching_card(self, card_id: str):
        return self._get(f"/api/coaching/{card_id}")

    def approve_coaching_card(self, card_id: str):
        return self._post(f"/api/coaching/{card_id}/approve")

    def reject_coaching_card(self, card_id: str):
        return self._post(f"/api/coaching/{card_id}/reject")

    def get_coaching_report(self, agent_id: str):
        return self._get(f"/api/coaching/agents/{agent_id}/report")

    # ── Prompt-to-Agent 2.0 ─────────────────────────────────────────────
    def preview_agent_from_prompt(self, data: dict):
        """Extract intent + generate structured config (no DB write)."""
        return self._post("/api/agents/generate-from-prompt/preview", json=data)

    def create_agent_from_preview(self, data: dict):
        """Create agent from confirmed preview + auto-generate sim suite."""
        return self._post("/api/agents/generate-from-prompt/create", json=data)

    def list_agent_versions(self, agent_id: str):
        return self._get(f"/api/agents/{agent_id}/versions")

    def save_agent_version(self, agent_id: str, data: dict):
        return self._post(f"/api/agents/{agent_id}/versions", json=data)

    def restore_agent_version(self, agent_id: str, version_id: str):
        return self._post(f"/api/agents/{agent_id}/versions/{version_id}/restore")

    def get_revision_diff(self, agent_id: str, data: dict):
        return self._post(f"/api/agents/{agent_id}/revision-diff", json=data)

    def auto_simulate_agent(self, agent_id: str, data: dict):
        return self._post(f"/api/agents/{agent_id}/auto-simulate", json=data)

    def update_agent_telephony(self, agent_id: str, data: dict):
        return self._put(f"/api/agents/{agent_id}/telephony", json=data)

    def configure_agent_whatsapp(self, agent_id: str, data: dict):
        return self._post(f"/api/agents/{agent_id}/whatsapp", json=data)

    def run_agent_simulation(self, agent_id: str, data: dict):
        return self._post(f"/api/simulate/{agent_id}", json=data)

    def run_adversarial_simulation(self, agent_id: str, data: dict):
        return self._post(f"/api/simulate/{agent_id}/adversarial", json=data)

    def run_simulation_gate(self, agent_id: str, data: dict):
        return self._post(f"/api/simulate/{agent_id}/gate", json=data)

    def list_templates(self):
        return self._get("/api/templates")

    # ── Voice Library ──────────────────────────────────────────────────
    def get_voice_catalog(self, language=None, gender=None, provider=None, category=None, search=None):
        params = {k: v for k, v in {
            "language": language, "gender": gender, "provider": provider,
            "category": category, "search": search,
        }.items() if v}
        return self._get("/api/voices/catalog", params=params)

    def get_voice_preview(self, body: dict):
        return self._post("/api/voices/preview", json=body)

    def list_voice_clones(self):
        return self._get("/api/voices/clones")

    def upload_voice_clone(self, audio_data: bytes, filename: str, name: str, language: str):
        import io
        files = {"audio": (filename, io.BytesIO(audio_data), "audio/mpeg")}
        data  = {"name": name, "language": language}
        return self._post("/api/voices/clones", files=files, data=data)

    def delete_voice_clone(self, clone_id: str):
        return self._delete(f"/api/voices/clones/{clone_id}")

    # ── Integrations ───────────────────────────────────────────────────
    def get_integrations(self, agent_id: str):
        return self._get(f"/api/integrations/{agent_id}")

    def save_integrations(self, agent_id: str, data: dict):
        return self._put(f"/api/integrations/{agent_id}", json=data)

    def test_integration(self, agent_id: str, int_type: str):
        return self._post(f"/api/integrations/{agent_id}/test/{int_type}")

    def remove_integration(self, agent_id: str, int_type: str):
        return self._delete(f"/api/integrations/{agent_id}/{int_type}")

    def get_integration_variables(self, agent_id: str):
        return self._get(f"/api/integrations/{agent_id}/variables")

    def save_integration_variables(self, agent_id: str, data: dict):
        return self._put(f"/api/integrations/{agent_id}/variables", json=data)

    def run_delivery(self, agent_id: str, call_log_id: str):
        return self._post(f"/api/integrations/{agent_id}/run-delivery/{call_log_id}")


def get_client(request) -> BackendClient:
    """Build a BackendClient from the current Django request."""
    tenant_id = getattr(request, "tenant_id", "")
    if request.user.is_authenticated:
        user_id = str(request.user.id)
        email = getattr(request.user, "email", "") or ""
        display_name = (getattr(request.user, "get_full_name", lambda: "")() or "").strip()
        if not display_name:
            display_name = (getattr(request.user, "username", "") or "").strip()
    else:
        user_id = ""
        email = ""
        display_name = ""
    return BackendClient(tenant_id=tenant_id, user_id=user_id, email=email, display_name=display_name)
