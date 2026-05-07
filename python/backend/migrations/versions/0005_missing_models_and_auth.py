"""Add all missing tables and auth columns.

Revision ID: 0005
Revises: 0004
Create Date: 2025-07-01 00:00:00.000000

Idempotent — all CREATE TABLE use IF NOT EXISTS; ALTER TABLE use IF NOT EXISTS.
Safe to re-run on a partially-migrated database.

Tables added (if missing):
  usage_logs, voice_prints, coaching_cards, ivr_trees, call_recordings,
  dnd_registry, webhook_endpoints, contacts, campaigns, campaign_contacts,
  audit_logs, notifications, pipelines, onboarding_progress,
  agent_versions, agent_templates, agent_configurations

Columns added on existing tables (if missing):
  users.passwordHash              TEXT nullable
  tenants.pilotPlanEndDate        TIMESTAMPTZ nullable
  tenants.totalCallCount          INTEGER default 0
  tenants.planType                TEXT default 'free'
  tenants.planTier                TEXT default 'free'
  tenants.stripeCustomerId        TEXT nullable
  tenants.stripeSubscriptionId    TEXT nullable
  tenants.managedMinutesBalance   INTEGER default 0
  tenants.policyRules             JSONB nullable
  agents.simulation_suite         JSONB nullable
  agents.deployment_readiness_score INTEGER nullable
  agents.post_call_actions        JSONB nullable
  agents.language_config          JSONB nullable
  agents.caller_personas          JSONB nullable
  agents.context_breakdown        JSONB nullable
  agents.welcome_message          TEXT nullable
  agents.telephony_provider       TEXT default 'twilio-gather'

Referential integrity:
  agent_versions.tenantId FK → tenants.id (added as FK constraint if missing)
"""
from alembic import op
from sqlalchemy import text

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _exec(sql: str) -> None:
    op.get_bind().execute(text(sql))


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:

    # ── Tenant: new billing / plan columns ───────────────────────────────────
    _exec('ALTER TABLE tenants ADD COLUMN IF NOT EXISTS "planType"              TEXT NOT NULL DEFAULT \'free\'')
    _exec('ALTER TABLE tenants ADD COLUMN IF NOT EXISTS "planTier"              TEXT NOT NULL DEFAULT \'free\'')
    _exec('ALTER TABLE tenants ADD COLUMN IF NOT EXISTS "stripeCustomerId"      TEXT')
    _exec('ALTER TABLE tenants ADD COLUMN IF NOT EXISTS "stripeSubscriptionId"  TEXT')
    _exec('ALTER TABLE tenants ADD COLUMN IF NOT EXISTS "managedMinutesBalance" INTEGER NOT NULL DEFAULT 0')
    _exec('ALTER TABLE tenants ADD COLUMN IF NOT EXISTS "pilotPlanEndDate"      TIMESTAMPTZ')
    _exec('ALTER TABLE tenants ADD COLUMN IF NOT EXISTS "totalCallCount"        INTEGER NOT NULL DEFAULT 0')
    _exec('ALTER TABLE tenants ADD COLUMN IF NOT EXISTS "policyRules"           JSONB')

    # ── Users: password hash ─────────────────────────────────────────────────
    _exec('ALTER TABLE users ADD COLUMN IF NOT EXISTS "passwordHash" TEXT')

    # ── Agents: extended columns ─────────────────────────────────────────────
    _exec('ALTER TABLE agents ADD COLUMN IF NOT EXISTS simulation_suite          JSONB')
    _exec('ALTER TABLE agents ADD COLUMN IF NOT EXISTS deployment_readiness_score INTEGER')
    _exec('ALTER TABLE agents ADD COLUMN IF NOT EXISTS post_call_actions          JSONB')
    _exec('ALTER TABLE agents ADD COLUMN IF NOT EXISTS language_config            JSONB')
    _exec('ALTER TABLE agents ADD COLUMN IF NOT EXISTS caller_personas            JSONB')
    _exec('ALTER TABLE agents ADD COLUMN IF NOT EXISTS context_breakdown          JSONB')
    _exec('ALTER TABLE agents ADD COLUMN IF NOT EXISTS welcome_message            TEXT')
    _exec("ALTER TABLE agents ADD COLUMN IF NOT EXISTS telephony_provider         TEXT NOT NULL DEFAULT 'twilio-gather'")

    # ── agent_templates ───────────────────────────────────────────────────────
    _exec("""
    CREATE TABLE IF NOT EXISTS agent_templates (
        id                             TEXT PRIMARY KEY,
        name                           TEXT NOT NULL UNIQUE,
        description                    TEXT,
        "baseSystemPrompt"             TEXT,
        "defaultCapabilities"          JSONB,
        "suggestedKnowledgeCategories" JSONB,
        "defaultTools"                 JSONB,
        icon                           TEXT,
        "isActive"                     BOOLEAN NOT NULL DEFAULT TRUE,
        "createdAt"                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        "updatedAt"                    TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)

    # ── agent_configurations ──────────────────────────────────────────────────
    _exec("""
    CREATE TABLE IF NOT EXISTS agent_configurations (
        id                      TEXT PRIMARY KEY,
        "agentId"               TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
        "voiceId"               TEXT,
        "responseTone"          TEXT,
        "preferredResponseStyle" TEXT,
        "languageCode"          TEXT NOT NULL DEFAULT 'en-IN',
        "enableBilingual"       BOOLEAN NOT NULL DEFAULT FALSE,
        "createdAt"             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        "updatedAt"             TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    _exec('CREATE INDEX IF NOT EXISTS ix_agent_conf_agent ON agent_configurations ("agentId")')

    # ── agent_versions ────────────────────────────────────────────────────────
    _exec("""
    CREATE TABLE IF NOT EXISTS agent_versions (
        id                  TEXT PRIMARY KEY,
        "agentId"           TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
        "tenantId"          TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        "versionNumber"     INTEGER NOT NULL DEFAULT 1,
        "changeDescription" TEXT,
        snapshot            JSONB NOT NULL DEFAULT '{}',
        "createdAt"         TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    _exec('CREATE INDEX IF NOT EXISTS ix_agent_ver_agent  ON agent_versions ("agentId")')
    _exec('CREATE INDEX IF NOT EXISTS ix_agent_ver_tenant ON agent_versions ("tenantId")')

    # If agent_versions already existed without the FK on tenantId, add it safely
    _exec("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = 'agent_versions'
              AND tc.constraint_type = 'FOREIGN KEY'
              AND kcu.column_name = 'tenantId'
        ) THEN
            BEGIN
                ALTER TABLE agent_versions
                    ADD CONSTRAINT fk_agent_versions_tenant
                    FOREIGN KEY ("tenantId") REFERENCES tenants(id) ON DELETE CASCADE;
            EXCEPTION WHEN others THEN
                NULL;  -- ignore if data doesn't satisfy the FK (dev environment)
            END;
        END IF;
    END;
    $$;
    """)

    # ── onboarding_progress ───────────────────────────────────────────────────
    _exec("""
    CREATE TABLE IF NOT EXISTS onboarding_progress (
        id            SERIAL PRIMARY KEY,
        "userEmail"   TEXT NOT NULL UNIQUE REFERENCES users(email) ON DELETE CASCADE,
        "tenantId"    TEXT REFERENCES tenants(id),
        "agentId"     TEXT,
        "currentStep" INTEGER,
        data          JSONB,
        "createdAt"   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        "updatedAt"   TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)

    # ── voice_prints ──────────────────────────────────────────────────────────
    _exec("""
    CREATE TABLE IF NOT EXISTS voice_prints (
        id               TEXT PRIMARY KEY,
        "tenantId"       TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        "phoneNumber"    TEXT NOT NULL,
        embedding        JSONB NOT NULL DEFAULT '[]',
        "callerName"     TEXT,
        "isVerified"     BOOLEAN NOT NULL DEFAULT FALSE,
        "createdAt"      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        "updatedAt"      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    _exec('CREATE INDEX IF NOT EXISTS ix_voice_prints_tenant  ON voice_prints ("tenantId")')
    _exec('CREATE INDEX IF NOT EXISTS ix_voice_prints_phone   ON voice_prints ("phoneNumber")')
    _exec('CREATE UNIQUE INDEX IF NOT EXISTS ux_voice_prints ON voice_prints ("tenantId", "phoneNumber")')

    # ── usage_logs ────────────────────────────────────────────────────────────
    _exec("""
    CREATE TABLE IF NOT EXISTS usage_logs (
        id                TEXT PRIMARY KEY,
        "tenantId"        TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        "callLogId"       TEXT REFERENCES call_logs(id) ON DELETE SET NULL,
        "durationSeconds" INTEGER NOT NULL DEFAULT 0,
        "providersUsed"   JSONB NOT NULL DEFAULT '[]',
        "rawCostInr"      NUMERIC(10, 4) NOT NULL DEFAULT 0,
        "billedAmountInr" NUMERIC(10, 4) NOT NULL DEFAULT 0,
        "stripeEventId"   TEXT,
        "createdAt"       TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    _exec('CREATE INDEX IF NOT EXISTS ix_usage_logs_tenant    ON usage_logs ("tenantId")')
    _exec('CREATE INDEX IF NOT EXISTS ix_usage_logs_call_log  ON usage_logs ("callLogId")')
    _exec('CREATE INDEX IF NOT EXISTS ix_usage_logs_created   ON usage_logs ("createdAt")')

    # ── pipelines ─────────────────────────────────────────────────────────────
    _exec("""
    CREATE TABLE IF NOT EXISTS pipelines (
        id          TEXT PRIMARY KEY,
        "tenantId"  TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        name        TEXT NOT NULL,
        description TEXT,
        steps       JSONB NOT NULL DEFAULT '[]',
        schedule    TEXT,
        "isActive"  BOOLEAN NOT NULL DEFAULT TRUE,
        "lastRunAt" TIMESTAMPTZ,
        "createdAt" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    _exec('CREATE INDEX IF NOT EXISTS ix_pipelines_tenant ON pipelines ("tenantId")')

    # ── audit_logs ────────────────────────────────────────────────────────────
    _exec("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id          TEXT PRIMARY KEY,
        "tenantId"  TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        "userId"    TEXT,
        action      TEXT NOT NULL,
        resource    TEXT,
        "resourceId" TEXT,
        details     JSONB,
        "ipAddress" TEXT,
        "userAgent" TEXT,
        "createdAt" TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    _exec('CREATE INDEX IF NOT EXISTS ix_audit_logs_tenant  ON audit_logs ("tenantId")')
    _exec('CREATE INDEX IF NOT EXISTS ix_audit_logs_created ON audit_logs ("createdAt")')

    # ── notifications ─────────────────────────────────────────────────────────
    _exec("""
    CREATE TABLE IF NOT EXISTS notifications (
        id         TEXT PRIMARY KEY,
        "tenantId" TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        type       TEXT NOT NULL DEFAULT 'info',
        title      TEXT NOT NULL,
        message    TEXT NOT NULL,
        "isRead"   BOOLEAN NOT NULL DEFAULT FALSE,
        "createdAt" TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    _exec('CREATE INDEX IF NOT EXISTS ix_notifications_tenant  ON notifications ("tenantId")')
    _exec('CREATE INDEX IF NOT EXISTS ix_notifications_read    ON notifications ("isRead")')

    # ── campaigns ─────────────────────────────────────────────────────────────
    _exec("""
    CREATE TABLE IF NOT EXISTS campaigns (
        id                TEXT PRIMARY KEY,
        "tenantId"        TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        "agentId"         TEXT REFERENCES agents(id) ON DELETE SET NULL,
        name              TEXT NOT NULL,
        description       TEXT,
        status            TEXT NOT NULL DEFAULT 'draft',
        "scheduledAt"     TIMESTAMPTZ,
        "startedAt"       TIMESTAMPTZ,
        "completedAt"     TIMESTAMPTZ,
        "totalContacts"   INTEGER NOT NULL DEFAULT 0,
        "calledContacts"  INTEGER NOT NULL DEFAULT 0,
        "answeredContacts" INTEGER NOT NULL DEFAULT 0,
        "convertedContacts" INTEGER NOT NULL DEFAULT 0,
        settings          JSONB,
        "createdAt"       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        "updatedAt"       TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    _exec('CREATE INDEX IF NOT EXISTS ix_campaigns_tenant ON campaigns ("tenantId")')
    _exec('CREATE INDEX IF NOT EXISTS ix_campaigns_status ON campaigns (status)')

    # ── campaign_contacts ─────────────────────────────────────────────────────
    _exec("""
    CREATE TABLE IF NOT EXISTS campaign_contacts (
        id           TEXT PRIMARY KEY,
        "campaignId" TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
        "tenantId"   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        phone        TEXT NOT NULL,
        name         TEXT,
        variables    JSONB,
        status       TEXT NOT NULL DEFAULT 'pending',
        "callLogId"  TEXT REFERENCES call_logs(id) ON DELETE SET NULL,
        "attemptedAt" TIMESTAMPTZ,
        "createdAt"  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    _exec('CREATE INDEX IF NOT EXISTS ix_campaign_contacts_campaign ON campaign_contacts ("campaignId")')
    _exec('CREATE INDEX IF NOT EXISTS ix_campaign_contacts_status   ON campaign_contacts (status)')

    # ── dnd_registry ──────────────────────────────────────────────────────────
    _exec("""
    CREATE TABLE IF NOT EXISTS dnd_registry (
        id          TEXT PRIMARY KEY,
        "tenantId"  TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        phone       TEXT NOT NULL,
        reason      TEXT,
        "addedBy"   TEXT,
        "createdAt" TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    _exec('CREATE UNIQUE INDEX IF NOT EXISTS ux_dnd_tenant_phone ON dnd_registry ("tenantId", phone)')

    # ── webhook_endpoints ─────────────────────────────────────────────────────
    _exec("""
    CREATE TABLE IF NOT EXISTS webhook_endpoints (
        id          TEXT PRIMARY KEY,
        "tenantId"  TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        url         TEXT NOT NULL,
        events      JSONB NOT NULL DEFAULT '[]',
        secret      TEXT,
        "isActive"  BOOLEAN NOT NULL DEFAULT TRUE,
        description TEXT,
        "createdAt" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    _exec('CREATE INDEX IF NOT EXISTS ix_webhook_endpoints_tenant ON webhook_endpoints ("tenantId")')

    # ── contacts ──────────────────────────────────────────────────────────────
    _exec("""
    CREATE TABLE IF NOT EXISTS contacts (
        id           TEXT PRIMARY KEY,
        "tenantId"   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        phone        TEXT NOT NULL,
        name         TEXT,
        email        TEXT,
        "customData" JSONB,
        tags         JSONB NOT NULL DEFAULT '[]',
        "crmSource"  TEXT,
        "crmId"      TEXT,
        "createdAt"  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        "updatedAt"  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    _exec('CREATE INDEX IF NOT EXISTS ix_contacts_tenant ON contacts ("tenantId")')
    _exec('CREATE INDEX IF NOT EXISTS ix_contacts_phone  ON contacts (phone)')
    _exec('CREATE UNIQUE INDEX IF NOT EXISTS ux_contacts_tenant_phone ON contacts ("tenantId", phone)')

    # ── ivr_trees ─────────────────────────────────────────────────────────────
    _exec("""
    CREATE TABLE IF NOT EXISTS ivr_trees (
        id            TEXT PRIMARY KEY,
        "tenantId"    TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        name          TEXT NOT NULL,
        description   TEXT,
        nodes         JSONB NOT NULL DEFAULT '[]',
        "isActive"    BOOLEAN NOT NULL DEFAULT TRUE,
        "phoneNumber" TEXT,
        "createdAt"   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        "updatedAt"   TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    _exec('CREATE INDEX IF NOT EXISTS ix_ivr_trees_tenant ON ivr_trees ("tenantId")')

    # ── call_recordings ───────────────────────────────────────────────────────
    _exec("""
    CREATE TABLE IF NOT EXISTS call_recordings (
        id               TEXT PRIMARY KEY,
        "tenantId"       TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        "callLogId"      TEXT REFERENCES call_logs(id) ON DELETE SET NULL,
        "agentId"        TEXT REFERENCES agents(id) ON DELETE SET NULL,
        "storageUrl"     TEXT,
        "storagePath"    TEXT,
        "durationSeconds" INTEGER,
        "fileSize"       INTEGER,
        format           TEXT NOT NULL DEFAULT 'mp3',
        "isEncrypted"    BOOLEAN NOT NULL DEFAULT FALSE,
        "transcriptPath" TEXT,
        "createdAt"      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    _exec('CREATE INDEX IF NOT EXISTS ix_call_recordings_tenant   ON call_recordings ("tenantId")')
    _exec('CREATE INDEX IF NOT EXISTS ix_call_recordings_call_log ON call_recordings ("callLogId")')

    # ── coaching_cards ────────────────────────────────────────────────────────
    _exec("""
    CREATE TABLE IF NOT EXISTS coaching_cards (
        id                TEXT PRIMARY KEY,
        "tenantId"        TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        "agentId"         TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
        "callLogId"       TEXT REFERENCES call_logs(id) ON DELETE SET NULL,
        "sourceType"      TEXT NOT NULL DEFAULT 'manual',
        "promptDelta"     TEXT NOT NULL,
        reasoning         TEXT,
        status            TEXT NOT NULL DEFAULT 'pending',
        "approvedBy"      TEXT,
        "approvedAt"      TIMESTAMPTZ,
        "createdAt"       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        "updatedAt"       TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    _exec('CREATE INDEX IF NOT EXISTS ix_coaching_cards_tenant  ON coaching_cards ("tenantId")')
    _exec('CREATE INDEX IF NOT EXISTS ix_coaching_cards_agent   ON coaching_cards ("agentId")')
    _exec('CREATE INDEX IF NOT EXISTS ix_coaching_cards_status  ON coaching_cards (status)')

    # ── Indexes on existing tables (idempotent) ───────────────────────────────
    _exec('CREATE INDEX IF NOT EXISTS ix_tenants_api_key   ON tenants ("apiKey")')
    _exec('CREATE INDEX IF NOT EXISTS ix_users_tenant      ON users ("tenantId")')
    _exec('CREATE INDEX IF NOT EXISTS ix_agents_tenant     ON agents ("tenantId")')
    _exec('CREATE INDEX IF NOT EXISTS ix_call_logs_tenant  ON call_logs ("tenantId")')
    _exec('CREATE INDEX IF NOT EXISTS ix_call_logs_agent   ON call_logs ("agentId")')
    _exec('CREATE INDEX IF NOT EXISTS ix_documents_tenant  ON documents ("tenantId")')


def downgrade() -> None:
    # Destructive — only for dev. Production should use point-in-time recovery.
    for table in (
        "coaching_cards", "call_recordings", "ivr_trees", "contacts",
        "campaign_contacts", "campaigns", "webhook_endpoints", "dnd_registry",
        "notifications", "audit_logs", "pipelines", "usage_logs", "voice_prints",
        "onboarding_progress", "agent_versions", "agent_configurations",
        "agent_templates",
    ):
        op.get_bind().execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
