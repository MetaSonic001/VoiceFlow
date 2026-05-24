"""Add extended agent fields and agent_versions table.

Revision ID: 0001
Revises: 
Create Date: 2025-01-01 00:00:00.000000

This migration is idempotent — all ALTER TABLE statements use
IF NOT EXISTS so it is safe to run against both a fresh database
(created via create_tables.py / init_schema.sql) and an existing one.
"""
from alembic import op
from sqlalchemy import text

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── New columns on agents ──────────────────────────────────────────────
    agent_columns = [
        ('ALTER TABLE agents ADD COLUMN IF NOT EXISTS "telephonyProvider" TEXT DEFAULT \'twilio-gather\''),
        ('ALTER TABLE agents ADD COLUMN IF NOT EXISTS "contextBreakdown" JSONB'),
        ('ALTER TABLE agents ADD COLUMN IF NOT EXISTS "welcomeMessage" TEXT'),
        ('ALTER TABLE agents ADD COLUMN IF NOT EXISTS "postCallActions" JSONB'),
        ('ALTER TABLE agents ADD COLUMN IF NOT EXISTS "languageConfig" JSONB'),
        ('ALTER TABLE agents ADD COLUMN IF NOT EXISTS "callerPersonas" JSONB'),
        ('ALTER TABLE agents ADD COLUMN IF NOT EXISTS "simulationSuite" JSONB'),
        ('ALTER TABLE agents ADD COLUMN IF NOT EXISTS "deploymentReadinessScore" INTEGER'),
        ('ALTER TABLE agents ADD COLUMN IF NOT EXISTS "versionNumber" INTEGER DEFAULT 1'),
    ]
    for stmt in agent_columns:
        conn.execute(text(stmt))

    # ── agent_versions table ───────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS agent_versions (
            id TEXT PRIMARY KEY,
            "agentId" TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            "tenantId" TEXT NOT NULL,
            "versionNumber" INTEGER DEFAULT 1,
            "changeDescription" TEXT,
            snapshot JSONB NOT NULL,
            "createdAt" TIMESTAMPTZ DEFAULT now()
        )
    """))
    conn.execute(text(
        'CREATE INDEX IF NOT EXISTS ix_agent_versions_agent_id ON agent_versions ("agentId")'
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DROP TABLE IF EXISTS agent_versions CASCADE"))
    for col in [
        "telephonyProvider", "contextBreakdown", "welcomeMessage",
        "postCallActions", "languageConfig", "callerPersonas",
        "simulationSuite", "deploymentReadinessScore", "versionNumber",
    ]:
        conn.execute(text(f'ALTER TABLE agents DROP COLUMN IF EXISTS "{col}"'))
