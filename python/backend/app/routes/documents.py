"""
/api/documents routes — mirrors Express src/routes/documents.ts
Supports file upload to MinIO + document ingestion pipeline.
"""
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Response, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Document, Agent
from app.config import settings

import logging
logger = logging.getLogger("voiceflow.documents")

router = APIRouter()


def _doc_to_dict(doc: Document) -> dict:
    return {
        "id": doc.id,
        "url": doc.url,
        "s3Path": doc.s3Path,
        "status": doc.status,
        "title": doc.title,
        "content": doc.content,
        "metadata": doc.metadata_,
        "tenantId": doc.tenantId,
        "agentId": doc.agentId,
        "createdAt": doc.createdAt.isoformat() if doc.createdAt else None,
        "updatedAt": doc.updatedAt.isoformat() if doc.updatedAt else None,
    }


def _get_s3_client():
    """Get MinIO/S3 client."""
    import boto3
    endpoint = settings.MINIO_ENDPOINT or "localhost:9000"
    if not endpoint.startswith("http"):
        endpoint = f"http://{endpoint}"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.MINIO_ACCESS_KEY or "minioadmin",
        aws_secret_access_key=settings.MINIO_SECRET_KEY or "minioadmin",
    )


@router.get("/")
async def list_documents(agentId: str = Query(...), auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Agent).where(Agent.id == agentId, Agent.tenantId == auth.tenant_id))
    if not r.scalar_one_or_none():
        return JSONResponse({"error": "Access denied"}, status_code=403)

    result = await db.execute(select(Document).where(Document.agentId == agentId).order_by(Document.createdAt.desc()))
    docs = result.scalars().all()
    return [_doc_to_dict(d) for d in docs]


@router.get("/{doc_id}")
async def get_document(doc_id: str, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id, Document.tenantId == auth.tenant_id))
    doc = result.scalar_one_or_none()
    if not doc:
        return JSONResponse({"error": "Document not found"}, status_code=404)
    return _doc_to_dict(doc)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    agentId: str = Form(...),
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a file, store in MinIO, and trigger the ingestion pipeline.
    Supports: PDF, DOCX, PPTX, XLSX, TXT, CSV, images (PNG/JPG/TIFF).
    """
    # Validate agent belongs to tenant
    r = await db.execute(select(Agent).where(Agent.id == agentId, Agent.tenantId == auth.tenant_id))
    if not r.scalar_one_or_none():
        return JSONResponse({"error": "Access denied"}, status_code=403)

    # Validate file type
    allowed_extensions = {".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".xls", ".txt", ".md", ".csv", ".json",
                          ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}
    ext = Path(file.filename or "file").suffix.lower()
    if ext not in allowed_extensions:
        return JSONResponse(
            {"error": f"Unsupported file type: {ext}. Allowed: {', '.join(sorted(allowed_extensions))}"},
            status_code=400,
        )

    # Read file content
    file_bytes = await file.read()
    if len(file_bytes) > 50 * 1024 * 1024:  # 50MB limit
        return JSONResponse({"error": "File too large. Maximum 50MB."}, status_code=400)

    # Upload to MinIO
    s3_key = f"{auth.tenant_id}/{int(datetime.now(timezone.utc).timestamp())}-{file.filename}"
    bucket = "voiceflow-documents"
    try:
        s3 = _get_s3_client()
        # Ensure bucket exists
        try:
            s3.head_bucket(Bucket=bucket)
        except Exception:
            s3.create_bucket(Bucket=bucket)
        import io
        s3.upload_fileobj(io.BytesIO(file_bytes), bucket, s3_key)
    except Exception as e:
        # MinIO might not be running — continue with direct ingestion
        s3_key = None

    # Create document record
    doc = Document(
        url=None,
        s3Path=f"{bucket}/{s3_key}" if s3_key else None,
        agentId=agentId,
        tenantId=auth.tenant_id,
        title=file.filename,
        status="processing",
    )
    db.add(doc)
    await db.flush()
    await db.commit()
    await db.refresh(doc)

    # Trigger ingestion pipeline in background
    import asyncio
    from app.services.ingestion_service import ingest_file

    async def _run_ingestion():
        try:
            result = await ingest_file(
                file_bytes=file_bytes,
                filename=file.filename,
                tenant_id=auth.tenant_id,
                agent_id=agentId,
                job_id=doc.id,
            )
            # Update document status
            from app.database import AsyncSessionLocal
            from sqlalchemy import update
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(Document).where(Document.id == doc.id).values(
                        status="completed" if result.get("status") == "completed" else "failed",
                        metadata_=result,
                    )
                )
                await session.commit()
                logger.info(f"Document {doc.id} status updated to completed")
        except Exception:
            logger.exception("Ingestion background task failed")

    asyncio.create_task(_run_ingestion())

    return JSONResponse(_doc_to_dict(doc), status_code=201)


@router.post("/")
async def create_document(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    agent_id = body.get("agentId")
    url = body.get("url")
    if not agent_id:
        return JSONResponse({"error": "\"agentId\" is required"}, status_code=400)

    r = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
    if not r.scalar_one_or_none():
        return JSONResponse({"error": "Access denied"}, status_code=403)

    doc = Document(url=url, agentId=agent_id, tenantId=auth.tenant_id, status="pending")
    db.add(doc)
    await db.flush()
    await db.commit()
    await db.refresh(doc)

    # Trigger URL ingestion if URL provided
    if url:
        import asyncio
        from app.services.ingestion_service import ingest_urls

        async def _run_url_ingestion():
            try:
                result = await ingest_urls(
                    urls=[url],
                    tenant_id=auth.tenant_id,
                    agent_id=agent_id,
                    job_id=doc.id,
                )
                from app.database import AsyncSessionLocal
                from sqlalchemy import update
                async with AsyncSessionLocal() as session:
                    await session.execute(
                        update(Document).where(Document.id == doc.id).values(
                            status="completed" if result.get("status") == "completed" else "failed",
                            metadata_=result,
                        )
                    )
                    await session.commit()
            except Exception:
                logger.exception("URL ingestion failed")

        asyncio.create_task(_run_url_ingestion())

    return JSONResponse(_doc_to_dict(doc), status_code=201)


@router.put("/{doc_id}")
async def update_document(doc_id: str, body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id, Document.tenantId == auth.tenant_id))
    doc = result.scalar_one_or_none()
    if not doc:
        return JSONResponse({"error": "Document not found"}, status_code=404)

    for field in ("status", "title", "content"):
        if field in body:
            setattr(doc, field, body[field])
    if "metadata" in body:
        doc.metadata_ = body["metadata"]
    await db.commit()
    await db.refresh(doc)
    return _doc_to_dict(doc)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id, Document.tenantId == auth.tenant_id))
    doc = result.scalar_one_or_none()
    if not doc:
        return JSONResponse({"error": "Document not found"}, status_code=404)

    # Also delete from MinIO if s3Path exists
    if doc.s3Path:
        try:
            parts = doc.s3Path.split("/", 1)
            if len(parts) == 2:
                s3 = _get_s3_client()
                s3.delete_object(Bucket=parts[0], Key=parts[1])
        except Exception:
            pass

    await db.delete(doc)
    await db.commit()
    return Response(status_code=204)
