"""Initial schema — all tables from app.models

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use CREATE TABLE IF NOT EXISTS pattern so re-running is idempotent.
    # All tables are defined in app.models; alembic autogenerate would produce
    # the same DDL.  We delegate to SQLAlchemy metadata create_all for the
    # initial migration so the revision stays readable.
    from app.models import Base
    from sqlalchemy import inspect
    from alembic import op as _op
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = set(inspector.get_table_names())
    Base.metadata.create_all(bind=bind, tables=[
        t for t in Base.metadata.sorted_tables if t.name not in existing
    ])


def downgrade() -> None:
    # Dropping all tables is destructive; require explicit confirmation in
    # production.  No-op in migration context.
    pass
