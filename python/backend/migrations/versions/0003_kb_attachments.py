"""Add kb_attachments table and fileType/chunkCount columns to documents.

Revision ID: 0003
Revises: 0002
Create Date: 2025-01-01 00:00:00.000000

Idempotent — uses IF NOT EXISTS / IF NOT EXISTS so safe to re-run.
"""
from alembic import op
from sqlalchemy import text

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── Add new columns to documents ─────────────────────────────────────────
    conn.execute(text('ALTER TABLE documents ADD COLUMN IF NOT EXISTS "fileType"   TEXT'))
    conn.execute(text('ALTER TABLE documents ADD COLUMN IF NOT EXISTS "chunkCount" INTEGER'))

    # ── Create kb_attachments table ───────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS kb_attachments (
            id           TEXT PRIMARY KEY,
            "tenantId"   TEXT NOT NULL REFERENCES tenants(id)   ON DELETE CASCADE,
            "agentId"    TEXT NOT NULL REFERENCES agents(id)    ON DELETE CASCADE,
            "documentId" TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            "whenToUse"  TEXT,
            "chunkCount" INTEGER     DEFAULT 0,
            status       TEXT        DEFAULT 'pending',
            "errorMessage" TEXT,
            "createdAt"  TIMESTAMPTZ DEFAULT now(),
            "updatedAt"  TIMESTAMPTZ DEFAULT now()
        )
    """))

    # ── Indexes ───────────────────────────────────────────────────────────────
    conn.execute(text(
        'CREATE INDEX IF NOT EXISTS ix_kb_attachments_tenant   ON kb_attachments ("tenantId")'
    ))
    conn.execute(text(
        'CREATE INDEX IF NOT EXISTS ix_kb_attachments_agent    ON kb_attachments ("agentId")'
    ))
    conn.execute(text(
        'CREATE INDEX IF NOT EXISTS ix_kb_attachments_document ON kb_attachments ("documentId")'
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DROP TABLE IF EXISTS kb_attachments CASCADE"))
    conn.execute(text('ALTER TABLE documents DROP COLUMN IF EXISTS "fileType"'))
    conn.execute(text('ALTER TABLE documents DROP COLUMN IF EXISTS "chunkCount"'))
