import asyncio
from fastapi import BackgroundTasks
from typing import Optional
from .minio_helper import get_minio_client, MINIO_BUCKET
from .db import AsyncSessionLocal
from .models import Document, Pipeline, PipelineAgent
import aiofiles
import os
import pathlib
import traceback
import sys
import io
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
import time

logger = logging.getLogger(__name__)


async def _retry_db_operation(operation, max_retries=3, delay=1.0):
    """Retry database operations that may fail due to event loop issues."""
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await operation()
        except (RuntimeError, ConnectionError, asyncio.TimeoutError) as e:
            last_exception = e
            if "attached to a different loop" in str(e) or "another operation is in progress" in str(e):
                logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                    continue
            # Re-raise immediately for non-retryable errors
            raise
        except Exception as e:
            # For other exceptions, don't retry
            raise
    # If we get here, all retries failed
    logger.error(f"Database operation failed after {max_retries} attempts: {last_exception}")
    raise last_exception


async def _create_task_session():
    """Create a database session factory bound to the current event loop.

    This ensures that asyncpg connections are created in the same event loop
    as the worker task, preventing 'Task got Future attached to a different loop' errors.
    """
    # Get database URL from environment
    database_url = os.getenv('BACKEND_DATABASE_URL') or os.getenv('DATABASE_URL') or 'postgresql+asyncpg://doc_user:doc_password@localhost:5433/documents_db'

    # Create engine bound to current event loop
    engine = create_async_engine(database_url, future=True, echo=False)

    # Create session maker for this engine
    session_maker = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def get_session():
        async with session_maker() as session:
            try:
                yield session
            finally:
                # Ensure session is properly closed
                await session.close()

    return get_session


