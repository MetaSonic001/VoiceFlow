"""
Adapter to use the backend's SQLAlchemy-managed database as the canonical document store.
If the backend package isn't available at runtime, this adapter is a no-op and callers should
fall back to the existing asyncpg-based storage.
"""
from typing import Optional, Dict, Any
import logging
import sys
import pathlib

logger = logging.getLogger(__name__)


def get_backend_session_and_models():
    try:
        repo_root = pathlib.Path(__file__).resolve().parents[2]
        backend_path = repo_root / 'backend'
        if str(backend_path) not in sys.path and backend_path.exists():
            sys.path.insert(0, str(backend_path))
        # import the SQLAlchemy AsyncSessionLocal and models
        from backend.backend.db import AsyncSessionLocal
        from backend.backend.models import Document as BackendDocument
        return AsyncSessionLocal, BackendDocument
    except Exception:
        return None, None


async def write_document_to_backend(document_id: str, filename: str, content: bytes, file_type: str, metadata: Dict[str, Any], status: str = 'processing') -> bool:
    AsyncSessionLocal, BackendDocument = get_backend_session_and_models()
    if not AsyncSessionLocal or not BackendDocument:
        return False

    try:
        async with AsyncSessionLocal() as session:
            # Create or update the backend document with the canonical id
            # Use plain dict assignment to avoid SQLAlchemy import issues
            doc = BackendDocument(
                id=document_id,
                filename=filename,
                content=content,
                file_type=file_type,
                metadata=metadata,
                status=status
            )
            session.add(doc)
            await session.commit()
        return True
    except Exception:
        logger.exception("Failed to write document to backend DB via adapter")
        return False
