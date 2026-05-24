"""Make CallLog.transcript nullable (no default was set, causing INSERT failures).

Revision ID: 0006
Revises: 0005
Create Date: 2025-07-01 00:00:01.000000

Safe to re-run — ALTER uses IF NOT NULL guard via DO block.
"""
from alembic import op


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make transcript nullable so callers that omit it don't get a NOT NULL violation.
    # Existing rows that have NULL values (shouldn't happen, but be safe) get an empty string.
    op.execute("""
        DO $$
        BEGIN
            -- Only alter if the column is currently NOT NULL
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'call_logs'
                  AND column_name = 'transcript'
                  AND is_nullable = 'NO'
            ) THEN
                UPDATE call_logs SET transcript = '' WHERE transcript IS NULL;
                ALTER TABLE call_logs ALTER COLUMN transcript DROP NOT NULL;
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            UPDATE call_logs SET transcript = '' WHERE transcript IS NULL;
            ALTER TABLE call_logs ALTER COLUMN transcript SET NOT NULL;
        END
        $$;
    """)
