"""
FastAPI Ingestion Service
Handles document upload, OCR, web scraping, embedding, and storage
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

# Import modular components
from services.file_detector import FileDetector
from services.ocr_processor import OCRProcessor
from services.web_scraper import WebScraper
from services.embedder import TextEmbedder
from services.vector_store import VectorStore
from services.database import DatabaseManager
# Optional summarizer (precompute summaries at ingest)
try:
    from services.summarizer import Summarizer
except Exception:
    Summarizer = None

import asyncio  # Add this import

# Load environment variables
load_dotenv()

# Configure logging
# Determine log directory (allow override via env). Default to document-ingestion folder
log_dir = os.environ.get("INGESTION_LOG_DIR", os.path.join(os.getcwd(), "ingestion_logs"))
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, "ingestion_service.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# On Windows, ensure the Proactor event loop policy is used so
# subprocess support (required by Playwright/crawl4ai) is available.
try:
    import sys
    if sys.platform.startswith("win"):
        # Set policy before any asyncio subprocesses are created
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        logger.info("Windows ProactorEventLoopPolicy set for asyncio (subprocess support)")
except Exception as _:
    # If setting the policy fails, continue and let the application log any runtime errors
    logger.warning("Could not set Windows ProactorEventLoopPolicy; subprocess support may be limited")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting FastAPI app with services...")
    # NOTE: automatic startup sync has been intentionally removed to avoid
    # running the sync in every process when uvicorn reload is enabled.
    # Use the /admin/sync endpoint or a CLI task to trigger sync manually.

    # Attempt to flush any pending filesystem-stored documents into Postgres.
    # This is safe to call at startup; the flush helper will no-op if Postgres
    # is still unavailable. Controlled by FLUSH_PENDING_ON_STARTUP env var.
    try:
        flush_on_start = os.getenv('FLUSH_PENDING_ON_STARTUP', 'true').lower() in ('1', 'true', 'yes')
        if flush_on_start:
            batch = int(os.getenv('FLUSH_PENDING_BATCH_SIZE', '100'))
            try:
                # db_manager is initialized later in the module but will be available
                # by the time the lifespan startup runs.
                n = await db_manager.flush_pending_documents(batch_size=batch)
                logger.info(f"Flushed {n} pending documents into Postgres on startup")
            except Exception:
                logger.exception("Failed to flush pending documents on startup")

        # Optionally run a periodic background flush task which will attempt
        # to flush pending documents every PERIODIC_FLUSH_INTERVAL seconds.
        periodic = os.getenv('PERIODIC_FLUSH', 'false').lower() in ('1', 'true', 'yes')
        flush_task = None
        if periodic:
            interval = int(os.getenv('PERIODIC_FLUSH_INTERVAL', '60'))
            batch = int(os.getenv('FLUSH_PENDING_BATCH_SIZE', '100'))

            async def _periodic_flush():
                logger.info(f"Starting periodic pending-docs flush every {interval}s")
                try:
                    while True:
                        await asyncio.sleep(interval)
                        try:
                            n = await db_manager.flush_pending_documents(batch_size=batch)
                            if n:
                                logger.info(f"Periodic flush inserted {n} pending documents")
                        except Exception:
                            logger.exception("Periodic flush failed")
                except asyncio.CancelledError:
                    logger.info("Periodic flush task cancelled")

            flush_task = asyncio.create_task(_periodic_flush())
            # Attach to app state so shutdown can cancel it
            app.state._flush_task = flush_task

    except Exception:
        logger.exception("Exception during startup flush setup")

    yield  # Run app
    
    # Shutdown (optional)
    # Cancel periodic flush task if present
    try:
        task = getattr(app.state, '_flush_task', None)
        if task:
            task.cancel()
            try:
                await task
            except Exception:
                pass
    except Exception:
        logger.exception("Failed to cancel periodic flush task on shutdown")

    logger.info("Shutting down app...")

app = FastAPI(
    title="Document Ingestion API",
    description="API for ingesting documents, images, PDFs, and URLs with OCR and web scraping",
    version="1.0.0",
    lifespan=lifespan  # Add this
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
file_detector = FileDetector()
ocr_processor = OCRProcessor()
web_scraper = WebScraper()
embedder = TextEmbedder()
vector_store = VectorStore()
db_manager = DatabaseManager()
if Summarizer and os.getenv('USE_SUMMARIZER', 'true').lower() in ('1', 'true', 'yes'):
    try:
        summarizer = Summarizer()
        logger.info('Summarizer initialized for ingestion')
    except Exception:
        logger.exception('Failed to initialize Summarizer; document summaries will be truncated previews')
        summarizer = None
else:
    summarizer = None


# (Removed deprecated @app.on_event startup handler in favor of lifespan scheduling above.)


# Administrative endpoints
@app.post("/admin/sync")
async def trigger_sync(background_tasks: BackgroundTasks):
    """
    Manually trigger database -> vector-store sync.
    Use this endpoint after startup to avoid automatic sync running in every
    reload worker process.
    """

    async def _sync_runner():
        try:
            logger.info("Manual sync triggered via /admin/sync")
            await vector_store.sync_from_database(db_manager, ocr_processor, web_scraper, embedder, file_detector, summarizer=summarizer)
            logger.info("Manual sync completed successfully")
        except Exception as e:
            logger.error(f"Manual sync failed: {e}", exc_info=True)

    # Schedule as background task so this request returns immediately
    background_tasks.add_task(lambda: asyncio.create_task(_sync_runner()))

    return JSONResponse(content={"status": "success", "message": "Sync started in background"})


# Request/Response Models
class URLUploadRequest(BaseModel):
    url: HttpUrl
    metadata: Optional[Dict[str, Any]] = {}


class IngestionResponse(BaseModel):
    status: str
    message: str
    document_id: Optional[str] = None
    chunks_created: Optional[int] = None
    processing_time: Optional[float] = None


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    services: Dict[str, bool]

class DocumentListResponse(BaseModel):
    status: str
    message: str
    documents: List[Dict[str, Any]]  # e.g., [{"id": str, "filename": str, "file_type": str, "created_at": str, ...}]
    total: int
    limit: Optional[int] = None
    offset: Optional[int] = None

class BulkDeleteRequest(BaseModel):
    document_ids: List[str]

class BulkDeleteResponse(BaseModel):
    status: str
    message: str
    deleted: List[str]
    not_found: List[str]
    errors: List[Dict[str, Any]]  # e.g., [{"id": "uuid", "error": "msg"}]

# Helper function for processing pipeline
async def process_document(
    content,
    filename: str,
    file_type: str,
    metadata: Dict[str, Any]
) -> IngestionResponse:
    """
    Main processing pipeline for documents
    """
    start_time = datetime.now()
    logger.info(f"Starting processing for {filename} of type {file_type}")
    
    try:
        extracted_text = ""

        # If content is a path string, read minimal info and let services open file as needed
        is_path = isinstance(content, str)
        data_bytes = None
        if is_path:
            # leave actual heavy reads to OCR or scraper which can operate on paths
            data_bytes = None
        else:
            data_bytes = content

        # Step 1: Extract text based on file type
        if file_type in ["image", "pdf"]:
            logger.info(f"Processing {file_type} with OCR")
            # OCR processor supports either bytes or a file path
            if is_path:
                extracted_text = await ocr_processor.process(content, file_type)
            else:
                extracted_text = await ocr_processor.process(data_bytes, file_type)
            logger.info(f"OCR completed. Extracted {len(extracted_text)} characters")
        
        elif file_type == "url":
            url = content.decode('utf-8') if not is_path else open(content, 'rb').read().decode('utf-8')
            logger.info(f"Scraping URL: {url}")
            extracted_text = await web_scraper.scrape(url)
            logger.info(f"Scraping completed. Extracted {len(extracted_text)} characters")
            metadata['url'] = url
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")
        
        if not extracted_text or len(extracted_text.strip()) == 0:
            raise HTTPException(status_code=400, detail="No text could be extracted from the document")
        
        # Precompute a document-level summary to speed up RAG prompt construction later
        try:
            if summarizer and extracted_text and len(extracted_text.strip()) > 0:
                try:
                    doc_summary = summarizer.summarize([extracted_text], max_length=200)[0]
                except Exception:
                    logger.exception('Summarizer failed; falling back to truncated preview')
                    doc_summary = extracted_text.replace('\n', ' ')[:200]
            else:
                doc_summary = extracted_text.replace('\n', ' ')[:200]
            metadata['document_summary'] = doc_summary
        except Exception:
            logger.exception('Failed to compute document summary')
            metadata['document_summary'] = ''

        # Step 2: Store original document in Postgres
        logger.info("Storing original document in database")
        # For store_document we prefer to pass bytes when available; if caller provided a file path,
        # read its bytes for storing the raw content. If file is too large this may be slow; consider
        # letting the backend DB store a reference and filesystem storage handle the file contents.
        store_content = data_bytes if data_bytes is not None else None
        if store_content is None and is_path:
            try:
                with open(content, 'rb') as fh:
                    store_content = fh.read()
            except Exception:
                store_content = b''

        document_id = await db_manager.store_document(
            filename=filename,
            content=store_content,
            file_type=file_type,
            metadata=metadata
        )
        logger.info(f"Document stored with ID: {document_id}")
        
        # Step 3: Chunk the text
        logger.info("Chunking text")
        chunks = embedder.chunk_text(extracted_text)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Step 4: Create embeddings
        logger.info("Creating embeddings")
        embeddings = await embedder.embed_chunks(chunks)
        logger.info(f"Created {len(embeddings)} embeddings")
        
        # Step 5: Store in vector database
        logger.info("Storing embeddings in ChromaDB")
        await vector_store.store_embeddings(
            document_id=document_id,
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadata
        )
        # Mark document as completed in the database
        try:
            await db_manager.update_document_status(document_id, "completed")
            logger.info(f"Document {document_id} status updated to completed")
        except Exception as _:
            logger.warning(f"Failed to update status to completed for document {document_id}")
        logger.info("Embeddings stored successfully")
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Processing completed for {filename} in {processing_time:.2f}s")
        
        return IngestionResponse(
            status="success",
            message="Document processed and stored successfully",
            document_id=document_id,
            chunks_created=len(chunks),
            processing_time=processing_time
        )
    
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}", exc_info=True)
        # Attempt to mark as failed if we have a document_id
        try:
            if 'document_id' in locals() and document_id:
                await db_manager.update_document_status(document_id, "failed", error_message=str(e))
        except Exception:
            logger.warning("Failed to set document status to failed")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


# API Routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify all services are running
    """
    logger.info("Health check requested")
    
    services_status = {
        "database": await db_manager.check_connection(),
        "vector_store": vector_store.check_connection(),
        "ocr": ocr_processor.is_available(),
        "scraper": web_scraper.is_available()
    }
    
    all_healthy = all(services_status.values())
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=datetime.now().isoformat(),
        services=services_status
    )


