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

    # API proxy endpoints (for HTMX / JS calls from the browser)
    path("api/agents/", api_proxy.agents_list, name="api_agents"),
    path("api/agents/<str:agent_id>/", api_proxy.agent_detail_api, name="api_agent_detail"),
    path("api/agents/<str:agent_id>/activate/", api_proxy.agent_activate, name="api_agent_activate"),
    path("api/agents/<str:agent_id>/pause/", api_proxy.agent_pause, name="api_agent_pause"),
    path("api/agents/<str:agent_id>/deploy/", api_proxy.agent_deploy, name="api_agent_deploy"),
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
    path("api/settings/", api_proxy.settings_api, name="api_settings"),
    path("api/settings/twilio/", api_proxy.twilio_credentials, name="api_twilio_credentials"),
    path("api/settings/groq/", api_proxy.groq_api_key, name="api_groq_key"),
    path("api/analytics/overview/", api_proxy.analytics_overview, name="api_analytics"),
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

    # DND
    path("api/dnd/", api_proxy.dnd_api, name="api_dnd"),
    path("api/dnd/<str:number_id>/", api_proxy.dnd_delete, name="api_dnd_delete"),
    path("api/dnd/bulk/", api_proxy.dnd_bulk, name="api_dnd_bulk"),
]
