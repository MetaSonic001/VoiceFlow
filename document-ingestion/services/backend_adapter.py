"""
Adapter to use the backend's SQLAlchemy-managed database as the canonical document store.
If the backend package isn't available at runtime, this adapter is a no-op and callers should
fall back to the existing asyncpg-based storage.
"""
from typing import Optional, Dict, Any
import logging
import sys
import pathlib
import asyncio

logger = logging.getLogger(__name__)


def get_backend_session_and_models():
    try:
        repo_root = pathlib.Path(__file__).resolve().parents[2]
        backend_path = repo_root / 'backend'
        backend_backend_path = repo_root / 'backend' / 'backend'
        if str(backend_backend_path) not in sys.path and backend_backend_path.exists():
            sys.path.insert(0, str(backend_backend_path))
        if str(backend_path) not in sys.path and backend_path.exists():
            sys.path.insert(0, str(backend_path))
        # import the SQLAlchemy AsyncSessionLocal and models
        from backend.backend.db import AsyncSessionLocal
        from backend.backend.models import Document as BackendDocument
        return AsyncSessionLocal, BackendDocument
    except Exception:
        return None, None


async def write_document_to_backend(document_id: str, filename: str, content: bytes, file_type: str, metadata: Dict[str, Any], status: str = 'processing') -> bool:
    # For now, disable direct backend writes to avoid event loop conflicts
    # The backend upload endpoint handles document creation
    logger.info(f"Backend adapter write disabled for document {document_id} to avoid event loop conflicts")
    return False


async def update_document_status_backend(document_id: str, status: str, error_message: Optional[str] = None) -> bool:
    # For now, disable direct backend updates to avoid event loop conflicts
    # Use HTTP API instead
    logger.info(f"Backend adapter status update disabled for document {document_id} to avoid event loop conflicts")
    return False
