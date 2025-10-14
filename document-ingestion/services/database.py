"""
Canonical document store for the ingestion pipeline.

This manager uses the backend application's SQLAlchemy-managed database
via backend_adapter. If the backend is not available, document storage fails.
"""

from typing import Dict, Any, Optional, List, Tuple
import logging
import os
from datetime import datetime
import uuid
import json
import asyncio
import pathlib
import base64

logger = logging.getLogger(__name__)

try:
    from .backend_adapter import write_document_to_backend, get_backend_session_and_models
except Exception:
    write_document_to_backend = None
    get_backend_session_and_models = None


class DatabaseManager:
    def __init__(self):
        pass  # No pending directory needed

    async def check_connection(self) -> bool:
        return write_document_to_backend is not None

    async def store_document(self, filename: str, content: bytes, file_type: str, metadata: Dict[str, Any]) -> str:
        document_id = str(uuid.uuid4())
        now = datetime.utcnow()

        if write_document_to_backend:
            try:
                ok = await write_document_to_backend(document_id, filename, content, file_type, metadata, status='processing')
                if ok:
                    logger.info(f"Wrote document {document_id} to backend DB via adapter")
                    return document_id
            except Exception:
                logger.exception('Backend adapter write failed')

        # No fallback - raise exception
        raise Exception("Backend database not available for document storage")

    async def update_document_status(self, document_id: str, status: str, error_message: Optional[str] = None) -> None:
        now = datetime.utcnow()
        if get_backend_session_and_models:
            try:
                AsyncSessionLocal, BackendDocument = get_backend_session_and_models()
                if AsyncSessionLocal and BackendDocument:
                    async with AsyncSessionLocal() as session:
                        doc = await session.get(BackendDocument, document_id)
                        if doc:
                            doc.status = status
                            doc.updated_at = now
                            if error_message:
                                doc.error_message = error_message
                            await session.commit()
                            return
            except Exception:
                logger.exception('Failed to update backend status via adapter')

        # No fallback - just log the failure
        logger.error(f"Could not update status for document {document_id}: backend not available")

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        if get_backend_session_and_models:
            try:
                AsyncSessionLocal, BackendDocument = get_backend_session_and_models()
                if AsyncSessionLocal and BackendDocument:
                    async with AsyncSessionLocal() as session:
                        row = await session.get(BackendDocument, document_id)
                        if row:
                            return {
                                'id': str(row.id),
                                'filename': row.filename,
                                'file_type': row.file_type,
                                'file_size': len(row.content) if row.content else 0,
                                'metadata': row.metadata or {},
                                'created_at': row.created_at.isoformat() if row.created_at else None,
                                'updated_at': row.updated_at.isoformat() if row.updated_at else None,
                                'status': getattr(row, 'status', None),
                                'error_message': getattr(row, 'error_message', None),
                                'content': None,
                                'has_content': bool(row.content)
                            }
            except Exception:
                logger.exception('Backend adapter read failed')

        return None

    async def get_document_content(self, document_id: str) -> Optional[bytes]:
        if get_backend_session_and_models:
            try:
                AsyncSessionLocal, BackendDocument = get_backend_session_and_models()
                if AsyncSessionLocal and BackendDocument:
                    async with AsyncSessionLocal() as session:
                        row = await session.get(BackendDocument, document_id)
                        if row and getattr(row, 'content', None):
                            return row.content
            except Exception:
                logger.exception('Backend adapter content read failed')

        return None

    async def list_documents(self, limit: int = 10, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        if get_backend_session_and_models:
            try:
                AsyncSessionLocal, BackendDocument = get_backend_session_and_models()
                if AsyncSessionLocal and BackendDocument:
                    async with AsyncSessionLocal() as session:
                        # Get total count
                        result = await session.execute("SELECT COUNT(*) FROM documents")
                        total = result.scalar()

                        # Get paginated results
                        result = await session.execute(
                            "SELECT id, filename, file_type, content, metadata, created_at, updated_at, status, error_message FROM documents ORDER BY created_at DESC LIMIT :limit OFFSET :offset",
                            {'limit': limit, 'offset': offset}
                        )
                        rows = result.fetchall()

                        documents = []
                        for row in rows:
                            documents.append({
                                'id': str(row[0]),
                                'filename': row[1],
                                'file_type': row[2],
                                'file_size': len(row[3]) if row[3] else 0,
                                'metadata': row[4] or {},
                                'created_at': row[5].isoformat() if row[5] else None,
                                'updated_at': row[6].isoformat() if row[6] else None,
                                'status': row[7],
                                'error_message': row[8],
                                'content': None,
                                'has_content': bool(row[3])
                            })

                        return documents, total
            except Exception:
                logger.exception('Backend adapter list failed')

        return [], 0

from typing import Dict, Any, Optional, List, Tuple
import logging
import os
from datetime import datetime
import uuid
import json
import asyncio
import pathlib
import base64

logger = logging.getLogger(__name__)

try:
    from .backend_adapter import write_document_to_backend, get_backend_session_and_models
except Exception:
    write_document_to_backend = None
    get_backend_session_and_models = None


class DatabaseManager:
    def __init__(self):
        pass  # No pending directory needed

    async def check_connection(self) -> bool:
        return write_document_to_backend is not None

    async def store_document(self, filename: str, content: bytes, file_type: str, metadata: Dict[str, Any]) -> str:
        document_id = str(uuid.uuid4())
        now = datetime.utcnow()

        if write_document_to_backend:
            try:
                ok = await write_document_to_backend(document_id, filename, content, file_type, metadata, status='processing')
                if ok:
                    logger.info(f"Wrote document {document_id} to backend DB via adapter")
                    return document_id
            except Exception:
                logger.exception('Backend adapter write failed')

        # No fallback - raise exception
        raise Exception("Backend database not available for document storage")

    async def update_document_status(self, document_id: str, status: str, error_message: Optional[str] = None) -> None:
        now = datetime.utcnow()
        if get_backend_session_and_models:
            try:
                AsyncSessionLocal, BackendDocument = get_backend_session_and_models()
                if AsyncSessionLocal and BackendDocument:
                    async with AsyncSessionLocal() as session:
                        doc = await session.get(BackendDocument, document_id)
                        if doc:
                            doc.status = status
                            doc.updated_at = now
                            if error_message:
                                doc.error_message = error_message
                            await session.commit()
                            return
            except Exception:
                logger.exception('Failed to update backend status via adapter')

        # No fallback - just log the failure
        logger.error(f"Could not update status for document {document_id}: backend not available")

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        if get_backend_session_and_models:
            try:
                AsyncSessionLocal, BackendDocument = get_backend_session_and_models()
                if AsyncSessionLocal and BackendDocument:
                    async with AsyncSessionLocal() as session:
                        row = await session.get(BackendDocument, document_id)
                        if row:
                            return {
                                'id': str(row.id),
                                'filename': row.filename,
                                'file_type': row.file_type,
                                'file_size': len(row.content) if row.content else 0,
                                'metadata': row.metadata or {},
                                'created_at': row.created_at.isoformat() if row.created_at else None,
                                'updated_at': row.updated_at.isoformat() if row.updated_at else None,
                                'status': getattr(row, 'status', None),
                                'error_message': getattr(row, 'error_message', None),
                                'content': None,
                                'has_content': bool(row.content)
                            }
            except Exception:
                logger.exception('Backend adapter read failed; falling back')

        p = self._pending_dir / f"{document_id}.json"
        if p.exists():
            with p.open('r', encoding='utf-8') as fh:
                r = json.load(fh)
            return {
                'id': r.get('id'),
                'filename': r.get('filename'),
                'file_type': r.get('file_type'),
                'file_size': r.get('file_size'),
                'metadata': r.get('metadata', {}),
                'created_at': r.get('created_at'),
                'updated_at': r.get('updated_at'),
                'status': r.get('status'),
                'error_message': r.get('error_message'),
                'content': None,
                'has_content': bool(r.get('content_b64'))
            }
        return None

    async def get_document_content(self, document_id: str) -> Optional[bytes]:
        if get_backend_session_and_models:
            try:
                AsyncSessionLocal, BackendDocument = get_backend_session_and_models()
                if AsyncSessionLocal and BackendDocument:
                    async with AsyncSessionLocal() as session:
                        row = await session.get(BackendDocument, document_id)
                        if row and getattr(row, 'content', None):
                            return row.content
            except Exception:
                logger.exception('Backend adapter content read failed; falling back')

        p = self._pending_dir / f"{document_id}.json"
        if p.exists():
            with p.open('r', encoding='utf-8') as fh:
                r = json.load(fh)
            b64 = r.get('content_b64')
            if b64:
                return base64.b64decode(b64)
        return None

    async def list_documents(self, limit: int = 10, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        if get_backend_session_and_models:
            try:
                AsyncSessionLocal, BackendDocument = get_backend_session_and_models()
                if AsyncSessionLocal and BackendDocument:
                    async with AsyncSessionLocal() as session:
                        q = await session.execute(f"SELECT id, filename, file_type, content IS NOT NULL as has_content, metadata, created_at, updated_at, status, error_message FROM {BackendDocument.__tablename__} ORDER BY created_at DESC LIMIT :limit OFFSET :offset", {'limit': limit, 'offset': offset})
                        rows = q.fetchall()
                        documents = []
                        for r in rows:
                            documents.append({
                                'id': str(r[0]),
                                'filename': r[1],
                                'file_type': r[2],
                                'file_size': None,
                                'metadata': r[4] or {},
                                'created_at': r[5].isoformat() if r[5] else None,
                                'updated_at': r[6].isoformat() if r[6] else None,
                                'status': r[7],
                                'error_message': r[8],
                                'content': None,
                                'has_content': bool(r[3])
                            })
                        qc = await session.execute(f"SELECT count(*) FROM {BackendDocument.__tablename__}")
                        total = qc.scalar() or 0
                        return documents, int(total)
            except Exception:
                logger.exception('Backend adapter list failed; falling back')

        files = sorted(self._pending_dir.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
        total = len(files)
        docs = []
        for p in files[offset: offset + limit]:
            try:
                with p.open('r', encoding='utf-8') as fh:
                    r = json.load(fh)
                docs.append({
                    'id': r.get('id'),
                    'filename': r.get('filename'),
                    'file_type': r.get('file_type'),
                    'file_size': r.get('file_size'),
                    'metadata': r.get('metadata', {}),
                    'created_at': r.get('created_at'),
                    'updated_at': r.get('updated_at'),
                    'status': r.get('status'),
                    'error_message': r.get('error_message'),
                    'content': None,
                    'has_content': bool(r.get('content_b64'))
                })
            except Exception:
                logger.exception(f'Failed to read pending file {p}')
        return docs, total

    async def delete_document(self, document_id: str) -> None:
        if get_backend_session_and_models:
            try:
                AsyncSessionLocal, BackendDocument = get_backend_session_and_models()
                if AsyncSessionLocal and BackendDocument:
                    async with AsyncSessionLocal() as session:
                        row = await session.get(BackendDocument, document_id)
                        if row:
                            await session.delete(row)
                            await session.commit()
                            return
            except Exception:
                logger.exception('Failed to delete via backend adapter; falling back')

        p = self._pending_dir / f"{document_id}.json"
        if p.exists():
            try:
                p.unlink()
            except Exception:
                logger.exception('Failed to delete pending file')

    async def flush_pending_documents(self, batch_size: int = 10) -> int:
        flushed = 0
        files = sorted(self._pending_dir.glob('*.json'), key=lambda p: p.stat().st_mtime)
        for p in files[:batch_size]:
            try:
                with p.open('r', encoding='utf-8') as fh:
                    r = json.load(fh)
                doc_id = r.get('id')
                content_b64 = r.get('content_b64')
                if not content_b64:
                    p.unlink()
                    continue
                content = base64.b64decode(content_b64)
                if write_document_to_backend:
                    ok = await write_document_to_backend(doc_id, r.get('filename'), content, r.get('file_type'), r.get('metadata', {}), status=r.get('status', 'processing'))
                    if ok:
                        try:
                            p.unlink()
                        except Exception:
                            logger.exception('Failed to remove pending file after flush')
                        flushed += 1
            except Exception:
                logger.exception(f'Failed to flush pending file {p}')
        if flushed:
            logger.info(f'Flushed {flushed} pending documents via backend adapter')
        return flushed
"""
Keep a small, filesystem-first DatabaseManager for document-ingestion.

This file intentionally avoids depending on asyncpg or a separate Postgres
client. The ingestion code should prefer writing to the backend SQLAlchemy
database via the `backend_adapter` when available; otherwise it persists
pending documents to disk for later flushing.
"""

from typing import Dict, Any, Optional, List, Tuple
import logging
import os
from datetime import datetime
import uuid
import json
import asyncio
import pathlib
import base64

logger = logging.getLogger(__name__)

try:
    from .backend_adapter import write_document_to_backend, get_backend_session_and_models
except Exception:
    write_document_to_backend = None
    get_backend_session_and_models = None


class DatabaseManager:
    def __init__(self):
        # Use absolute path based on this module's location, not current working directory
        module_dir = pathlib.Path(__file__).parent.parent  # document-ingestion directory
        self._pending_dir = module_dir / 'pending_documents'
        try:
            self._pending_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    async def check_connection(self) -> bool:
        return write_document_to_backend is not None

    async def store_document(self, filename: str, content: bytes, file_type: str, metadata: Dict[str, Any]) -> str:
        document_id = str(uuid.uuid4())
        now = datetime.utcnow()

        if write_document_to_backend:
            try:
                ok = await write_document_to_backend(document_id, filename, content, file_type, metadata, status='processing')
                if ok:
                    logger.info(f"Wrote document {document_id} to backend DB via adapter")
                    return document_id
            except Exception:
                logger.exception('Backend adapter write failed; falling back to pending dir')

        # Fallback to disk
        payload = {
            'id': document_id,
            'filename': filename,
            'file_type': file_type,
            'file_size': len(content),
            'metadata': metadata,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
            'status': 'pending'
        }
        out_path = self._pending_dir / f"{document_id}.json"
        with out_path.open('w', encoding='utf-8') as fh:
            record = payload.copy()
            record['content_b64'] = base64.b64encode(content).decode('ascii')
            json.dump(record, fh)
        logger.info(f"Wrote pending document {document_id} to {out_path}")
        return document_id

    async def update_document_status(self, document_id: str, status: str, error_message: Optional[str] = None) -> None:
        now = datetime.utcnow()
        if get_backend_session_and_models:
            try:
                AsyncSessionLocal, BackendDocument = get_backend_session_and_models()
                if AsyncSessionLocal and BackendDocument:
                    async with AsyncSessionLocal() as session:
                        doc = await session.get(BackendDocument, document_id)
                        if doc:
                            doc.status = status
                            doc.updated_at = now
                            if error_message:
                                doc.error_message = error_message
                            await session.commit()
                            return
            except Exception:
                logger.exception('Failed to update backend status via adapter; falling back to pending file')

        try:
            p = self._pending_dir / f"{document_id}.json"
            if p.exists():
                with p.open('r', encoding='utf-8') as fh:
                    r = json.load(fh)
                r['status'] = status
                r['updated_at'] = now.isoformat()
                if error_message:
                    r['error_message'] = error_message
                with p.open('w', encoding='utf-8') as fh:
                    json.dump(r, fh)
        except Exception:
            logger.exception('Failed to update pending file status')

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        if get_backend_session_and_models:
            try:
                AsyncSessionLocal, BackendDocument = get_backend_session_and_models()
                if AsyncSessionLocal and BackendDocument:
                    async with AsyncSessionLocal() as session:
                        row = await session.get(BackendDocument, document_id)
                        if row:
                            return {
                                'id': str(row.id),
                                'filename': row.filename,
                                'file_type': row.file_type,
                                'file_size': len(row.content) if row.content else 0,
                                'metadata': row.metadata or {},
                                'created_at': row.created_at.isoformat() if row.created_at else None,
                                'updated_at': row.updated_at.isoformat() if row.updated_at else None,
                                'status': getattr(row, 'status', None),
                                'error_message': getattr(row, 'error_message', None),
                                'content': None,
                                'has_content': bool(row.content)
                            }
            except Exception:
                logger.exception('Backend adapter read failed; falling back')

        p = self._pending_dir / f"{document_id}.json"
        if p.exists():
            with p.open('r', encoding='utf-8') as fh:
                r = json.load(fh)
            return {
                'id': r.get('id'),
                'filename': r.get('filename'),
                'file_type': r.get('file_type'),
                'file_size': r.get('file_size'),
                'metadata': r.get('metadata', {}),
                'created_at': r.get('created_at'),
                'updated_at': r.get('updated_at'),
                'status': r.get('status'),
                'error_message': r.get('error_message'),
                'content': None,
                'has_content': bool(r.get('content_b64'))
            }
        return None

    async def get_document_content(self, document_id: str) -> Optional[bytes]:
        if get_backend_session_and_models:
            try:
                AsyncSessionLocal, BackendDocument = get_backend_session_and_models()
                if AsyncSessionLocal and BackendDocument:
                    async with AsyncSessionLocal() as session:
                        row = await session.get(BackendDocument, document_id)
                        if row and getattr(row, 'content', None):
                            return row.content
            except Exception:
                logger.exception('Backend adapter content read failed; falling back')

        p = self._pending_dir / f"{document_id}.json"
        if p.exists():
            with p.open('r', encoding='utf-8') as fh:
                r = json.load(fh)
            b64 = r.get('content_b64')
            if b64:
                return base64.b64decode(b64)
        return None

    async def list_documents(self, limit: int = 10, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        if get_backend_session_and_models:
            try:
                AsyncSessionLocal, BackendDocument = get_backend_session_and_models()
                if AsyncSessionLocal and BackendDocument:
                    async with AsyncSessionLocal() as session:
                        q = await session.execute(f"SELECT id, filename, file_type, content IS NOT NULL as has_content, metadata, created_at, updated_at, status, error_message FROM {BackendDocument.__tablename__} ORDER BY created_at DESC LIMIT :limit OFFSET :offset", {'limit': limit, 'offset': offset})
                        rows = q.fetchall()
                        documents = []
                        for r in rows:
                            documents.append({
                                'id': str(r[0]),
                                'filename': r[1],
                                'file_type': r[2],
                                'file_size': None,
                                'metadata': r[4] or {},
                                'created_at': r[5].isoformat() if r[5] else None,
                                'updated_at': r[6].isoformat() if r[6] else None,
                                'status': r[7],
                                'error_message': r[8],
                                'content': None,
                                'has_content': bool(r[3])
                            })
                        qc = await session.execute(f"SELECT count(*) FROM {BackendDocument.__tablename__}")
                        total = qc.scalar() or 0
                        return documents, int(total)
            except Exception:
                logger.exception('Backend adapter list failed; falling back')

        files = sorted(self._pending_dir.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
        total = len(files)
        docs = []
        for p in files[offset: offset + limit]:
            try:
                with p.open('r', encoding='utf-8') as fh:
                    r = json.load(fh)
                docs.append({
                    'id': r.get('id'),
                    'filename': r.get('filename'),
                    'file_type': r.get('file_type'),
                    'file_size': r.get('file_size'),
                    'metadata': r.get('metadata', {}),
                    'created_at': r.get('created_at'),
                    'updated_at': r.get('updated_at'),
                    'status': r.get('status'),
                    'error_message': r.get('error_message'),
                    'content': None,
                    'has_content': bool(r.get('content_b64'))
                })
            except Exception:
                logger.exception(f'Failed to read pending file {p}')
        return docs, total

    async def delete_document(self, document_id: str) -> None:
        if get_backend_session_and_models:
            try:
                AsyncSessionLocal, BackendDocument = get_backend_session_and_models()
                if AsyncSessionLocal and BackendDocument:
                    async with AsyncSessionLocal() as session:
                        row = await session.get(BackendDocument, document_id)
                        if row:
                            await session.delete(row)
                            await session.commit()
                            return
            except Exception:
                logger.exception('Failed to delete via backend adapter; falling back')

        p = self._pending_dir / f"{document_id}.json"
        if p.exists():
            try:
                p.unlink()
            except Exception:
                logger.exception('Failed to delete pending file')

    async def flush_pending_documents(self, batch_size: int = 10) -> int:
        flushed = 0
        files = sorted(self._pending_dir.glob('*.json'), key=lambda p: p.stat().st_mtime)
        for p in files[:batch_size]:
            try:
                with p.open('r', encoding='utf-8') as fh:
                    r = json.load(fh)
                doc_id = r.get('id')
                content_b64 = r.get('content_b64')
                if not content_b64:
                    p.unlink()
                    continue
                content = base64.b64decode(content_b64)
                if write_document_to_backend:
                    ok = await write_document_to_backend(doc_id, r.get('filename'), content, r.get('file_type'), r.get('metadata', {}), status=r.get('status', 'processing'))
                    if ok:
                        try:
                            p.unlink()
                        except Exception:
                            logger.exception('Failed to remove pending file after flush')
                        flushed += 1
            except Exception:
                logger.exception(f'Failed to flush pending file {p}')
        if flushed:
            logger.info(f'Flushed {flushed} pending documents via backend adapter')
        return flushed
