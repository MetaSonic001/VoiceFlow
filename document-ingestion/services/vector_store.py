"""
Vector Store Service using ChromaDB
Handles embedding storage and retrieval
"""

from __future__ import annotations

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Service for storing and retrieving embeddings in ChromaDB
    """
    
    def __init__(self, persist_directory: str = None):
        """
        Initialize ChromaDB client with persistent storage
        
        Args:
            persist_directory: Directory for persistent storage
        """
    # Allow overriding persistent directory via environment variable so
    # development runs can keep DB/log files outside the watched source tree.
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
            
            # Initialize client with persistent storage
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="documents",
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )
            
            logger.info(f"ChromaDB initialized with collection: documents")
            logger.info(f"Current collection count: {self.collection.count()}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}", exc_info=True)
            raise
    
    def check_connection(self) -> bool:
        """
        Check if ChromaDB is accessible
        
        Returns:
            True if accessible, False otherwise
        """
        try:
            self.collection.count()
            return True
        except:
            return False
    
    async def store_embeddings(
        self,
        document_id: str,
        chunks: List[str],
        embeddings: List[List[float]],
        metadata: Dict[str, Any]
    ) -> None:
        """
        Store embeddings in ChromaDB
        
        Args:
            document_id: Unique document identifier
            chunks: Text chunks
            embeddings: Embedding vectors
            metadata: Document metadata
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")
        
        logger.info(f"Storing {len(embeddings)} embeddings for document {document_id}")
        
        try:
            # Deduplicate near-identical chunks before inserting.
            # Use a simple cosine threshold on the provided embeddings.
            import numpy as np

            unique_chunks = []
            unique_embeddings = []
            unique_metadatas = []
            ids = []

            def _cosine(a, b):
                a = np.array(a, dtype=np.float32)
                b = np.array(b, dtype=np.float32)
                if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
                    return 0.0
                return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

            for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                # Skip empty chunks
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
                    **metadata
                }
                unique_metadatas.append(chunk_metadata)

            if not unique_chunks:
                logger.info("No unique chunks to store after deduplication")
                return

            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=unique_embeddings,
                documents=unique_chunks,
                metadatas=unique_metadatas
            )

            # If Whoosh index is present in the repo, update it for BM25
            try:
                from services.whoosh_index import WhooshIndex
                whoosh_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'chroma_db', 'whoosh_index'))
                wi = WhooshIndex(whoosh_dir)
                wi.add_documents(ids, unique_chunks, unique_metadatas)
            except Exception:
                # Whoosh optional; ignore failures here
                pass

            logger.info(f"Successfully stored {len(unique_embeddings)} unique embeddings")
            logger.info(f"Total documents in collection: {self.collection.count()}")

        except Exception as e:
            logger.error(f"Error storing embeddings: {e}", exc_info=True)
            raise
    
    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filter_metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar embeddings
        
        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            filter_metadata: Optional metadata filters
        
        Returns:
            List of search results with documents and metadata
        """
        logger.info(f"Searching for {limit} similar documents")
        
        try:
            # Query collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=filter_metadata if filter_metadata else None
            )
            
            # Format results
            formatted_results = []
            
            if results['ids'] and len(results['ids']) > 0:
                for i in range(len(results['ids'][0])):
                    result = {
                        "id": results['ids'][0][i],
                        "document": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if 'distances' in results else None
                    }
                    formatted_results.append(result)
            
            logger.info(f"Found {len(formatted_results)} results")
            return formatted_results
        
        except Exception as e:
            logger.error(f"Error searching embeddings: {e}", exc_info=True)
            raise
    
    async def get_by_document_id(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all chunks for a specific document
        
        Args:
            document_id: Document identifier
        
        Returns:
            List of chunks with metadata
        """
        logger.info(f"Retrieving chunks for document {document_id}")
        
        try:
            results = self.collection.get(
                where={"document_id": document_id}
            )
            
            formatted_results = []
            
            if results['ids']:
                for i in range(len(results['ids'])):
                    result = {
                        "id": results['ids'][i],
                        "document": results['documents'][i],
                        "metadata": results['metadatas'][i]
                    }
                    formatted_results.append(result)
            
            logger.info(f"Retrieved {len(formatted_results)} chunks")
            return formatted_results
        
        except Exception as e:
            logger.error(f"Error retrieving document chunks: {e}", exc_info=True)
            raise
    
    async def delete_embeddings_by_document(self, document_id: str) -> None:
        """
        Delete all embeddings and chunks associated with a document ID
        """
        try:
            results = self.collection.get(where={"document_id": document_id})
            if results["ids"]:  # If any embeddings found
                self.collection.delete(ids=results["ids"])
                logger.info(f"Deleted {len(results['ids'])} embeddings for document {document_id}")
            else:
                logger.warning(f"No embeddings found for document {document_id}")
        except Exception as e:
            logger.error(f"Failed to delete embeddings for document {document_id}: {str(e)}")
            raise
    
    def reset_collection(self) -> None:
        """
        Reset the entire collection (use with caution)
        """
        logger.warning("Resetting collection - all data will be lost!")
        
        try:
            self.client.delete_collection("documents")
            self.collection = self.client.get_or_create_collection(
                name="documents",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("Collection reset complete")
        
        except Exception as e:
            logger.error(f"Error resetting collection: {e}", exc_info=True)
            raise
        
    async def sync_from_database(
        self,
        db_manager: Any,
        ocr_processor: Any,
        web_scraper: Any,
        embedder: Any,
        file_detector: Any
    ) -> None:
        """
        Sync all documents from database to vector store on startup
        """
        logger.info("Starting database sync to vector store")
        
        try:
            # Get documents in paginated batches to avoid memory pressure
            # Attempt to fetch up to 1000 records on initial sync
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
                
                # Skip if already in Chroma
                existing_chunks = await self.get_by_document_id(doc_id)
                if existing_chunks:
                    logger.info(f"Document {doc_id} already synced, skipping")
                    skipped_count += 1
                    continue
                
                try:
                    # Fetch content
                    content = await db_manager.get_document_content(doc_id)
                    if not content:
                        logger.warning(f"No content for document {doc_id}, skipping")
                        logger.info(f"Skipping document {doc_id} because stored content is empty or unavailable")
                        continue
                    
                    # Detect type and extract text
                    file_type = doc.get("file_type", "unknown") if isinstance(doc, dict) else getattr(doc, "file_type", "unknown")
                    filename = doc.get("filename", "unknown") if isinstance(doc, dict) else getattr(doc, "filename", "unknown")
                    metadata = doc.get("metadata", {}) if isinstance(doc, dict) else {}
                    
                    extracted_text = ""
                    if file_type in ["image", "pdf"]:
                        extracted_text = await ocr_processor.process(content, file_type)
                    elif file_type == "url":
                        url = content.decode('utf-8')
                        extracted_text = await web_scraper.scrape(url)
                        metadata['url'] = url
                    else:
                        # Assume text or other; decode if possible
                        try:
                            extracted_text = content.decode('utf-8')
                        except Exception:
                            logger.warning(f"Could not extract text for {file_type} in {doc_id}")
                            continue
                    
                    if not extracted_text or not extracted_text.strip():
                        logger.warning(f"No text extracted for {doc_id}, skipping")
                        logger.info(f"Skipping document {doc_id} because extracted text is empty after processing")
                        continue
                    
                    # Chunk and embed
                    chunks = embedder.chunk_text(extracted_text)
                    if not chunks:
                        continue
                    
                    embeddings = await embedder.embed_chunks(chunks)
                    
                    # Store
                    await self.store_embeddings(doc_id, chunks, embeddings, metadata)
                    # Update document status to completed
                    try:
                        await db_manager.update_document_status(doc_id, "completed")
                        logger.info(f"Document {doc_id} status set to completed in DB")
                    except Exception as e:
                        logger.warning(f"Failed to update status for {doc_id}: {e}")
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