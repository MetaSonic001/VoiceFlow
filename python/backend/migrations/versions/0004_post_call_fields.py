"""Add post-call action fields to call_logs and agents.

Revision ID: 0004
Revises: 0003
Create Date: 2025-01-01 00:00:00.000000

Idempotent — uses IF NOT EXISTS / type-cast guard so safe to re-run.

New columns on call_logs:
  callSid            TEXT          — Twilio CallSid (e.g. CA...)
  callDirection      TEXT          — "inbound" | "outbound"
  recordingUrl       TEXT          — link to call recording
  extractedVariables JSONB         — output from post_call_actions extraction

New column on agents:
  integrations       JSONB         — per-agent integration config (overrides tenant defaults)
"""
from alembic import op
from sqlalchemy import text

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── call_logs — new columns ───────────────────────────────────────────────
    conn.execute(text('ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS "callSid"            TEXT'))
    conn.execute(text('ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS "callDirection"      TEXT'))
    conn.execute(text('ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS "recordingUrl"       TEXT'))
    conn.execute(text(
        'ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS "extractedVariables" JSONB'
    ))

    # ── agents — integrations column ─────────────────────────────────────────
    conn.execute(text(
        'ALTER TABLE agents ADD COLUMN IF NOT EXISTS integrations JSONB'
    ))

    # ── Index for callSid lookups ─────────────────────────────────────────────
    conn.execute(text(
        'CREATE INDEX IF NOT EXISTS ix_call_logs_call_sid ON call_logs ("callSid")'
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text('DROP INDEX IF EXISTS ix_call_logs_call_sid'))
    conn.execute(text('ALTER TABLE call_logs DROP COLUMN IF EXISTS "callSid"'))
    conn.execute(text('ALTER TABLE call_logs DROP COLUMN IF EXISTS "callDirection"'))
    conn.execute(text('ALTER TABLE call_logs DROP COLUMN IF EXISTS "recordingUrl"'))
    conn.execute(text('ALTER TABLE call_logs DROP COLUMN IF EXISTS "extractedVariables"'))
    conn.execute(text('ALTER TABLE agents    DROP COLUMN IF EXISTS integrations'))