async def ingest_document_task(document_id, s3_path, agent_id, tenant_id):
    """Background ingestion: download file from MinIO, chunk, embed, and upsert to Chroma.

    This is a placeholder that should call the document-ingestion pipeline present
    in the repository (e.g. document-ingestion services). For now it updates DB status.
    """
    # Create a database session factory bound to the current event loop
    get_session = await _create_task_session()

    # Real ingestion flow: download from MinIO, run extraction, chunking, embedding, and upsert
    # We'll attempt to reuse the repository's document-ingestion services by adding
    # the document-ingestion folder to sys.path so we can import its modules.
    try:
        repo_root = pathlib.Path(__file__).resolve().parents[2]
        ingestion_path = repo_root / 'document-ingestion'
        if str(ingestion_path) not in sys.path and ingestion_path.exists():
            sys.path.insert(0, str(ingestion_path))

        # Import ingestion services dynamically
        try:
            from services.file_detector import FileDetector
            from services.ocr_processor import OCRProcessor
            from services.web_scraper import WebScraper
            from services.embedder import TextEmbedder
            from services.vector_store import VectorStore
            # Optional ingestion DB manager for canonical status updates
            try:
                from services.database import DatabaseManager
            except Exception:
                DatabaseManager = None
        except Exception as imp_e:
            logger.exception("Failed to import document-ingestion services; worker cannot proceed")
            raise

        # Fetch backend document metadata
        async def _fetch_doc():
            async with get_session() as session:
                return await session.get(Document, document_id)
        
        backend_doc = await _retry_db_operation(_fetch_doc)

        filename = getattr(backend_doc, 'filename', None) if backend_doc else None
        file_type = getattr(backend_doc, 'file_type', None) if backend_doc else None

        # Initialize ingestion DB manager if available
        dbm = None
        if DatabaseManager:
            try:
                dbm = DatabaseManager()
            except Exception:
                dbm = None

        # Download file from MinIO
        client = get_minio_client()
        # s3_path may be either 's3://bucket/key' or just the object key used by upload helpers
        if s3_path and s3_path.startswith('s3://'):
            # parse s3://bucket/key
            try:
                _, rest = s3_path.split('s3://', 1)
                bucket, obj = rest.split('/', 1)
            except Exception:
                bucket = os.getenv('MINIO_BUCKET', MINIO_BUCKET)
                obj = s3_path
        else:
            bucket = os.getenv('MINIO_BUCKET', MINIO_BUCKET)
            obj = s3_path

        # Stream object to a temporary file to avoid large in-memory usage.
        import tempfile
        tmp_path = None
        content = None
        try:
            res = client.get_object(bucket, obj)
            # Write to a temporary file on disk
            suffix = pathlib.Path(obj).suffix if obj else ''
            tf = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            tmp_path = tf.name
            try:
                # stream in chunks
                while True:
                    chunk = res.read(64 * 1024)
                    if not chunk:
                        break
                    tf.write(chunk)
            finally:
                try:
                    tf.close()
                except Exception:
                    pass
        except Exception:
            logger.exception(f"Failed to download {obj} from MinIO bucket {bucket}")
            # mark backend document as failed
            async def _mark_failed():
                async with get_session() as session:
                    doc = await session.get(Document, document_id)
                    if doc:
                        doc.embedding_status = 'failed'
                        await session.commit()
            
            await _retry_db_operation(_mark_failed)
            return

        # First try to reuse the document-ingestion pipeline's process_document
        try:
            # import the canonical ingestion pipeline
            from main import process_document as ingestion_process_document
            logger.info("Using document-ingestion.process_document for ingestion")

            # Determine file type if not known using file detector
            fd = FileDetector()
            if not file_type:
                try:
                    if tmp_path:
                        file_type = fd.detect_type(str(tmp_path), filename or obj)
                    else:
                        file_type = fd.detect_type(content, filename or obj)
                except Exception:
                    file_type = 'unknown'

            # Check if detected text file contains a URL
            if file_type in ["text", "text/plain"] and tmp_path:
                try:
                    with open(tmp_path, 'r', encoding='utf-8') as f:
                        text_content = f.read().strip()
                    if fd.is_url(text_content):
                        file_type = "url"
                        # Update input to be the URL string for process_document
                        input_to_ingest = text_content.encode('utf-8')
                        logger.info(f"Detected URL in text file: {text_content}")
                except Exception as e:
                    logger.warning(f"Failed to check for URL in text file: {e}")

            metadata = {'original_filename': filename or obj, 'ingested_via': 'backend_worker', 'tenant_id': tenant_id, 'agent_id': agent_id}

            # Mark backend doc processing and also mark ingestion DB status if possible
            if dbm:
                try:
                    await dbm.update_document_status(document_id, 'processing')
                except Exception:
                    logger.exception('Failed to update ingestion DB status to processing')

            async def _mark_processing():
                async with get_session() as session:
                    doc = await session.get(Document, document_id)
                    if doc:
                        doc.embedding_status = 'processing'
                        await session.commit()
            
            await _retry_db_operation(_mark_processing)

            # Call the ingestion pipeline (it will store to its DB and vector store).
            # Ensure we pass tenant/agent context so Chroma stores in the correct collection.
            try:
                # If we streamed to disk, pass the file path so ingestion can read from disk
                input_to_ingest = str(tmp_path) if tmp_path else content
                res = await ingestion_process_document(input_to_ingest, filename or obj, file_type, metadata)
                # ingestion pipeline should have updated canonical ingestion DB; ensure backend row is marked completed
                async def _mark_completed():
                    async with get_session() as session:
                        doc = await session.get(Document, document_id)
                        if doc:
                            doc.embedding_status = 'completed'
                            await session.commit()
                
                await _retry_db_operation(_mark_completed)
                return
            except Exception as e:
                logger.exception(f"document-ingestion.process_document failed: {e}")
                # fall through to local fallback
        except Exception:
            # If process_document isn't importable, proceed with local embedding flow
            logger.info("document-ingestion.process_document not available; falling back to local embedding flow")

        # Local fallback: initialize local ingestion helpers
        fd = FileDetector()
        ocr = OCRProcessor()
        ws = WebScraper()
        embedder = TextEmbedder()
        vs = VectorStore()

        # Determine file type if not known
        if not file_type:
            try:
                if tmp_path:
                    file_type = fd.detect_type(str(tmp_path), filename or obj)
                else:
                    file_type = fd.detect_type(content, filename or obj)
            except Exception:
                file_type = 'unknown'

        metadata = {
            'original_filename': filename or obj,
            'ingested_via': 'backend_worker',
            'tenant_id': tenant_id,
            'agent_id': agent_id,
        }

        # Update backend doc to processing and mark ingestion DB if available
        if dbm:
            try:
                await dbm.update_document_status(document_id, 'processing')
            except Exception:
                logger.exception('Failed to update ingestion DB status to processing (local fallback)')

        async def _mark_processing_fallback():
            async with get_session() as session:
                doc = await session.get(Document, document_id)
                if doc:
                    doc.embedding_status = 'processing'
                    await session.commit()
        
        await _retry_db_operation(_mark_processing_fallback)

        # Extract text depending on type
        extracted_text = ''
        try:
            if file_type in ['image', 'pdf']:
                # Let OCRProcessor read from disk when tmp_path is present to avoid loading whole file
                if tmp_path:
                    extracted_text = await ocr.process(str(tmp_path), file_type)
                else:
                    extracted_text = await ocr.process(content, file_type)
            elif file_type == 'url':
                # Read url text from file if needed
                if tmp_path:
                    try:
                        with open(tmp_path, 'rb') as _f:
                            url_text = _f.read().decode('utf-8')
                    except Exception:
                        url_text = ''
                else:
                    url_text = content.decode('utf-8') if content else ''
                extracted_text = await ws.scrape(url_text)
                metadata['url'] = url_text
            else:
                # Try to decode as text
                try:
                    if tmp_path and content is None:
                        with open(tmp_path, 'rb') as _f:
                            extracted_text = _f.read().decode('utf-8')
                    else:
                        extracted_text = content.decode('utf-8') if content else ''
                except Exception:
                    # Unsupported binary type
                    extracted_text = ''

            if not extracted_text or not extracted_text.strip():
                raise ValueError('No text extracted from document')

            # Precompute document summary (simple truncated preview to avoid heavy deps here)
            metadata['document_summary'] = extracted_text.replace('\n', ' ')[:300]

            # Chunk and embed
            chunks = embedder.chunk_text(extracted_text)
            if not chunks:
                raise ValueError('No chunks were produced from extracted text')

            embeddings = await embedder.embed_chunks(chunks)

            # Store embeddings using backend document_id so cross-references are simple
            # Ensure tenant/agent are present in metadata for multi-tenant collections
            if 'tenant_id' not in metadata:
                metadata['tenant_id'] = tenant_id
            if 'agent_id' not in metadata:
                metadata['agent_id'] = agent_id
            await vs.store_embeddings(str(document_id), chunks, embeddings, metadata)

            # Mark ingestion DB completed if available
            if dbm:
                try:
                    await dbm.update_document_status(document_id, 'completed')
                except Exception:
                    logger.exception('Failed to update ingestion DB status to completed')

            # Mark backend doc completed
            async def _mark_completed_fallback():
                async with get_session() as session:
                    doc = await session.get(Document, document_id)
                    if doc:
                        doc.embedding_status = 'completed'
                        await session.commit()
            
            await _retry_db_operation(_mark_completed_fallback)

        except Exception as e:
            logger.exception(f"Ingestion failed for document {document_id}: {e}")
            # Try to mark ingestion DB failed
            if dbm:
                try:
                    await dbm.update_document_status(document_id, 'failed', error_message=str(e))
                except Exception:
                    logger.exception('Failed to update ingestion DB status to failed')

            async def _mark_failed_exception():
                async with get_session() as session:
                    doc = await session.get(Document, document_id)
                    if doc:
                        doc.embedding_status = 'failed'
                        await session.commit()
            
            await _retry_db_operation(_mark_failed_exception)
            return

    except Exception as e:
        traceback.print_exc()
        # Ensure backend doc is marked failed
        try:
            async def _mark_failed_outer():
                async with get_session() as session:
                    doc = await session.get(Document, document_id)
                    if doc:
                        doc.embedding_status = 'failed'
                        await session.commit()
            
            await _retry_db_operation(_mark_failed_outer)
        except Exception:
            logger.exception('Failed to mark document failed in backend DB')
    finally:
        # cleanup temporary file if created
        try:
            if tmp_path:
                os.unlink(tmp_path)
        except Exception:
            logger.exception('Failed to remove temporary file')


