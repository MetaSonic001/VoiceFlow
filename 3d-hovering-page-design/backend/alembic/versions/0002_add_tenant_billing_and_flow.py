"""Add missing tenant billing columns and agent flowDefinition

Revision ID: 0002
Revises: 0001_initial
Create Date: 2026-05-08

The initial migration used create_all which only creates new tables. These
columns were added to models.py after the initial schema was created, so
existing databases are missing them.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # ── tenants table: add billing / plan columns ────────────────────────────
    existing_tenant_cols = {col["name"] for col in inspector.get_columns("tenants")}

    if "planType" not in existing_tenant_cols:
        op.add_column(
            "tenants",
            sa.Column("planType", sa.String(), nullable=False, server_default="free"),
        )
    if "planTier" not in existing_tenant_cols:
        op.add_column(
            "tenants",
            sa.Column("planTier", sa.String(), nullable=False, server_default="free"),
        )
    if "stripeCustomerId" not in existing_tenant_cols:
        op.add_column(
            "tenants",
            sa.Column("stripeCustomerId", sa.String(), nullable=True),
        )
    if "stripeSubscriptionId" not in existing_tenant_cols:
        op.add_column(
            "tenants",
            sa.Column("stripeSubscriptionId", sa.String(), nullable=True),
        )
    if "managedMinutesBalance" not in existing_tenant_cols:
        op.add_column(
            "tenants",
            sa.Column("managedMinutesBalance", sa.Integer(), nullable=False, server_default="0"),
        )
    if "pilotPlanEndDate" not in existing_tenant_cols:
        op.add_column(
            "tenants",
            sa.Column("pilotPlanEndDate", sa.DateTime(timezone=True), nullable=True),
        )
    if "totalCallCount" not in existing_tenant_cols:
        op.add_column(
            "tenants",
            sa.Column("totalCallCount", sa.Integer(), nullable=False, server_default="0"),
        )

    # ── agents table: add flowDefinition column ──────────────────────────────
    existing_agent_cols = {col["name"] for col in inspector.get_columns("agents")}

    if "flowDefinition" not in existing_agent_cols:
        op.add_column(
            "agents",
            sa.Column("flowDefinition", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    # Column removal is destructive — no-op intentionally.
    pass
