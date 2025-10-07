import asyncio
from fastapi import BackgroundTasks
from typing import Optional
from .minio_helper import get_minio_client, MINIO_BUCKET
from .db import AsyncSessionLocal
from .models import Document
import aiofiles
import os
import pathlib
import traceback
import sys
import io
import logging

logger = logging.getLogger(__name__)


async def ingest_document_task(document_id, s3_path, agent_id, tenant_id):
    """Background ingestion: download file from MinIO, chunk, embed, and upsert to Chroma.

    This is a placeholder that should call the document-ingestion pipeline present
    in the repository (e.g. document-ingestion services). For now it updates DB status.
    """
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
        async with AsyncSessionLocal() as session:
            backend_doc = await session.get(Document, document_id)

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
            async with AsyncSessionLocal() as session:
                doc = await session.get(Document, document_id)
                if doc:
                    doc.embedding_status = 'failed'
                    await session.commit()
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

            metadata = {'original_filename': filename or obj, 'ingested_via': 'backend_worker', 'tenant_id': tenant_id, 'agent_id': agent_id}

            # Mark backend doc processing and also mark ingestion DB status if possible
            if dbm:
                try:
                    await dbm.update_document_status(document_id, 'processing')
                except Exception:
                    logger.exception('Failed to update ingestion DB status to processing')

            async with AsyncSessionLocal() as session:
                doc = await session.get(Document, document_id)
                if doc:
                    doc.embedding_status = 'processing'
                    await session.commit()

            # Call the ingestion pipeline (it will store to its DB and vector store).
            # Ensure we pass tenant/agent context so Chroma stores in the correct collection.
            try:
                # If we streamed to disk, pass the file path so ingestion can read from disk
                input_to_ingest = str(tmp_path) if tmp_path else content
                res = await ingestion_process_document(input_to_ingest, filename or obj, file_type, metadata)
                # ingestion pipeline should have updated canonical ingestion DB; ensure backend row is marked completed
                async with AsyncSessionLocal() as session:
                    doc = await session.get(Document, document_id)
                    if doc:
                        doc.embedding_status = 'completed'
                        await session.commit()
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

        async with AsyncSessionLocal() as session:
            doc = await session.get(Document, document_id)
            if doc:
                doc.embedding_status = 'processing'
                await session.commit()

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
            async with AsyncSessionLocal() as session:
                doc = await session.get(Document, document_id)
                if doc:
                    doc.embedding_status = 'completed'
                    await session.commit()

        except Exception as e:
            logger.exception(f"Ingestion failed for document {document_id}: {e}")
            # Try to mark ingestion DB failed
            if dbm:
                try:
                    await dbm.update_document_status(document_id, 'failed', error_message=str(e))
                except Exception:
                    logger.exception('Failed to update ingestion DB status to failed')

            async with AsyncSessionLocal() as session:
                doc = await session.get(Document, document_id)
                if doc:
                    doc.embedding_status = 'failed'
                    await session.commit()
            return

    except Exception as e:
        traceback.print_exc()
        # Ensure backend doc is marked failed
        try:
            async with AsyncSessionLocal() as session:
                doc = await session.get(Document, document_id)
                if doc:
                    doc.embedding_status = 'failed'
                    await session.commit()
        except Exception:
            logger.exception('Failed to mark document failed in backend DB')
    finally:
        # cleanup temporary file if created
        try:
            if tmp_path:
                import os
                os.unlink(tmp_path)
        except Exception:
            logger.exception('Failed to remove temporary file')


def schedule_ingestion(background_tasks: BackgroundTasks, document_id, s3_path, agent_id, tenant_id):
    background_tasks.add_task(asyncio.create_task, ingest_document_task(document_id, s3_path, agent_id, tenant_id))


async def run_pipeline_stages(pipeline_id: str, target_agent_id: Optional[str] = None):
    """Run pipeline stages defined in the `pipelines` table.

    Each stage is expected to be a dict with a 'type' and optional 'agent_ref' and 'settings'.
    This function implements simple orchestration and placeholder calls to common agent types:
      - curator: runs a knowledge curation pass (sync embeddings / extract FAQs)
      - evaluator: runs a lightweight evaluation over recent embeddings
      - summarizer: summarizes recent calls or documents
      - qa: runs QA audits on transcripts / recent calls

    The implementations here are intentionally lightweight: they either call into
    document-ingestion services when available, or log the intended action.
    """
    import pathlib, sys
    from .db import AsyncSessionLocal
    from .models import Pipeline, PipelineAgent

    # make document-ingestion importable
    try:
        repo_root = pathlib.Path(__file__).resolve().parents[2]
        ingestion_path = repo_root / 'document-ingestion'
        if str(ingestion_path) not in sys.path and ingestion_path.exists():
            sys.path.insert(0, str(ingestion_path))
    except Exception:
        pass

    async with AsyncSessionLocal() as session:
        p = await session.get(Pipeline, pipeline_id)
        if not p:
            logger.error('Pipeline not found: %s', pipeline_id)
            return
        stages = p.stages or []

    # Simple context passed between stages
    context = {'tenant_id': str(p.tenant_id), 'agent_id': str(p.agent_id) if p.agent_id else target_agent_id}

    for idx, stage in enumerate(stages):
        stype = stage.get('type')
        agent_ref = stage.get('agent_ref')
        settings = stage.get('settings', {})
        logger.info('Pipeline %s: running stage %d type=%s agent_ref=%s', pipeline_id, idx, stype, agent_ref)

        # Attempt to load a PipelineAgent for the agent_ref if provided
        pa_obj = None
        if agent_ref:
            async with AsyncSessionLocal() as session:
                try:
                    pa_obj = await session.get(PipelineAgent, agent_ref)
                except Exception:
                    pa_obj = None

        # Handle common stage types
        if stype == 'curator':
            # Knowledge curation: extract FAQs, generate embeddings for new docs
            try:
                # Use ingestion sync_from_database if available
                from services.vector_store import VectorStore
                from services.summarizer import Summarizer
                from services.database import DatabaseManager
                vs = VectorStore()
                dbm = DatabaseManager()
                summ = Summarizer() if 'Summarizer' in globals() else None
                # call sync (this will reindex docs for tenant/agent)
                await vs.sync_from_database(dbm, None, None, None, None, summarizer=None)
            except Exception as e:
                logger.exception('Curator stage failed or services unavailable: %s', e)

        elif stype == 'evaluator':
            # Evaluator: run lightweight checks (placeholder)
            logger.info('Evaluator: would run relevance/accuracy checks (placeholder) settings=%s', settings)

        elif stype == 'summarizer':
            # Summarizer: summarize recent calls/docs to prime context
            try:
                from services.summarizer import Summarizer
                summ = Summarizer()
                # call summarizer with tenant/agent context if available
                await summ.run_for_context(context.get('tenant_id'), context.get('agent_id'), settings)
            except Exception:
                logger.exception('Summarizer not available or failed; skipping')

        elif stype == 'qa':
            # QA auditing: check recent transcripts/calls
            logger.info('QA auditor: would analyze recent transcripts for compliance (placeholder) settings=%s', settings)

        else:
            logger.warning('Unknown pipeline stage type: %s', stype)

    logger.info('Pipeline %s completed', pipeline_id)
