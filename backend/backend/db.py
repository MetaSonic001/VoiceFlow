from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import AsyncEngine
from contextlib import asynccontextmanager
import os
from typing import Optional, AsyncGenerator
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('BACKEND_DATABASE_URL') or os.getenv('DATABASE_URL') or 'postgresql+asyncpg://doc_user:doc_password@localhost:5433/documents_db'

# Lazily created engine and sessionmaker so importing this module doesn't
# immediately attempt to import the async DB driver (asyncpg). The engine
# will be created on first call to get_session().
_engine: Optional[AsyncEngine] = None
_SessionMaker: Optional[sessionmaker] = None

Base = declarative_base()


def _ensure_engine_and_maker() -> None:
    global _engine, _SessionMaker
    if _engine is None:
        _engine = create_async_engine(DATABASE_URL, future=True, echo=False)
    if _SessionMaker is None:
        _SessionMaker = sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    _ensure_engine_and_maker()
    async with _SessionMaker() as session:  # type: ignore[misc]
        yield session


def AsyncSessionLocal():
    """Compatibility factory so existing code using
    `async with AsyncSessionLocal() as session:` continues to work.
    This will ensure the engine/sessionmaker are created lazily.
    """
    _ensure_engine_and_maker()
    return _SessionMaker()  # type: ignore[return-value]
