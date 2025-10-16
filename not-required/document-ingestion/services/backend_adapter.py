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
        from backend.db import AsyncSessionLocal
        from backend.models import Document as BackendDocument
        return AsyncSessionLocal, BackendDocument
    except Exception as e:
        logger.exception(f"Failed to get backend session and models: {e}")
        return None, None


async def write_document_to_backend(document_id: str, filename: str, content: bytes, file_type: str, metadata: Dict[str, Any], tenant_id: Optional[str], agent_id: Optional[str], status: str = 'processing') -> bool:
    try:
        AsyncSessionLocal, BackendDocument = get_backend_session_and_models()
        if not AsyncSessionLocal or not BackendDocument:
            logger.error("Backend session/models not available")
            return False

        async with AsyncSessionLocal() as session:
            # Create document record
            # Convert "standalone" strings to None for database storage
            db_tenant_id = None if tenant_id == 'standalone' else tenant_id
            db_agent_id = None if agent_id == 'documents' else agent_id
            
            doc = BackendDocument(
                id=document_id,
                agent_id=db_agent_id,
                tenant_id=db_tenant_id,
                filename=filename,
                file_path="",  # Will be set by backend upload if needed
                file_type=file_type,
                content=content,
                doc_metadata=metadata,
                status=status
            )
            session.add(doc)
            await session.commit()
            logger.info(f"Created document {document_id} in backend DB")
            return True
    except Exception as e:
        logger.exception(f"Failed to write document {document_id} to backend")
        return False


async def update_document_status_backend(document_id: str, status: str, error_message: Optional[str] = None) -> bool:
    # For now, disable direct backend updates to avoid event loop conflicts
    # Use HTTP API instead
    logger.info(f"Backend adapter status update disabled for document {document_id} to avoid event loop conflicts")
    return False