@app.post("/ingest", response_model=IngestionResponse)
async def ingest_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Main ingestion endpoint for file uploads
    Accepts: images, PDFs, documents, or text files containing URLs
    """
    logger.info(f"Ingestion request received for file: {file.filename}")
    
    try:
        # Read file content
        content = await file.read()
        logger.info(f"File size: {len(content)} bytes")
        
        # Detect file type
        file_type = file_detector.detect_type(content, file.filename)
        logger.info(f"Detected file type: {file_type}")
        
        # Check if it's a URL (text file containing URL)
        if file_type == "text":
            text_content = content.decode('utf-8').strip()
            if file_detector.is_url(text_content):
                file_type = "url"
                content = text_content.encode('utf-8')
                logger.info("Detected URL in text file")
        
        # Process document
        metadata = {
            "original_filename": file.filename,
            "content_type": file.content_type,
            "uploaded_at": datetime.now().isoformat()
        }
        
        result = await process_document(content, file.filename, file_type, metadata)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in ingestion endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.post("/ingest/url", response_model=IngestionResponse)
async def ingest_url(request: URLUploadRequest):
    """
    Dedicated endpoint for URL ingestion
    """
    logger.info(f"URL ingestion request received: {request.url}")
    
    try:
        url_str = str(request.url)
        
        # Check if URL is valid and not blank
        if not url_str or url_str.strip() == "":
            raise HTTPException(status_code=400, detail="URL cannot be blank")
        
        # Process as URL
        metadata = {
            "original_url": url_str,
            "uploaded_at": datetime.now().isoformat(),
            **request.metadata
        }
        
        result = await process_document(
            content=url_str.encode('utf-8'),
            filename=f"url_{datetime.now().timestamp()}",
            file_type="url",
            metadata=metadata
        )
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in URL ingestion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"URL ingestion failed: {str(e)}")


@app.post("/webhook/upload", response_model=IngestionResponse)
async def webhook_upload(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Webhook endpoint for external services to upload documents
    Same functionality as /ingest but designed for webhook integrations
    """
    logger.info(f"Webhook upload received from external service: {file.filename}")
    return await ingest_document(file, background_tasks)


