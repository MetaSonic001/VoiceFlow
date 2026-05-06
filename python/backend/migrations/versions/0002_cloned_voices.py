"""Add cloned_voices table.

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-01 00:00:00.000000

Idempotent — CREATE TABLE IF NOT EXISTS so safe to re-run.
"""
from alembic import op
from sqlalchemy import text

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS cloned_voices (
            id TEXT PRIMARY KEY,
            "tenantId" TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            "userId" TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL,
            "languageCode" TEXT NOT NULL DEFAULT 'en-IN',
            "languageName" TEXT,
            "referenceAudioKey" TEXT NOT NULL,
            "durationSecs" DOUBLE PRECISION,
            status TEXT NOT NULL DEFAULT 'ready',
            "errorMessage" TEXT,
            "createdAt" TIMESTAMPTZ DEFAULT now(),
            "updatedAt" TIMESTAMPTZ DEFAULT now()
        )
    """))
    conn.execute(text(
        'CREATE INDEX IF NOT EXISTS ix_cloned_voices_tenant_id ON cloned_voices ("tenantId")'
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DROP TABLE IF EXISTS cloned_voices CASCADE"))
