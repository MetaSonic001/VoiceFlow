"""
Vector Store Service using ChromaDB
Handles embedding storage and retrieval
"""

from __future__ import annotations

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


def _collection_name(tenant_id: str, agent_id: str) -> str:
    """Stable collection naming: tenant_agent (hyphens -> underscores)"""
    return f"{tenant_id}_{agent_id}".replace('-', '_')


class VectorStore:
    """
    Service for storing and retrieving embeddings in ChromaDB
    """

    def __init__(self, persist_directory: Optional[str] = None):
        """
        Initialize ChromaDB client with persistent storage

        Args:
            persist_directory: Directory for persistent storage
        """
        if persist_directory is None:
            try:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            except NameError:
                base_dir = os.getcwd()
            persist_directory = os.path.join(base_dir, "..", "chroma_db")
            persist_directory = os.path.normpath(persist_directory)

        try:
            logger.info(f"Initializing ChromaDB at {persist_directory}")

            # Ensure directory exists
            os.makedirs(persist_directory, exist_ok=True)

            # Initialize client with persistent storage. Collections are created lazily.
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False, allow_reset=True),
            )

            logger.info("ChromaDB client initialized (collections are created per-tenant-agent on demand)")

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}", exc_info=True)
            raise

    def check_connection(self) -> bool:
        """Return True if ChromaDB client responds to list_collections"""
        try:
            self.client.list_collections()
            return True
        except Exception:
            return False

    def get_embedding_dimension(self) -> Optional[int]:
        """Try to infer embedding dimension from existing collection metadata if present"""
        try:
            cols = self.client.list_collections()
            if cols:
                md = cols[0].get("metadata") or {}
                if md.get("embedding_dim"):
                    return int(md.get("embedding_dim"))
        except Exception:
            return None
        return None

    def _get_or_create_collection(self, tenant_id: str, agent_id: str, embedding_dim: Optional[int] = None):
        name = _collection_name(tenant_id, agent_id)
        # Ensure metadata is non-empty to avoid Chroma validation errors
        metadata = {
            "hnsw:space": "cosine",
            "tenant_id": str(tenant_id),
            "agent_id": str(agent_id),
        }
        if embedding_dim:
            metadata["embedding_dim"] = embedding_dim
        return self.client.get_or_create_collection(name=name, metadata=metadata)

    async def store_embeddings(
        self,
        document_id: str,
        chunks: List[str],
        embeddings: List[List[float]],
        metadata: Dict[str, Any],
    ) -> None:
        """Store chunk texts and embeddings for a document. Deduplicates similar chunks."""
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")

        logger.info(f"Storing {len(embeddings)} embeddings for document {document_id}")
        try:
            import numpy as np

            unique_chunks: List[str] = []
            unique_embeddings: List[List[float]] = []
            unique_metadatas: List[Dict[str, Any]] = []
            ids: List[str] = []

            def _cosine(a, b):
                a = np.array(a, dtype=np.float32)
                b = np.array(b, dtype=np.float32)
                if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
                    return 0.0
                return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

            for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                if not chunk or not chunk.strip():
                    continue
                is_dup = False
                for u_emb in unique_embeddings:
                    try:
                        if _cosine(u_emb, emb) >= 0.95:
                            is_dup = True
                            break
                    except Exception:
                        continue
                if is_dup:
                    continue
                uid = f"{document_id}_chunk_{i}"
                ids.append(uid)
                unique_chunks.append(chunk)
                unique_embeddings.append(emb)
                chunk_metadata = {
                    "document_id": document_id,
                    "chunk_index": i,
                    "chunk_text": chunk[:500],
                    "total_chunks": len(chunks),
                    "timestamp": datetime.now().isoformat(),
                    **metadata,
                }
                unique_metadatas.append(chunk_metadata)

            if not unique_chunks:
                logger.info("No unique chunks to store after deduplication")
                return

            tenant_id = metadata.get("tenant_id") or metadata.get("tenant")
            agent_id = metadata.get("agent_id") or metadata.get("agent")
            if not tenant_id or not agent_id:
                raise ValueError("tenant_id and agent_id must be provided in metadata for multi-tenant collections")

            coll = self._get_or_create_collection(tenant_id, agent_id, embedding_dim=self.get_embedding_dimension())

            coll.add(ids=ids, embeddings=unique_embeddings, documents=unique_chunks, metadatas=unique_metadatas)

            # Optional: update whoosh index if present
            try:
                from services.whoosh_index import WhooshIndex

                whoosh_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "chroma_db", "whoosh_index"))
                wi = WhooshIndex(whoosh_dir)
                wi.add_documents(ids, unique_chunks, unique_metadatas)
            except Exception:
                pass

            try:
                logger.info(f"Total documents in collection: {coll.count()}")
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error storing embeddings: {e}", exc_info=True)
            raise

    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search a specific tenant/agent collection for similar embeddings"""
        logger.info(f"Searching for {limit} similar documents")
        try:
            if not filter_metadata:
                filter_metadata = {}
            if tenant_id:
                filter_metadata["tenant_id"] = tenant_id
            if agent_id:
                filter_metadata["agent_id"] = agent_id
            if "tenant_id" not in filter_metadata or "agent_id" not in filter_metadata:
                raise ValueError("search requires tenant_id and agent_id either as args or inside filter_metadata")

            coll_name = _collection_name(filter_metadata["tenant_id"], filter_metadata["agent_id"])
            coll = self.client.get_collection(coll_name)

            results = coll.query(query_embeddings=[query_embedding], n_results=limit, where=filter_metadata)

            formatted_results: List[Dict[str, Any]] = []
            if results.get("ids") and len(results["ids"]) > 0:
                for i in range(len(results["ids"][0])):
                    result = {
                        "id": results["ids"][0][i],
                        "document": results["documents"][0][i] if results.get("documents") else None,
                        "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                        "distance": results.get("distances", [[None]])[0][i] if results.get("distances") else None,
                    }
                    formatted_results.append(result)

            logger.info(f"Found {len(formatted_results)} results")
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching embeddings: {e}", exc_info=True)
            raise

    async def get_by_document_id_for(self, tenant_id: str, agent_id: str, document_id: str) -> List[Dict[str, Any]]:
        """Retrieve all chunks for a specific document inside a tenant/agent collection"""
        logger.info(f"Retrieving chunks for document {document_id} in {tenant_id}/{agent_id}")
        try:
            coll_name = _collection_name(tenant_id, agent_id)
            coll = self.client.get_collection(coll_name)
            results = coll.query(where={"document_id": document_id}, n_results=10000)

            formatted_results: List[Dict[str, Any]] = []
            if results.get("ids") and results["ids"]:
                ids = results["ids"][0]
                docs = results["documents"][0] if results.get("documents") else []
                metas = results["metadatas"][0] if results.get("metadatas") else []
                for i in range(len(ids)):
                    formatted_results.append({
                        "id": ids[i],
                        "document": docs[i] if i < len(docs) else None,
                        "metadata": metas[i] if i < len(metas) else {},
                    })

            logger.info(f"Retrieved {len(formatted_results)} chunks for document {document_id}")
            return formatted_results
        except Exception as e:
            logger.error(f"Error retrieving document chunks: {e}", exc_info=True)
            raise

    async def get_by_document_id(self, document_id: str) -> List[Dict[str, Any]]:
        """Search across all collections for a document id and return the first match"""
        logger.info(f"Searching for document {document_id} across collections")
        try:
            cols = self.client.list_collections()
            for col in cols:
                md = col.get("metadata") or {}
                t = md.get("tenant_id")
                a = md.get("agent_id")
                if t and a:
                    try:
                        res = await self.get_by_document_id_for(t, a, document_id)
                        if res:
                            return res
                    except Exception:
                        continue
            return []
        except Exception as e:
            logger.error(f"Error searching document across collections: {e}", exc_info=True)
            raise

    async def delete_embeddings_by_document_for(self, tenant_id: str, agent_id: str, document_id: str) -> None:
        """Delete embeddings for a document inside a tenant/agent collection"""
        try:
            coll = self._get_or_create_collection(tenant_id, agent_id, embedding_dim=self.get_embedding_dimension())
            coll.delete(where={"document_id": document_id})
            logger.info(f"Deleted embeddings for document {document_id} from {tenant_id}/{agent_id}")
        except Exception as e:
            logger.error(f"Failed to delete embeddings for document {document_id}: {e}", exc_info=True)
            raise

    async def delete_embeddings_by_document(self, document_id: str) -> None:
        """Delete embeddings for a document across all collections"""
        logger.info(f"Deleting embeddings for document {document_id} across collections")
        try:
            cols = self.client.list_collections()
            for col in cols:
                md = col.get("metadata") or {}
                t = md.get("tenant_id")
                a = md.get("agent_id")
                if t and a:
                    try:
                        await self.delete_embeddings_by_document_for(t, a, document_id)
                    except Exception:
                        continue
            logger.info(f"Completed deletion attempts for {document_id}")
        except Exception as e:
            logger.error(f"Failed to delete embeddings across collections for {document_id}: {e}", exc_info=True)
            raise

    def reset_collection_for(self, tenant_id: str, agent_id: str) -> None:
        """Reset (delete) an entire tenant/agent collection"""
        logger.warning(f"Resetting collection for {tenant_id}/{agent_id}")
        try:
            coll = self._get_or_create_collection(tenant_id, agent_id, embedding_dim=self.get_embedding_dimension())
            coll.delete()
            logger.info(f"Collection {tenant_id}_{agent_id} reset")
        except Exception as e:
            logger.error(f"Failed to reset collection {tenant_id}_{agent_id}: {e}", exc_info=True)
            raise

    async def sync_from_database(
        self,
        db_manager: Any,
        ocr_processor: Any,
        web_scraper: Any,
        embedder: Any,
        file_detector: Any,
        summarizer: Any = None,
    ) -> None:
        """Sync documents from DB into the vector store"""
        logger.info("Starting database sync to vector store")
        try:
            documents, total = await db_manager.list_documents(limit=1000, offset=0)
            logger.info(f"Found {total} documents in database (fetched {len(documents)})")
            synced_count = 0
            skipped_count = 0
            for doc in documents:
                doc_id = doc.get("id") if isinstance(doc, dict) else getattr(doc, "id", None)
                if not doc_id:
                    logger.warning("Skipping document without id")
                    continue
                logger.info(f"Syncing document {doc_id}")
                existing_chunks = await self.get_by_document_id(doc_id)
                if existing_chunks:
                    logger.info(f"Document {doc_id} already synced, skipping")
                    skipped_count += 1
                    continue
                try:
                    content = await db_manager.get_document_content(doc_id)
                    if not content:
                        logger.warning(f"No content for document {doc_id}, skipping")
                        continue
                    file_type = doc.get("file_type", "unknown") if isinstance(doc, dict) else getattr(doc, "file_type", "unknown")
                    metadata = doc.get("metadata", {}) if isinstance(doc, dict) else {}
                    extracted_text = ""
                    
                    # Check if this is a URL (either marked as url type or text content that looks like a URL)
                    is_url_content = False
                    if file_type == "url":
                        is_url_content = True
                        logger.info(f"Document {doc_id} is marked as URL type")
                    elif file_type.startswith("text/") or file_type == "unknown":
                        # Check if the content looks like a URL using the file detector
                        try:
                            text_content = content.decode("utf-8").strip()
                            logger.info(f"Checking if text content is URL: '{text_content[:100]}{'...' if len(text_content) > 100 else ''}'")
                            if file_detector.is_url(text_content):
                                is_url_content = True
                                file_type = "url"  # Reclassify for processing
                                logger.info(f"Reclassified document {doc_id} as URL type based on content")
                            else:
                                logger.info(f"Document {doc_id} content is not a URL")
                        except Exception as e:
                            logger.warning(f"Error checking URL content for {doc_id}: {e}")
                    
                    if file_type in ["image", "pdf"]:
                        logger.info(f"Processing {file_type} with OCR for document {doc_id}")
                        extracted_text = await ocr_processor.process(content, file_type)
                    elif is_url_content:
                        try:
                            url = content.decode("utf-8").strip()
                            logger.info(f"🕷️ Starting web scraping for document {doc_id}: {url}")
                            extracted_text = await web_scraper.scrape(url)
                            metadata["url"] = url
                            logger.info(f"✅ Web scraping completed for document {doc_id}: {len(extracted_text)} characters")
                        except Exception as e:
                            logger.error(f"💥 Failed to scrape URL for document {doc_id}: {e}")
                            continue
                    elif file_type.startswith("text/"):
                        try:
                            logger.info(f"Processing plain text for document {doc_id}")
                            extracted_text = content.decode("utf-8")
                            logger.info(f"✅ Text extraction completed for document {doc_id}: {len(extracted_text)} characters")
                        except Exception:
                            logger.warning(f"Could not extract text for {file_type} in {doc_id}")
                            continue
                    else:
                        logger.warning(f"Unsupported file type {file_type} for document {doc_id}, skipping")
                        continue
                    if not extracted_text or not extracted_text.strip():
                        logger.warning(f"No text extracted for {doc_id}, skipping")
                        continue
                    chunks = embedder.chunk_text(extracted_text)
                    if not chunks:
                        continue
                    embeddings = await embedder.embed_chunks(chunks)
                    await self.store_embeddings(doc_id, chunks, embeddings, metadata)
                    try:
                        await db_manager.update_document_status(doc_id, "completed")
                        logger.info(f"Document {doc_id} status set to completed in DB")
                    except Exception:
                        logger.warning(f"Failed to update status for {doc_id}")
                    synced_count += 1
                    logger.info(f"Synced document {doc_id} ({len(chunks)} chunks)")
                except Exception as e:
                    logger.error(f"Error syncing document {doc_id}: {str(e)}", exc_info=True)
                    try:
                        await db_manager.update_document_status(doc_id, "failed", error_message=str(e))
                    except Exception:
                        logger.warning(f"Could not mark document {doc_id} as failed in DB")
                    continue
            logger.info(f"Sync complete: {synced_count} new docs synced, {skipped_count} skipped, total in DB: {total}")
        except Exception as e:
            logger.error(f"Sync failed: {str(e)}", exc_info=True)
            raise