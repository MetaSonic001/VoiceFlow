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
        except Exception as e:
            logger.error(f"Failed to create Postgres pool: {e}", exc_info=True)
            raise

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
        await self._ensure_pool()

        document_id = str(uuid.uuid4())
        now = datetime.utcnow()

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
            raise

    async def update_document_status(
        self,
        document_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        await self._ensure_pool()
        now = datetime.utcnow()

        try:
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
        await self._ensure_pool()

        try:
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
        await self._ensure_pool()

        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(f"SELECT content FROM {self.table_name} WHERE id=$1", document_id)

            if not row:
                return None

            return row["content"]
        except Exception as e:
            logger.error(f"Error retrieving document content from Postgres: {e}", exc_info=True)
            raise

    async def list_documents(self, limit: int = 10, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        await self._ensure_pool()

        try:
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
        await self._ensure_pool()

        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(f"DELETE FROM {self.table_name} WHERE id=$1", document_id)

            # asyncpg returns command tag like 'DELETE <n>' — we can ignore or check
            logger.info(f"Deleted document {document_id} from Postgres")
        except Exception as e:
            logger.error(f"Failed to delete document {document_id} from Postgres: {e}", exc_info=True)
            raise