def schedule_ingestion(background_tasks: BackgroundTasks, document_id, s3_path, agent_id, tenant_id):
    # BackgroundTasks will run the callable in a worker thread. Calling
    # asyncio.create_task inside that thread fails with "no running event loop".
    # Instead, run the coroutine to completion inside that thread using
    # asyncio.run, which creates a fresh event loop for the coroutine.
    try:
        coro = ingest_document_task(document_id, s3_path, agent_id, tenant_id)
        background_tasks.add_task(asyncio.run, coro)
    except Exception:
        # Fallback: if BackgroundTasks API changes or fails, spawn a fire-and-forget
        # task in the current loop when possible.
        try:
            asyncio.create_task(ingest_document_task(document_id, s3_path, agent_id, tenant_id))
        except Exception:
            # Last resort: run synchronously (blocking); not ideal but ensures ingestion runs
            asyncio.run(ingest_document_task(document_id, s3_path, agent_id, tenant_id))


async def run_pipeline_stages(pipeline_id: str, target_agent_id: Optional[str] = None):
    """Run pipeline stages defined in the `pipelines` table.

    Each stage is expected to be a dict with a 'type' and optional 'agent_ref' and 'settings'.
    This function implements simple orchestration and placeholder calls to common agent types:
      - curator: runs a knowledge curation pass (sync embeddings / extract FAQs)
      - evaluator: runs a lightweight evaluation over recent embeddings
    """
    # Create a database session factory bound to the current event loop
    get_session = await _create_task_session()

    try:
        # Ensure ingestion path is available for imports
        repo_root = pathlib.Path(__file__).resolve().parents[2]
        ingestion_path = repo_root / 'document-ingestion'
        if str(ingestion_path) not in sys.path and ingestion_path.exists():
            sys.path.insert(0, str(ingestion_path))
    except Exception:
        pass

    async with get_session() as session:
        async def _get_pipeline():
            return await session.get(Pipeline, pipeline_id)
        
        p = await _retry_db_operation(_get_pipeline)
        if not p:
            logger.error('Pipeline not found: %s', pipeline_id)
            return
        stages = p.stages or []
