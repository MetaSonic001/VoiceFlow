"""Simple DB initialization script for local development.

Usage: python -m backend.init_db
This will create tables for the SQLAlchemy models defined in backend.models
using the SQLAlchemy engine configured in backend.db.
"""
import asyncio
import os
from . import db
from .models import Tenant, Agent, Document, User, PipelineAgent, Pipeline


def create_tables():
    # ensure engine is created
    db._ensure_engine_and_maker()
    if db._engine is None:
        raise RuntimeError('Engine not initialized')

    async def _create():
        async with db._engine.begin() as conn:
            await conn.run_sync(db.Base.metadata.create_all)

    asyncio.run(_create())


if __name__ == '__main__':
    create_tables()
    print('Database tables created (if DB reachable).')
