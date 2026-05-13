"""
Idempotent ALTER TABLE … ADD COLUMN IF NOT EXISTS for existing Postgres DBs.

SQLAlchemy create_all() creates missing tables but does not add new columns to
tables that already exist. These patches mirror Alembic revisions where applicable.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


# Statements must be safe to run repeatedly (IF NOT EXISTS).
COLUMN_PATCH_SQL: tuple[str, ...] = (
    # tenants — billing / plan fields (added after initial schema)
    'ALTER TABLE tenants ADD COLUMN IF NOT EXISTS "planType" TEXT NOT NULL DEFAULT \'free\'',
    'ALTER TABLE tenants ADD COLUMN IF NOT EXISTS "planTier" TEXT NOT NULL DEFAULT \'free\'',
    'ALTER TABLE tenants ADD COLUMN IF NOT EXISTS "stripeCustomerId" TEXT',
    'ALTER TABLE tenants ADD COLUMN IF NOT EXISTS "stripeSubscriptionId" TEXT',
    'ALTER TABLE tenants ADD COLUMN IF NOT EXISTS "managedMinutesBalance" INTEGER NOT NULL DEFAULT 0',
    'ALTER TABLE tenants ADD COLUMN IF NOT EXISTS "pilotPlanEndDate" TIMESTAMPTZ',
    'ALTER TABLE tenants ADD COLUMN IF NOT EXISTS "totalCallCount" INTEGER NOT NULL DEFAULT 0',
    # agents — flow definition JSON
    'ALTER TABLE agents ADD COLUMN IF NOT EXISTS "flowDefinition" JSONB',
    # agents — per-agent integration overrides (Alembic 0004)
    'ALTER TABLE agents ADD COLUMN IF NOT EXISTS "integrations" JSONB',
    # call_logs — Twilio / post-call fields (Alembic 0004)
    'ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS "callSid" TEXT',
    'ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS "callDirection" TEXT',
    'ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS "recordingUrl" TEXT',
    'ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS "extractedVariables" JSONB',
    'ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS "voicemailDetected" BOOLEAN NOT NULL DEFAULT false',
    'CREATE INDEX IF NOT EXISTS ix_call_logs_call_sid ON call_logs ("callSid")',
    # users — password hash
    'ALTER TABLE users ADD COLUMN IF NOT EXISTS "passwordHash" TEXT',
    # documents — KB metadata (Alembic 0003)
    'ALTER TABLE documents ADD COLUMN IF NOT EXISTS "fileType" TEXT',
    'ALTER TABLE documents ADD COLUMN IF NOT EXISTS "chunkCount" INTEGER',
    # campaigns — evolved past migrations/versions/0005_missing_models_and_auth.py (create_all skips ALTER)
    'ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS "webhookUrl" TEXT',
    'ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS "allowedCallHours" JSONB',
    'ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS "timezone" TEXT NOT NULL DEFAULT \'UTC\'',
    'ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS "maxRetries" INTEGER NOT NULL DEFAULT 3',
    'ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS "voicemailAction" TEXT NOT NULL DEFAULT \'hangup\'',
    'ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS "voicemailMessage" TEXT',
    'ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS "dialedCount" INTEGER NOT NULL DEFAULT 0',
    'ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS "answeredCount" INTEGER NOT NULL DEFAULT 0',
    'ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS "machinedCount" INTEGER NOT NULL DEFAULT 0',
    'ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS "failedCount" INTEGER NOT NULL DEFAULT 0',
    # campaign_contacts — legacy table used `phone` / `attemptedAt`; models use phoneNumber / lastCalledAt
    """
    DO $$
    BEGIN
      IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = 'campaign_contacts'
          AND column_name = 'phone'
      ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = 'campaign_contacts'
          AND column_name = 'phoneNumber'
      ) THEN
        ALTER TABLE campaign_contacts RENAME COLUMN phone TO "phoneNumber";
      END IF;
    END $$;
    """,
    'ALTER TABLE campaign_contacts ADD COLUMN IF NOT EXISTS "phoneNumber" TEXT',
    'ALTER TABLE campaign_contacts ADD COLUMN IF NOT EXISTS "callAttempts" INTEGER NOT NULL DEFAULT 0',
    'ALTER TABLE campaign_contacts ADD COLUMN IF NOT EXISTS "lastCallSid" TEXT',
    'ALTER TABLE campaign_contacts ADD COLUMN IF NOT EXISTS "lastCalledAt" TIMESTAMPTZ',
    'ALTER TABLE campaign_contacts ADD COLUMN IF NOT EXISTS "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT NOW()',
    """
    DO $$
    BEGIN
      IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = 'campaign_contacts'
          AND column_name = 'attemptedAt'
      ) AND EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = 'campaign_contacts'
          AND column_name = 'lastCalledAt'
      ) THEN
        UPDATE campaign_contacts SET "lastCalledAt" = "attemptedAt" WHERE "lastCalledAt" IS NULL;
      END IF;
    END $$;
    """,
)


async def apply_column_patches(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        for stmt in COLUMN_PATCH_SQL:
            await conn.execute(text(stmt.strip()))
