from django.urls import path
from core.views import (
    landing, auth, dashboard, onboarding, chat, pages, api_proxy,
)

urlpatterns = [
    # Landing
    path("", landing.home, name="home"),

    # Auth
    path("auth/login/", auth.login_view, name="login"),
    path("auth/register/", auth.register_view, name="register"),
    path("auth/logout/", auth.logout_view, name="logout"),

    # Onboarding
    path("onboarding/", onboarding.flow, name="onboarding"),

    # Dashboard
    path("dashboard/", dashboard.index, name="dashboard"),
    path("dashboard/agents/<str:agent_id>/", dashboard.agent_detail, name="agent_detail"),
    path("dashboard/agents/<str:agent_id>/chat/", chat.agent_chat, name="agent_chat"),
    path("dashboard/voice-agent/", chat.voice_agent, name="voice_agent"),

    # Dashboard pages
    path("dashboard/analytics/", pages.analytics, name="analytics"),
    path("dashboard/calls/", pages.calls, name="calls"),
    path("dashboard/knowledge/", pages.knowledge, name="knowledge"),
    path("dashboard/settings/", pages.settings_page, name="settings"),
    path("dashboard/billing/", pages.billing, name="billing"),
    path("dashboard/system/", pages.system, name="system"),
    path("dashboard/users/", pages.users, name="users"),
    path("dashboard/retraining/", pages.retraining, name="retraining"),
    path("dashboard/widget/", pages.widget, name="widget"),
    path("dashboard/api-docs/", pages.api_docs, name="api_docs"),
    path("dashboard/notifications/", pages.notifications, name="notifications"),
    path("dashboard/audit/", pages.audit, name="audit"),
    path("dashboard/backup/", pages.backup, name="backup"),
    path("dashboard/reports/", pages.reports, name="reports"),
    path("dashboard/integrations/", pages.integrations, name="integrations"),
    path("dashboard/pipelines/", pages.pipelines, name="pipelines"),
    path("dashboard/brands/", pages.brands, name="brands"),
    path("dashboard/campaigns/", pages.campaigns, name="campaigns"),
    path("dashboard/webhooks/", pages.webhooks, name="webhooks"),
    path("dashboard/ab-testing/", pages.ab_testing, name="ab_testing"),
    path("dashboard/whatsapp/", pages.whatsapp, name="whatsapp"),
    path("dashboard/dnd/", pages.dnd_registry, name="dnd_registry"),
    path("dashboard/agents/builder/", pages.agent_builder, name="agent_builder"),
    path("dashboard/agents/create/", pages.agent_creator, name="agent_creator"),

    # ── Architecture Bible pages ─────────────────────────────────────────
    path("dashboard/ivr/", pages.ivr, name="ivr"),
    path("dashboard/recordings/", pages.recordings, name="recordings"),
    path("dashboard/contacts/", pages.contacts, name="contacts"),
    path("dashboard/coaching/", pages.coaching, name="coaching"),

    # API proxy endpoints (for HTMX / JS calls from the browser)
    path("api/agents/", api_proxy.agents_list, name="api_agents"),
    path("api/agents/<str:agent_id>/", api_proxy.agent_detail_api, name="api_agent_detail"),
    path("api/agents/<str:agent_id>/activate/", api_proxy.agent_activate, name="api_agent_activate"),
    path("api/agents/<str:agent_id>/pause/", api_proxy.agent_pause, name="api_agent_pause"),
    path("api/agents/<str:agent_id>/deploy/", api_proxy.agent_deploy, name="api_agent_deploy"),
    path("api/agents/<str:agent_id>/telephony/", api_proxy.agent_telephony, name="api_agent_telephony"),
    path("api/agents/<str:agent_id>/whatsapp/", api_proxy.agent_whatsapp, name="api_agent_whatsapp"),
    path("api/agents/<str:agent_id>/simulate/", api_proxy.agent_simulate, name="api_agent_simulate"),
    path("api/agents/<str:agent_id>/simulate/adversarial/", api_proxy.agent_simulate_adversarial, name="api_agent_simulate_adversarial"),
    path("api/chat/", api_proxy.chat_send, name="api_chat"),
    path("api/audio/", api_proxy.audio_send, name="api_audio"),
    path("api/tts/", api_proxy.tts_synthesize, name="api_tts"),
    path("api/tts/preview/", api_proxy.tts_preview, name="api_tts_preview"),
    path("api/voice/presets/", api_proxy.voice_presets, name="api_voice_presets"),
    path("api/voice/token/", api_proxy.voice_token, name="api_voice_token"),
    path("api/voice/clone/", api_proxy.voice_clone, name="api_voice_clone"),
    path("api/voice/clone-preview/", api_proxy.voice_clone_preview, name="api_voice_clone_preview"),
    path("api/onboarding/company/", api_proxy.onboarding_company, name="api_onboarding_company"),
    path("api/onboarding/knowledge/", api_proxy.onboarding_knowledge, name="api_onboarding_knowledge"),
    path("api/onboarding/agent-config/", api_proxy.onboarding_agent_config, name="api_onboarding_agent_config"),
    path("api/knowledge/", api_proxy.knowledge_list, name="api_knowledge"),
    path("api/knowledge/company-profile/", api_proxy.company_profile, name="api_company_profile"),
    path("api/knowledge/company-knowledge/", api_proxy.company_knowledge, name="api_company_knowledge"),
    path("api/documents/upload/", api_proxy.document_upload, name="api_document_upload"),
    path("api/documents/ingest-url/", api_proxy.document_ingest_url, name="api_document_ingest_url"),
    path("api/documents/<str:doc_id>/", api_proxy.document_delete, name="api_document_delete"),
    # ── Knowledge Base (per-agent) — specific paths BEFORE wildcard ─────────
    path("api/kb/attach/",                      api_proxy.kb_attach,            name="api_kb_attach"),
    path("api/kb/ingest-file/",                 api_proxy.kb_ingest_file,       name="api_kb_ingest_file"),
    path("api/kb/ingest-url/",                  api_proxy.kb_ingest_url,        name="api_kb_ingest_url"),
    path("api/kb/ingest-text/",                 api_proxy.kb_ingest_text,       name="api_kb_ingest_text"),
    path("api/kb/test-query/",                  api_proxy.kb_test_query,        name="api_kb_test_query"),
    path("api/kb/attachments/<str:att_id>/",    api_proxy.kb_update_attachment, name="api_kb_attachment"),
    path("api/kb/<str:agent_id>/",              api_proxy.kb_list,              name="api_kb_list"),
    path("api/settings/", api_proxy.settings_api, name="api_settings"),
    path("api/settings/twilio/", api_proxy.twilio_credentials, name="api_twilio_credentials"),
    path("api/settings/groq/", api_proxy.groq_api_key, name="api_groq_key"),
    path("api/settings/keys/all/", api_proxy.all_key_statuses, name="api_all_key_statuses"),
    path("api/settings/openai/", api_proxy.openai_api_key, name="api_openai_key"),
    path("api/settings/anthropic/", api_proxy.anthropic_api_key, name="api_anthropic_key"),
    path("api/settings/gemini/", api_proxy.gemini_api_key, name="api_gemini_key"),
    path("api/settings/elevenlabs/", api_proxy.elevenlabs_api_key, name="api_elevenlabs_key"),
    path("api/settings/sarvam/", api_proxy.sarvam_api_key, name="api_sarvam_key"),
    path("api/settings/deepgram/", api_proxy.deepgram_api_key, name="api_deepgram_key"),
    path("api/settings/assemblyai/", api_proxy.assemblyai_api_key, name="api_assemblyai_key"),
    path("api/settings/truecaller/", api_proxy.truecaller_api_key, name="api_truecaller_key"),
    path("api/analytics/overview/", api_proxy.analytics_overview, name="api_analytics"),
    path("api/analytics/resolution-stats/", api_proxy.analytics_resolution_stats, name="api_analytics_resolution"),
    path("api/analytics/top-intents/", api_proxy.analytics_top_intents, name="api_analytics_intents"),
    path("api/analytics/failure-modes/", api_proxy.analytics_failure_modes, name="api_analytics_failures"),
    path("api/analytics/cost-estimate/", api_proxy.analytics_cost_estimate, name="api_analytics_cost"),
    path("api/analytics/sentiment-trend/", api_proxy.analytics_sentiment_trend, name="api_analytics_sentiment"),
    path("api/analytics/handle-time-histogram/", api_proxy.analytics_handle_time, name="api_analytics_histogram"),
    path("api/analytics/campaign-roi/", api_proxy.analytics_campaign_roi, name="api_analytics_campaign_roi"),
    path("api/analytics/export.csv", api_proxy.analytics_export_csv, name="api_analytics_csv"),
    path("api/call-logs/", api_proxy.call_logs_api, name="api_call_logs"),
    path("api/retraining/", api_proxy.retraining_api, name="api_retraining"),
    path("api/retraining/trigger/", api_proxy.retraining_trigger, name="api_retraining_trigger"),
    path("api/system/metrics/", api_proxy.system_metrics, name="api_system_metrics"),
    path("api/users/", api_proxy.users_api, name="api_users"),
    path("api/billing/usage/", api_proxy.billing_usage, name="api_billing_usage"),
    path("api/pipelines/", api_proxy.pipelines_api, name="api_pipelines"),
    path("api/pipelines/trigger/", api_proxy.pipeline_trigger, name="api_pipeline_trigger"),
    path("api/reports/", api_proxy.reports_api, name="api_reports"),
    path("api/notifications/", api_proxy.notifications_api, name="api_notifications"),
    path("api/notification-read/<str:notif_id>/", api_proxy.notification_read, name="api_notification_read"),
    path("api/notifications-read-all/", api_proxy.notifications_read_all, name="api_notifications_read_all"),
    path("api/system/health-check/", api_proxy.system_health, name="api_system_health"),
    path("api/call-logs/<str:log_id>/flag/", api_proxy.call_log_flag, name="api_call_log_flag"),
    path("api/retraining/<str:example_id>/update/", api_proxy.retraining_update, name="api_retraining_update"),
    path("api/users/<str:user_id>/", api_proxy.user_detail_api, name="api_user_detail"),

    # Data Explorer
    path("dashboard/data-explorer/", pages.data_explorer, name="data_explorer"),
    path("api/data-explorer/overview/", api_proxy.data_explorer_overview, name="api_data_explorer_overview"),
    path("api/data-explorer/postgres/", api_proxy.data_explorer_postgres, name="api_data_explorer_postgres"),
    path("api/data-explorer/chromadb/", api_proxy.data_explorer_chromadb, name="api_data_explorer_chromadb"),
    path("api/data-explorer/redis/", api_proxy.data_explorer_redis, name="api_data_explorer_redis"),
    path("api/audit/", api_proxy.audit_api, name="api_audit"),
    path("api/brands/", api_proxy.brands_api, name="api_brands"),
    path("api/brands/<str:brand_id>/", api_proxy.brand_detail_api, name="api_brand_detail"),

    # Campaigns
    path("api/campaigns/", api_proxy.campaigns_api, name="api_campaigns"),
    path("api/campaigns/<str:campaign_id>/", api_proxy.campaign_detail_api, name="api_campaign_detail"),
    path("api/campaigns/<str:campaign_id>/contacts/upload/", api_proxy.campaign_upload_contacts, name="api_campaign_upload"),
    path("api/campaigns/<str:campaign_id>/start/", api_proxy.campaign_start, name="api_campaign_start"),
    path("api/campaigns/<str:campaign_id>/pause/", api_proxy.campaign_pause, name="api_campaign_pause"),
    path("api/campaigns/<str:campaign_id>/stats/", api_proxy.campaign_stats, name="api_campaign_stats"),

    # Webhooks
    path("api/webhooks/", api_proxy.webhooks_api, name="api_webhooks"),
    path("api/webhooks/<str:webhook_id>/", api_proxy.webhook_detail_api, name="api_webhook_detail"),

    # A/B Testing
    path("api/ab-testing/variants/", api_proxy.ab_variants_api, name="api_ab_variants"),
    path("api/ab-testing/<str:agent_id>/create-variant/", api_proxy.ab_create_variant, name="api_ab_create_variant"),
    path("api/ab-testing/<str:test_id>/results/", api_proxy.ab_results, name="api_ab_results"),

    # DND — bulk must come BEFORE the <number_id> param to avoid shadowing
    path("api/dnd/", api_proxy.dnd_api, name="api_dnd"),
    path("api/dnd/bulk/", api_proxy.dnd_bulk, name="api_dnd_bulk"),
    path("api/dnd/<str:number_id>/", api_proxy.dnd_delete, name="api_dnd_delete"),

    # ── IVR Trees ──────────────────────────────────────────────────────
    path("api/ivr/", api_proxy.ivr_list, name="api_ivr_list"),
    path("api/ivr/<str:tree_id>/", api_proxy.ivr_detail, name="api_ivr_detail"),

    # ── Call Recordings ────────────────────────────────────────────────
    path("api/recordings/", api_proxy.recordings_list, name="api_recordings_list"),
    path("api/recordings/<str:recording_id>/", api_proxy.recording_detail, name="api_recording_detail"),
    path("api/recordings/<str:recording_id>/download/", api_proxy.recording_download, name="api_recording_download"),

    # ── Contacts (OmniCRM) ─────────────────────────────────────────────
    path("api/contacts/import/", api_proxy.contacts_import_csv, name="api_contacts_import"),
    path("api/contacts/", api_proxy.contacts_list, name="api_contacts_list"),
    path("api/contacts/<str:contact_id>/", api_proxy.contact_detail, name="api_contact_detail"),
    path("api/contacts/<str:contact_id>/note/", api_proxy.contact_note, name="api_contact_note"),

    # ── CRM Settings ───────────────────────────────────────────────────
    path("dashboard/crm-settings/", pages.crm_settings, name="crm_settings"),
    path("api/crm/field-mapping/", api_proxy.crm_field_mapping, name="api_crm_field_mapping"),
    path("api/crm/lookup/", api_proxy.crm_lookup, name="api_crm_lookup"),
    # OAuth callbacks — proxy straight to backend which handles code exchange + redirects
    path("api/crm/hubspot/callback/", api_proxy.crm_hubspot_callback, name="api_crm_hubspot_callback"),
    path("api/crm/salesforce/callback/", api_proxy.crm_salesforce_callback, name="api_crm_salesforce_callback"),

    # ── Coaching Cards ─────────────────────────────────────────────────
    path("api/coaching/from-recording/", api_proxy.coaching_from_recording, name="api_coaching_from_recording"),
    path("api/coaching/", api_proxy.coaching_list, name="api_coaching_list"),
    path("api/coaching/<str:card_id>/", api_proxy.coaching_detail, name="api_coaching_detail"),
    path("api/coaching/<str:card_id>/approve/", api_proxy.coaching_approve, name="api_coaching_approve"),
    path("api/coaching/<str:card_id>/reject/", api_proxy.coaching_reject, name="api_coaching_reject"),
    path("api/coaching/agents/<str:agent_id>/report/", api_proxy.coaching_report, name="api_coaching_report"),

    # ── Prompt-to-Agent 2.0 ──────────────────────────────────────────────
    path("api/agents/generate-from-prompt/preview/", api_proxy.agent_preview_from_prompt, name="api_agent_preview"),
    path("api/agents/generate-from-prompt/create/", api_proxy.agent_create_from_preview, name="api_agent_create_preview"),
    path("api/agents/<str:agent_id>/revise/", api_proxy.agent_revise, name="api_agent_revise"),
    path("api/agents/<str:agent_id>/versions/", api_proxy.agent_versions_list, name="api_agent_versions_list"),
    path("api/agents/<str:agent_id>/versions/save/", api_proxy.agent_version_save, name="api_agent_version_save"),
    path("api/agents/<str:agent_id>/versions/<str:version_id>/restore/", api_proxy.agent_version_restore, name="api_agent_version_restore"),
    path("api/agents/<str:agent_id>/revision-diff/", api_proxy.agent_revision_diff, name="api_agent_revision_diff"),
    path("api/agents/<str:agent_id>/auto-simulate/", api_proxy.agent_auto_simulate, name="api_agent_auto_simulate"),

    # ── Agent Templates ──────────────────────────────────────────────────
    path("api/templates/", api_proxy.templates_list, name="api_templates"),

    # ── Voice Library ─────────────────────────────────────────────────────────
    path("dashboard/voice-library/", pages.voice_library, name="voice_library"),
    path("api/voices/catalog/",                  api_proxy.voice_catalog,              name="api_voice_catalog"),
    path("api/voices/preview/",                  api_proxy.voice_preview_api,           name="api_voice_preview_new"),
    path("api/voices/clones/",                   api_proxy.voice_clones,               name="api_voice_clones"),
    path("api/voices/clones/<str:clone_id>/preview/", api_proxy.voice_clone_preview_stream, name="api_voice_clone_preview"),
    path("api/voices/clones/<str:clone_id>/",    api_proxy.voice_clone_delete,         name="api_voice_clone_delete"),

    # ── Integrations ──────────────────────────────────────────────────────────
    path("api/integrations/<str:agent_id>/",                              api_proxy.integrations_get,          name="api_integrations_get"),
    path("api/integrations/<str:agent_id>/variables/",                    api_proxy.integrations_variables,    name="api_integrations_variables"),
    path("api/integrations/<str:agent_id>/test/<str:int_type>/",          api_proxy.integrations_test,         name="api_integrations_test"),
    path("api/integrations/<str:agent_id>/run-delivery/<str:call_log_id>/", api_proxy.integrations_run_delivery, name="api_integrations_run_delivery"),
    path("api/integrations/<str:agent_id>/<str:int_type>/",               api_proxy.integrations_remove,       name="api_integrations_remove"),

    # ── Phone Numbers Shop ────────────────────────────────────────────────────
    path("dashboard/phone-numbers/", pages.phone_numbers, name="phone_numbers"),
    path("api/phone-numbers/search/", api_proxy.phone_numbers_search, name="api_phone_numbers_search"),
    path("api/phone-numbers/owned/", api_proxy.phone_numbers_owned, name="api_phone_numbers_owned"),
    path("api/phone-numbers/purchase/", api_proxy.phone_numbers_purchase, name="api_phone_numbers_purchase"),
    path("api/phone-numbers/<str:number_id>/release/", api_proxy.phone_number_release, name="api_phone_number_release"),
    path("api/phone-numbers/<str:phone_encoded>/assign/", api_proxy.phone_number_assign, name="api_phone_number_assign"),
    path("api/phone-numbers/<str:phone_encoded>/unassign/", api_proxy.phone_number_unassign, name="api_phone_number_unassign"),

    # ── Live Call Monitor ─────────────────────────────────────────────────────
    path("dashboard/live-monitor/", pages.live_monitor, name="live_monitor"),
    path("api/live-monitor/calls/", api_proxy.live_monitor_calls, name="api_live_monitor_calls"),
    path("api/live-monitor/calls/<str:call_sid>/takeover/", api_proxy.live_monitor_takeover, name="api_live_monitor_takeover"),
    path("api/live-monitor/calls/<str:call_sid>/end/", api_proxy.live_monitor_end, name="api_live_monitor_end"),
    path("api/live-monitor/calls/<str:call_sid>/note/", api_proxy.live_monitor_note, name="api_live_monitor_note"),
    path("api/live-monitor/calls/<str:call_sid>/whisper/", api_proxy.live_monitor_whisper, name="api_live_monitor_whisper"),

    # ── Speaker Verification (Voice Biometrics) ───────────────────────────────
    path("api/speaker-verification/", api_proxy.speaker_verification_list, name="api_sv_list"),
    path("api/speaker-verification/enroll/", api_proxy.speaker_verification_enroll, name="api_sv_enroll"),
    path("api/speaker-verification/verify/", api_proxy.speaker_verification_verify, name="api_sv_verify"),
    path("api/speaker-verification/<str:voiceprint_id>/", api_proxy.speaker_verification_delete, name="api_sv_delete"),

    # ── Background Ambient Sound ──────────────────────────────────────────────
    path("api/background-sound/types/", api_proxy.background_sound_types, name="api_bg_sound_types"),
    path("api/background-sound/<str:agent_id>/", api_proxy.background_sound_config, name="api_bg_sound_config"),

    # ── SIP Trunking ──────────────────────────────────────────────────────────
    path("dashboard/sip-trunking/", pages.sip_trunking, name="sip_trunking"),
    path("api/sip-trunking/trunks/", api_proxy.sip_trunks_list, name="api_sip_trunks"),
    path("api/sip-trunking/trunks/<str:trunk_id>/", api_proxy.sip_trunk_detail, name="api_sip_trunk_detail"),
    path("api/sip-trunking/trunks/<str:trunk_id>/test/", api_proxy.sip_trunk_test, name="api_sip_trunk_test"),
    path("api/sip-trunking/webhook-uri/<str:agent_id>/", api_proxy.sip_webhook_uri, name="api_sip_webhook_uri"),

    # ── Widget (public, no login_required) ────────────────────────────────────
    path("api/widget/<str:agent_id>/embed.js", api_proxy.widget_embed_js, name="api_widget_embed_js"),
    path("api/widget/<str:agent_id>/sessions", api_proxy.widget_sessions, name="api_widget_sessions"),
    path("api/widget/<str:agent_id>/sessions/<str:session_id>/message", api_proxy.widget_session_message, name="api_widget_session_message"),
    path("api/widget/<str:agent_id>/call-request", api_proxy.widget_call_request, name="api_widget_call_request"),
]
