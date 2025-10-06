"""
Database Service backed by local PostgreSQL (Docker) using asyncpg.
The service will create the required table on first connection if it doesn't
exist and exposes the async methods used throughout the ingestion service.
"""

from typing import Dict, Any, Optional, List, Tuple
import logging
import os
from datetime import datetime
import uuid
import json
import asyncpg
import asyncio
import pathlib
import base64

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Async PostgreSQL-backed manager for storing documents and metadata.
    Environment variables used to configure the connection:
      POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
    """

    def __init__(self):
        # Connection info (use sensible defaults for local docker)
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = os.getenv("POSTGRES_DB", "documents_db")
        self.user = os.getenv("POSTGRES_USER", "doc_user")
        self.password = os.getenv("POSTGRES_PASSWORD", "doc_password")

        # asyncpg pool (created lazily)
        self._pool: Optional[asyncpg.pool.Pool] = None

        # Fallback directory for storing documents when Postgres is unavailable.
        # This avoids hard failures during local development when Postgres isn't running.
        self._fallback_pending_dir = pathlib.Path(os.getenv('PENDING_DOCS_DIR', './pending_documents'))
        self._fallback = False
        # ensure dir exists (create lazily too)
        try:
            self._fallback_pending_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # if creation fails, we'll attempt again later when writing
            pass

        # Table name
        self.table_name = "documents"

    async def _ensure_pool(self):
        if self._pool:
            return
        dsn = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        logger.info(f"Connecting to Postgres at {self.host}:{self.port} db={self.database}")
        try:
            self._pool = await asyncpg.create_pool(dsn, min_size=1, max_size=4)
            # Create table if missing
            async with self._pool.acquire() as conn:
                await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id TEXT PRIMARY KEY,
                    filename TEXT,
                    file_type TEXT,
                    file_size BIGINT,
                    content BYTEA,
                    metadata JSONB,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    status TEXT,
                    error_message TEXT
                );
                """)
            logger.info("Postgres connection pool created and table ensured")
            # If we successfully connected, ensure fallback flag is off
            self._fallback = False
        except Exception as e:
            # Instead of raising here (which bubbles to the ingestion flow),
            # log and enable a local filesystem fallback so ingestion can continue
            logger.error(f"Failed to create Postgres pool: {e}", exc_info=True)
            logger.warning("Enabling local filesystem fallback for document storage (pending_documents)")
            self._pool = None
            self._fallback = True
            try:
                self._fallback_pending_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                logger.exception("Failed to ensure pending documents directory")

    async def check_connection(self) -> bool:
        try:
            await self._ensure_pool()
            async with self._pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Postgres connection check failed: {e}")
            return False

    async def store_document(
        self,
        filename: str,
        content: bytes,
        file_type: str,
        metadata: Dict[str, Any]
    ) -> str:
        # Try to ensure a Postgres pool; if that fails, _ensure_pool marks self._fallback
        try:
            await self._ensure_pool()
        except Exception:
            # _ensure_pool handles fallback flag and logs
            pass

        document_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # If fallback mode is active, write document to filesystem for later ingestion
        if self._fallback or self._pool is None:
            try:
                # Prepare payload
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
                # Write JSON file with base64 content to avoid binary file problems
                out_path = self._fallback_pending_dir / f"{document_id}.json"
                with out_path.open('w', encoding='utf-8') as fh:
                    record = payload.copy()
                    record['content_b64'] = base64.b64encode(content).decode('ascii')
                    json.dump(record, fh)

                logger.info(f"Document {document_id} written to fallback dir {out_path}")
                return document_id
            except Exception as e:
                logger.exception(f"Failed to write document to fallback dir: {e}")
                raise

        # Otherwise, write to Postgres as before
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    f"INSERT INTO {self.table_name} (id, filename, file_type, file_size, content, metadata, created_at, updated_at, status) "
                    f"VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9)",
                    document_id,
                    filename,
                    file_type,
                    len(content),
                    content,
                    json.dumps(metadata),
                    now,
                    now,
                    "processing",
                )

            logger.info(f"Document {document_id} stored in Postgres")
            return document_id
        except Exception as e:
            logger.error(f"Error storing document in Postgres: {e}", exc_info=True)
            # As a last resort, fallback to filesystem storage
            try:
                out_path = self._fallback_pending_dir / f"{document_id}.json"
                record = {
                    'id': document_id,
                    'filename': filename,
                    'file_type': file_type,
                    'file_size': len(content),
                    'metadata': metadata,
                    'created_at': now.isoformat(),
                    'updated_at': now.isoformat(),
                    'status': 'pending',
                    'content_b64': base64.b64encode(content).decode('ascii')
                }
                with out_path.open('w', encoding='utf-8') as fh:
                    json.dump(record, fh)
                logger.info(f"Document {document_id} written to fallback dir after Postgres error")
                # Mark fallback mode on so subsequent operations know
                self._fallback = True
                return document_id
            except Exception:
                logger.exception("Failed to persist document in fallback after Postgres error")
                raise

    async def update_document_status(
        self,
        document_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        now = datetime.utcnow()

        # If using fallback, update the JSON file if present
        if self._fallback or self._pool is None:
            try:
                path = self._fallback_pending_dir / f"{document_id}.json"
                if path.exists():
                    with path.open('r', encoding='utf-8') as fh:
                        record = json.load(fh)
                    record['status'] = status
                    record['updated_at'] = now.isoformat()
                    if error_message:
                        record['error_message'] = error_message
                    with path.open('w', encoding='utf-8') as fh:
                        json.dump(record, fh)
                    logger.info(f"Fallback record {document_id} updated with status {status}")
                    return
                else:
                    logger.warning(f"Fallback record {document_id} not found to update status")
                    return
            except Exception:
                logger.exception("Failed to update fallback record status")
                return

        # Otherwise update Postgres
        try:
            await self._ensure_pool()
            async with self._pool.acquire() as conn:
                if error_message:
                    await conn.execute(
                        f"UPDATE {self.table_name} SET status=$1, updated_at=$2, error_message=$3 WHERE id=$4",
                        status,
                        now,
                        error_message,
                        document_id,
                    )
                else:
                    await conn.execute(
                        f"UPDATE {self.table_name} SET status=$1, updated_at=$2 WHERE id=$3",
                        status,
                        now,
                        document_id,
                    )
            logger.info(f"Document {document_id} status updated to {status}")
        except Exception as e:
            logger.error(f"Error updating document status: {e}", exc_info=True)

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        # Fallback to filesystem when Postgres unavailable
        if self._fallback or self._pool is None:
            try:
                path = self._fallback_pending_dir / f"{document_id}.json"
                if not path.exists():
                    logger.warning(f"Fallback document {document_id} not found")
                    return None
                with path.open('r', encoding='utf-8') as fh:
                    record = json.load(fh)
                # Map to expected fields
                doc = {
                    'id': record.get('id'),
                    'filename': record.get('filename'),
                    'file_type': record.get('file_type'),
                    'file_size': record.get('file_size'),
                    'metadata': record.get('metadata', {}),
                    'created_at': record.get('created_at'),
                    'updated_at': record.get('updated_at'),
                    'status': record.get('status'),
                    'error_message': record.get('error_message'),
                    'content': None,
                    'has_content': bool(record.get('content_b64'))
                }
                return doc
            except Exception:
                logger.exception("Failed to read fallback document record")
                return None

        # Otherwise read from Postgres
        try:
            await self._ensure_pool()
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"SELECT id, filename, file_type, file_size, metadata, created_at, updated_at, status, error_message, content IS NOT NULL as has_content FROM {self.table_name} WHERE id=$1",
                    document_id,
                )

            if not row:
                logger.warning(f"Document {document_id} not found in Postgres")
                return None

            doc = dict(row)
            # Avoid returning actual content
            doc["content"] = None
            # Ensure metadata is parsed
            if isinstance(doc.get("metadata"), str):
                try:
                    doc["metadata"] = json.loads(doc["metadata"]) if doc["metadata"] else {}
                except Exception:
                    doc["metadata"] = {}

            return doc
        except Exception as e:
            logger.error(f"Error retrieving document from Postgres: {e}", exc_info=True)
            raise

    async def get_document_content(self, document_id: str) -> Optional[bytes]:
        # Fallback: read from filesystem
        if self._fallback or self._pool is None:
            try:
                path = self._fallback_pending_dir / f"{document_id}.json"
                if not path.exists():
                    return None
                with path.open('r', encoding='utf-8') as fh:
                    record = json.load(fh)
                b64 = record.get('content_b64')
                if not b64:
                    return None
                return base64.b64decode(b64)
            except Exception:
                logger.exception("Failed to read fallback document content")
                return None

        try:
            await self._ensure_pool()
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(f"SELECT content FROM {self.table_name} WHERE id=$1", document_id)

            if not row:
                return None

            return row["content"]
        except Exception as e:
            logger.error(f"Error retrieving document content from Postgres: {e}", exc_info=True)
            raise

    async def list_documents(self, limit: int = 10, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        # If fallback, list JSON files in pending dir
        if self._fallback or self._pool is None:
            try:
                docs = []
                files = sorted(self._fallback_pending_dir.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
                total = len(files)
                for p in files[offset: offset + limit]:
                    try:
                        with p.open('r', encoding='utf-8') as fh:
                            rec = json.load(fh)
                        d = {
                            'id': rec.get('id'),
                            'filename': rec.get('filename'),
                            'file_type': rec.get('file_type'),
                            'file_size': rec.get('file_size'),
                            'metadata': rec.get('metadata', {}),
                            'created_at': rec.get('created_at'),
                            'updated_at': rec.get('updated_at'),
                            'status': rec.get('status'),
                            'error_message': rec.get('error_message'),
                            'content': None,
                            'has_content': bool(rec.get('content_b64'))
                        }
                        docs.append(d)
                    except Exception:
                        logger.exception(f"Failed to read fallback record {p}")
                return docs, total
            except Exception:
                logger.exception("Failed to list fallback documents")
                return [], 0

        # Otherwise query Postgres
        try:
            await self._ensure_pool()
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    f"SELECT id, filename, file_type, file_size, metadata, created_at, updated_at, status, error_message, content IS NOT NULL as has_content "
                    f"FROM {self.table_name} ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                    limit,
                    offset,
                )
                count_row = await conn.fetchrow(f"SELECT count(*)::int as cnt FROM {self.table_name}")

            documents = []
            for r in rows:
                d = dict(r)
                d["content"] = None
                if isinstance(d.get("metadata"), str):
                    try:
                        d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else {}
                    except Exception:
                        d["metadata"] = {}
                documents.append(d)

            total = count_row["cnt"] if count_row else 0
            return documents, total
        except Exception as e:
            logger.error(f"Failed to list documents from Postgres: {e}", exc_info=True)
            raise

    async def delete_document(self, document_id: str) -> None:
        # Fallback: delete json file
        if self._fallback or self._pool is None:
            try:
                p = self._fallback_pending_dir / f"{document_id}.json"
                if p.exists():
                    p.unlink()
                    logger.info(f"Deleted fallback document {document_id}")
                else:
                    logger.warning(f"Fallback document {document_id} not found for deletion")
                return
            except Exception:
                logger.exception("Failed to delete fallback document")
                raise

        try:
            await self._ensure_pool()
            async with self._pool.acquire() as conn:
                result = await conn.execute(f"DELETE FROM {self.table_name} WHERE id=$1", document_id)

            logger.info(f"Deleted document {document_id} from Postgres")
        except Exception as e:
            logger.error(f"Failed to delete document {document_id} from Postgres: {e}", exc_info=True)
            raise

    async def flush_pending_documents(self, batch_size: int = 10) -> int:
        """Attempt to flush pending JSON-stored documents into Postgres.

        Returns the number of documents successfully flushed.
        This is safe to call repeatedly; successful flush removes the pending file.
        """
        flushed = 0
        try:
            # Try to (re)establish Postgres connection
            await self._ensure_pool()
        except Exception:
            logger.warning("Cannot flush pending documents because Postgres is still unavailable")
            return flushed

        if self._pool is None:
            logger.warning("Postgres pool not available; aborting flush")
            return flushed

        files = sorted(self._fallback_pending_dir.glob('*.json'), key=lambda p: p.stat().st_mtime)
        if not files:
            return 0

        async with self._pool.acquire() as conn:
            for p in files[:batch_size]:
                try:
                    with p.open('r', encoding='utf-8') as fh:
                        rec = json.load(fh)
                    doc_id = rec.get('id') or str(uuid.uuid4())
                    filename = rec.get('filename', f'pending_{doc_id}')
                    file_type = rec.get('file_type', 'unknown')
                    content_b64 = rec.get('content_b64')
                    metadata = rec.get('metadata', {})
                    created_at = rec.get('created_at')
                    updated_at = rec.get('updated_at')

                    if not content_b64:
                        logger.warning(f"Skipping pending {p} - no content_b64")
                        # remove or mark? we'll remove to avoid sticky failures
                        try:
                            p.unlink()
                        except Exception:
                            logger.exception(f"Failed to remove bad pending file {p}")
                        continue

                    content = base64.b64decode(content_b64)
                    now = datetime.utcnow()

                    # Insert into Postgres
                    await conn.execute(
                        f"INSERT INTO {self.table_name} (id, filename, file_type, file_size, content, metadata, created_at, updated_at, status) "
                        f"VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9)",
                        doc_id,
                        filename,
                        file_type,
                        len(content),
                        content,
                        json.dumps(metadata),
                        created_at or now,
                        updated_at or now,
                        rec.get('status', 'processing')
                    )

                    # remove file on success
                    try:
                        p.unlink()
                    except Exception:
                        logger.exception(f"Failed to remove pending file after flush: {p}")

                    flushed += 1
                except asyncpg.UniqueViolationError:
                    # Document already exists in DB; remove pending file
                    try:
                        p.unlink()
                    except Exception:
                        logger.exception(f"Failed to remove duplicate pending file {p}")
                except Exception:
                    logger.exception(f"Failed to flush pending file {p}")

        if flushed > 0:
            logger.info(f"Flushed {flushed} pending documents into Postgres")
        return flushed