@app.get("/documents/{document_id}")
async def get_document(document_id: str):
    """
    Retrieve document metadata and processing status
    """
    logger.info(f"Document retrieval requested: {document_id}")
    
    try:
        document = await db_manager.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return JSONResponse(content={
            "status": "success",
            "document": document
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")


@app.get("/documents/{document_id}/embeddings")
async def get_document_embeddings(document_id: str):
    """
    Return the number of embeddings/chunks stored in ChromaDB for a document
    and a small sample of chunk metadata (no full chunk text to avoid large payloads).
    """
    logger.info(f"Embeddings query requested for document: {document_id}")

    try:
        chunks = await vector_store.get_by_document_id(document_id)

        if not chunks:
            return JSONResponse(content={
                "status": "success",
                "document_id": document_id,
                "embeddings_count": 0,
                "sample": []
            })

        # Build a small sample with id, chunk_index, total_chunks and a short snippet
        sample = []
        for c in chunks[:5]:
            meta = c.get("metadata", {})
            snippet = c.get("document")
            if snippet:
                snippet = snippet[:160].replace("\n", " ")
            sample.append({
                "id": c.get("id"),
                "chunk_index": meta.get("chunk_index"),
                "total_chunks": meta.get("total_chunks"),
                "snippet": snippet
            })

        return JSONResponse(content={
            "status": "success",
            "document_id": document_id,
            "embeddings_count": len(chunks),
            "sample": sample
        })

    except Exception as e:
        logger.error(f"Error retrieving embeddings for {document_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Embeddings retrieval failed: {str(e)}")


@app.get("/search")
async def search_documents(query: str, limit: int = 10):
    """
    Search documents using vector similarity
    """
    logger.info(f"Search request: {query}")
    
    try:
        # Create query embedding
        query_embedding = await embedder.embed_text(query)
        
        # Search in vector store
        results = await vector_store.search(query_embedding, limit)
        
        return JSONResponse(content={
            "status": "success",
            "query": query,
            "results": results
        })
    
    except Exception as e:
        logger.error(f"Error in search: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and its associated embeddings by ID
    """
    logger.info(f"Deletion attempt for document: {document_id}")
    
    try:
        # Check if document exists
        document = await db_manager.get_document(document_id)
        if not document:
            logger.warning(f"Document not found for deletion: {document_id}")
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "Document not found",
                    "document_id": document_id
                }
            )
        
        # Delete from database
        await db_manager.delete_document(document_id)
        logger.info(f"Document record deleted from database: {document_id}")
        
        # Delete associated embeddings from vector store
        await vector_store.delete_embeddings_by_document(document_id)
        logger.info(f"Embeddings deleted from vector store: {document_id}")
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "Document deleted successfully",
                "document_id": document_id
            }
        )
    
    except HTTPException:
        raise  # Re-raise HTTP exceptions (e.g., 404)
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")

@app.post("/documents/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_documents(request: BulkDeleteRequest):
    """
    Bulk delete multiple documents and their embeddings by IDs
    """
    logger.info(f"Bulk deletion attempt for {len(request.document_ids)} documents")
    
    deleted = []
    not_found = []
    errors = []
    
    for doc_id in request.document_ids:
        try:
            logger.info(f"Processing bulk deletion for: {doc_id}")
            
            # Check existence
            document = await db_manager.get_document(doc_id)
            if not document:
                logger.warning(f"Document not found in bulk delete: {doc_id}")
                not_found.append(doc_id)
                continue
            
            # Delete from database
            await db_manager.delete_document(doc_id)
            logger.info(f"Document record deleted: {doc_id}")
            
            # Delete embeddings
            await vector_store.delete_embeddings_by_document(doc_id)
            logger.info(f"Embeddings deleted: {doc_id}")
            
            deleted.append(doc_id)
        
        except Exception as e:
            logger.error(f"Error in bulk delete for {doc_id}: {str(e)}", exc_info=True)
            errors.append({"id": doc_id, "error": str(e)})
    
    # Determine overall status
    if not deleted and not not_found and errors:
        raise HTTPException(status_code=500, detail="Bulk deletion failed for all documents")
    elif not deleted and not errors:
        raise HTTPException(status_code=404, detail="No documents found for deletion")
    
    message = f"Bulk deletion completed: {len(deleted)} deleted, {len(not_found)} not found, {len(errors)} errors"
    logger.info(message)
    
    return BulkDeleteResponse(
        status="success" if not errors else "partial",
        message=message,
        deleted=deleted,
        not_found=not_found,
        errors=errors
    )

@app.get("/documents", response_model=DocumentListResponse)
async def list_documents(limit: int = 10, offset: int = 0):
    """
    List all documents with optional pagination
    """
    logger.info(f"Document list requested: limit={limit}, offset={offset}")
    
    try:
        documents, total = await db_manager.list_documents(limit=limit, offset=offset)
        
        return DocumentListResponse(
            status="success",
            message="Documents listed successfully",
            documents=documents,
            total=total,
            limit=limit,
            offset=offset
        )
    
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Listing failed: {str(e)}")

@app.get("/")
async def root():
    """
    Root endpoint with API information
    """
    return {
        "name": "Document Ingestion API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "ingest_file": "/ingest",
            "ingest_url": "/ingest/url",
            "webhook": "/webhook/upload",
            "get_document": "/documents/{document_id}",
            "delete_document": "/documents/{document_id}",
            "bulk_delete_documents": "/documents/bulk-delete",  # Add this line
            "list_documents": "/documents",  # Add this line
            "search": "/search"
        }
    }


if __name__ == "__main__":
    import uvicorn
    # Start uvicorn without auto-reload to avoid multi-process reload issues.
    logger.info("Starting uvicorn without reload (python main.py)")
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=False)