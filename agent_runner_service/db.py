from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Agent runner will prefer an explicit AGENT_RUNNER_DATABASE_URL, but fall
# back to the backend's database environment if available. This allows the
# service to share the canonical backend Postgres DB when configured.
raw_url = os.getenv("AGENT_RUNNER_DATABASE_URL") or os.getenv("BACKEND_DATABASE_URL") or os.getenv("DATABASE_URL")

if raw_url:
    # If the URL references asyncpg (used by the backend async engine), strip
    # the +asyncpg suffix to create a sync driver URL for SQLAlchemy.
    sync_url = raw_url.replace("+asyncpg", "")
else:
    sync_url = "sqlite:///./agent_runner.db"

connect_args = {"check_same_thread": False} if sync_url.startswith("sqlite") else {}

engine = create_engine(sync_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
