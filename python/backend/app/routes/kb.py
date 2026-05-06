"""
/api/kb routes — Knowledge Base management per agent.

Endpoints
---------
GET    /api/kb/{agent_id}               — list all KB attachments for an agent
POST   /api/kb/attach                   — attach an existing document to an agent
POST   /api/kb/ingest-file              — upload file + auto-attach to agent
POST   /api/kb/ingest-url               — ingest URL + auto-attach to agent
POST   /api/kb/ingest-text              — paste plain text + auto-attach
PATCH  /api/kb/attachments/{id}         — update when_to_use instruction
DELETE /api/kb/attachments/{id}         — detach document from agent
POST   /api/kb/test-query               — debug retrieval for a query (no side effects)

The `when_to_use` field on each attachment drives precision retrieval:
at query time the RAG service checks semantic similarity between the user's
query and the when_to_use instruction.  Documents with low relevance are
excluded before hitting ChromaDB — preventing context bleed across topics.
"""
from __future__ import annotations

import asyncio
import io
import logging
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db, AsyncSessionLocal
from app.models import Agent, Document, KbAttachment

router = APIRouter()
logger = logging.getLogger("voiceflow.kb")


# ── Serializers ───────────────────────────────────────────────────────────────

def _att_to_dict(att: KbAttachment, doc: Optional[Document] = None) -> dict:
    return {
        "id":            att.id,
        "documentId":    att.documentId,
        "agentId":       att.agentId,
        "whenToUse":     att.whenToUse,
        "chunkCount":    att.chunkCount,
        "status":        att.status,
        "errorMessage":  att.errorMessage,
        "createdAt":     att.createdAt.isoformat() if att.createdAt else None,
        "updatedAt":     att.updatedAt.isoformat() if att.updatedAt else None,
        # document fields (when joined)
        "document": _doc_summary(doc) if doc else None,
    }


def _doc_summary(doc: Document) -> dict:
    return {
        "id":         doc.id,
        "title":      doc.title or doc.url or "Untitled",
        "url":        doc.url,
        "fileType":   doc.fileType or ("url" if doc.url else "file"),
        "chunkCount": doc.chunkCount,
        "status":     doc.status,
        "createdAt":  doc.createdAt.isoformat() if doc.createdAt else None,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _assert_agent_access(agent_id: str, auth: AuthContext, db: AsyncSession) -> Agent:
    r = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id)
    )
    agent = r.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


async def _get_attachment(att_id: str, auth: AuthContext, db: AsyncSession) -> KbAttachment:
    r = await db.execute(
        select(KbAttachment).where(
            KbAttachment.id == att_id,
            KbAttachment.tenantId == auth.tenant_id,
        )
    )
    att = r.scalar_one_or_none()
    if not att:
        raise HTTPException(status_code=404, detail="KB attachment not found")
    return att


async def _update_attachment_after_ingestion(
    att_id: str,
    doc_id: str,
    tenant_id: str,
    agent_id: str,
    ingestion_result: dict,
) -> None:
    """Update KbAttachment and Document status after ingestion completes."""
    chunk_count = ingestion_result.get("chunks", ingestion_result.get("total_chunks", 0))
    success = ingestion_result.get("status") == "completed"
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(KbAttachment).where(KbAttachment.id == att_id).values(
                status="indexed" if success else "error",
                chunkCount=chunk_count,
                errorMessage=None if success else str(ingestion_result.get("errors", "")),
                updatedAt=datetime.now(timezone.utc),
            )
        )
        await session.execute(
            update(Document).where(Document.id == doc_id).values(
                status="completed" if success else "failed",
                chunkCount=chunk_count,
                metadata_=ingestion_result,
            )
        )
        await session.commit()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/{agent_id}")
async def list_kb_attachments(
    agent_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Return all KB attachments for an agent, each joined with its document details."""
    await _assert_agent_access(agent_id, auth, db)

    r = await db.execute(
        select(KbAttachment, Document)
        .join(Document, Document.id == KbAttachment.documentId, isouter=True)
        .where(KbAttachment.agentId == agent_id, KbAttachment.tenantId == auth.tenant_id)
        .order_by(KbAttachment.createdAt.desc())
    )
    rows = r.all()
    return {"attachments": [_att_to_dict(att, doc) for att, doc in rows]}


@router.post("/attach", status_code=201)
async def attach_document(
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Attach an already-uploaded document to an agent with an optional when_to_use
    instruction.  The document must belong to the same tenant.
    """
    agent_id  = body.get("agentId", "")
    doc_id    = body.get("documentId", "")
    when_to_use = body.get("whenToUse") or None

    if not agent_id or not doc_id:
        raise HTTPException(status_code=400, detail="agentId and documentId are required")

    await _assert_agent_access(agent_id, auth, db)

    r = await db.execute(
        select(Document).where(Document.id == doc_id, Document.tenantId == auth.tenant_id)
    )
    doc = r.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Prevent duplicate attachment
    existing = await db.execute(
        select(KbAttachment).where(
            KbAttachment.agentId == agent_id,
            KbAttachment.documentId == doc_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Document already attached to this agent")

    att = KbAttachment(
        tenantId=auth.tenant_id,
        agentId=agent_id,
        documentId=doc_id,
        whenToUse=when_to_use,
        chunkCount=doc.chunkCount or 0,
        status="indexed" if doc.status == "completed" else "pending",
    )
    db.add(att)
    await db.commit()
    await db.refresh(att)
    logger.info("[kb] Attached doc %s → agent %s (when_to_use=%r)", doc_id, agent_id, when_to_use)
    return JSONResponse(_att_to_dict(att, doc), status_code=201)


@router.post("/ingest-file", status_code=201)
async def kb_ingest_file(
    file: UploadFile = File(...),
    agentId: str = Form(...),
    whenToUse: str = Form(""),
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a file, create a Document record, create a KbAttachment, and run
    the ingestion pipeline in the background.
    Supported: PDF, DOCX, TXT, CSV, images (PNG/JPG/TIFF).
    """
    await _assert_agent_access(agentId, auth, db)

    allowed_ext = {
        ".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".txt", ".md",
        ".csv", ".json", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp",
    }
    ext = Path(file.filename or "file").suffix.lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    file_bytes = await file.read()
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 50 MB.")

    file_type_map = {
        ".pdf": "pdf", ".docx": "docx", ".doc": "docx", ".pptx": "pptx",
        ".xlsx": "xlsx", ".txt": "txt", ".md": "txt", ".csv": "csv",
        ".json": "txt", ".png": "image", ".jpg": "image", ".jpeg": "image",
        ".tiff": "image", ".bmp": "image", ".webp": "image",
    }

    doc = Document(
        agentId=agentId,
        tenantId=auth.tenant_id,
        title=file.filename,
        status="processing",
        fileType=file_type_map.get(ext, "file"),
    )
    db.add(doc)
    await db.flush()

    att = KbAttachment(
        tenantId=auth.tenant_id,
        agentId=agentId,
        documentId=doc.id,
        whenToUse=whenToUse.strip() or None,
        status="pending",
    )
    db.add(att)
    await db.commit()
    await db.refresh(doc)
    await db.refresh(att)

    # Background ingestion
    att_id = att.id
    doc_id = doc.id
    tenant_id = auth.tenant_id

    async def _bg_ingest():
        from app.services.ingestion_service import ingest_file
        try:
            result = await ingest_file(
                file_bytes=file_bytes,
                filename=file.filename,
                tenant_id=tenant_id,
                agent_id=agentId,
                job_id=doc_id,
                document_id=doc_id,
            )
            await _update_attachment_after_ingestion(att_id, doc_id, tenant_id, agentId, result)
        except Exception as exc:
            logger.exception("[kb] ingest_file failed for doc %s: %s", doc_id, exc)
            async with AsyncSessionLocal() as sess:
                await sess.execute(
                    update(KbAttachment).where(KbAttachment.id == att_id).values(
                        status="error", errorMessage=str(exc)
                    )
                )
                await sess.execute(
                    update(Document).where(Document.id == doc_id).values(status="failed")
                )
                await sess.commit()

    asyncio.create_task(_bg_ingest())

    return JSONResponse({
        "attachment": _att_to_dict(att, doc),
        "message": "Ingestion started. Status will update to 'indexed' when complete.",
    }, status_code=201)


@router.post("/ingest-url", status_code=201)
async def kb_ingest_url(
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Scrape a URL, chunk it, embed it, store in ChromaDB, and attach to agent.
    """
    agent_id    = body.get("agentId", "")
    url         = (body.get("url") or "").strip()
    when_to_use = (body.get("whenToUse") or "").strip() or None

    if not agent_id or not url:
        raise HTTPException(status_code=400, detail="agentId and url are required")

    await _assert_agent_access(agent_id, auth, db)

    doc = Document(
        url=url,
        agentId=agent_id,
        tenantId=auth.tenant_id,
        title=url,
        status="processing",
        fileType="url",
    )
    db.add(doc)
    await db.flush()

    att = KbAttachment(
        tenantId=auth.tenant_id,
        agentId=agent_id,
        documentId=doc.id,
        whenToUse=when_to_use,
        status="pending",
    )
    db.add(att)
    await db.commit()
    await db.refresh(doc)
    await db.refresh(att)

    att_id, doc_id, tenant_id = att.id, doc.id, auth.tenant_id

    async def _bg_ingest():
        from app.services.ingestion_service import ingest_urls
        try:
            result = await ingest_urls(
                urls=[url],
                tenant_id=tenant_id,
                agent_id=agent_id,
                job_id=doc_id,
                document_id=doc_id,
            )
            await _update_attachment_after_ingestion(att_id, doc_id, tenant_id, agent_id, result)
        except Exception as exc:
            logger.exception("[kb] ingest_urls failed for doc %s: %s", doc_id, exc)
            async with AsyncSessionLocal() as sess:
                await sess.execute(
                    update(KbAttachment).where(KbAttachment.id == att_id).values(
                        status="error", errorMessage=str(exc)
                    )
                )
                await sess.execute(
                    update(Document).where(Document.id == doc_id).values(status="failed")
                )
                await sess.commit()

    asyncio.create_task(_bg_ingest())

    return JSONResponse({
        "attachment": _att_to_dict(att, doc),
        "message": "URL ingestion started.",
    }, status_code=201)


@router.post("/ingest-text", status_code=201)
async def kb_ingest_text(
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest pasted plain text directly into ChromaDB and attach to agent.
    Useful for product descriptions, FAQ answers, policies, etc.
    """
    agent_id    = body.get("agentId", "")
    text        = (body.get("text") or "").strip()
    title       = (body.get("title") or "Pasted text").strip()
    when_to_use = (body.get("whenToUse") or "").strip() or None

    if not agent_id or not text:
        raise HTTPException(status_code=400, detail="agentId and text are required")
    if len(text) < 20:
        raise HTTPException(status_code=400, detail="Text is too short (minimum 20 characters)")

    await _assert_agent_access(agent_id, auth, db)

    doc = Document(
        agentId=agent_id,
        tenantId=auth.tenant_id,
        title=title,
        content=text[:500],   # store a preview
        status="processing",
        fileType="text",
    )
    db.add(doc)
    await db.flush()

    att = KbAttachment(
        tenantId=auth.tenant_id,
        agentId=agent_id,
        documentId=doc.id,
        whenToUse=when_to_use,
        status="pending",
    )
    db.add(att)
    await db.commit()
    await db.refresh(doc)
    await db.refresh(att)

    att_id, doc_id, tenant_id = att.id, doc.id, auth.tenant_id

    async def _bg_ingest():
        from app.services.ingestion_service import clean_text, chunk_text, store_in_chromadb, build_bm25_index
        import asyncio as _aio
        from concurrent.futures import ThreadPoolExecutor
        try:
            cleaned = clean_text(text)
            chunks  = chunk_text(cleaned, source=title, metadata={"documentId": doc_id, "fileType": "text"})
            pool    = ThreadPoolExecutor(max_workers=2)
            loop    = _aio.get_event_loop()
            stored  = await loop.run_in_executor(pool, store_in_chromadb, tenant_id, agent_id, chunks, "text_paste")
            await loop.run_in_executor(pool, build_bm25_index, tenant_id, agent_id)
            await _update_attachment_after_ingestion(
                att_id, doc_id, tenant_id, agent_id,
                {"status": "completed", "chunks": stored}
            )
        except Exception as exc:
            logger.exception("[kb] text ingestion failed for doc %s: %s", doc_id, exc)
            async with AsyncSessionLocal() as sess:
                await sess.execute(
                    update(KbAttachment).where(KbAttachment.id == att_id).values(
                        status="error", errorMessage=str(exc)
                    )
                )
                await sess.execute(
                    update(Document).where(Document.id == doc_id).values(status="failed")
                )
                await sess.commit()

    asyncio.create_task(_bg_ingest())

    return JSONResponse({
        "attachment": _att_to_dict(att, doc),
        "message": "Text ingestion started.",
    }, status_code=201)


@router.patch("/attachments/{att_id}")
async def update_attachment(
    att_id: str,
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update the when_to_use instruction on an existing KB attachment."""
    att = await _get_attachment(att_id, auth, db)
    when_to_use = body.get("whenToUse")
    if "whenToUse" in body:
        att.whenToUse = (when_to_use or "").strip() or None
    await db.commit()
    await db.refresh(att)
    # Load document for response
    doc_r = await db.execute(select(Document).where(Document.id == att.documentId))
    doc   = doc_r.scalar_one_or_none()
    return _att_to_dict(att, doc)


@router.delete("/attachments/{att_id}")
async def detach_document(
    att_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Detach a document from an agent (delete the KbAttachment record).
    The underlying Document record is NOT deleted so it can be re-attached.
    """
    att = await _get_attachment(att_id, auth, db)
    await db.delete(att)
    await db.commit()
    logger.info("[kb] Detached attachment %s", att_id)
    return {"success": True, "id": att_id}


@router.post("/test-query")
async def test_kb_query(
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Debug endpoint — runs the full retrieval pipeline for a test query and
    returns granular debug information:
      - which KB attachments exist for this agent
      - which were INCLUDED vs EXCLUDED by the when_to_use filter (with similarity scores)
      - raw semantic search results
      - raw BM25 results
      - RRF-merged results (pre-rerank)
      - cross-encoder re-ranked results
      - the final LLM answer

    This lets admins inspect retrieval quality without making a real call.
    """
    agent_id = body.get("agentId", "")
    query    = (body.get("query") or "").strip()

    if not agent_id or not query:
        raise HTTPException(status_code=400, detail="agentId and query are required")

    await _assert_agent_access(agent_id, auth, db)

    from app.services.rag_service import (
        _load_kb_attachments,
        _is_query_relevant_to_kb,
        _semantic_search,
        _bm25_search,
        query_documents,
        _rerank_with_cross_encoder,
        apply_policy_scoring,
        process_query,
    )

    # ── 1. KB attachments + when_to_use decisions ─────────────────────────────
    kb_attachments = await _load_kb_attachments(db, agent_id)

    included_ids: list[str] = []
    excluded_ids: list[str] = []
    att_decisions: list[dict] = []

    import asyncio as _aio
    from concurrent.futures import ThreadPoolExecutor

    def _evaluate_attachments():
        decisions = []
        for att in kb_attachments:
            doc_id     = att.get("documentId")
            when_to_use = att.get("whenToUse")
            relevant   = _is_query_relevant_to_kb(query, when_to_use)
            # Compute cosine similarity for display
            sim: Optional[float] = None
            if when_to_use:
                try:
                    from app.services.ingestion_service import _get_embedding_model
                    import numpy as np
                    model = _get_embedding_model()
                    vecs  = model.encode([query, when_to_use], convert_to_numpy=True, show_progress_bar=False)
                    a, b  = vecs[0], vecs[1]
                    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
                    sim   = round(float(np.dot(a, b) / (na * nb)), 4) if na and nb else None
                except Exception:
                    pass
            decisions.append({
                "attachmentId": att["id"],
                "documentId":   doc_id,
                "whenToUse":    when_to_use,
                "similarity":   sim,
                "included":     relevant,
            })
            if relevant and doc_id:
                included_ids.append(doc_id)
            elif doc_id:
                excluded_ids.append(doc_id)
        return decisions

    loop = _aio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        att_decisions = await loop.run_in_executor(pool, _evaluate_attachments)

    # Use None if no KB attachments (backward compat), otherwise filtered list
    allowed_doc_ids = included_ids if kb_attachments else None

    # ── 2. Raw semantic results ───────────────────────────────────────────────
    raw_semantic = await _semantic_search(
        auth.tenant_id, agent_id, query, top_k=10, allowed_doc_ids=allowed_doc_ids
    )

    # ── 3. Raw BM25 results ───────────────────────────────────────────────────
    raw_bm25 = await _bm25_search(
        auth.tenant_id, agent_id, query, top_k=10, allowed_doc_ids=allowed_doc_ids
    )

    # ── 4. RRF-merged results (pre-rerank) ────────────────────────────────────
    merged = await query_documents(
        auth.tenant_id, agent_id, query, top_k=10, allowed_doc_ids=allowed_doc_ids
    )

    # ── 5. Cross-encoder re-ranked results ───────────────────────────────────
    reranked = await _rerank_with_cross_encoder(query, list(merged), top_k=7)

    def _fmt(docs: list[dict]) -> list[dict]:
        return [
            {
                "snippet":        d.get("content", "")[:300],
                "source":         d.get("metadata", {}).get("source", "?"),
                "documentId":     d.get("metadata", {}).get("documentId"),
                "score":          round(d.get("score", 0), 4),
                "rerank_score":   round(d.get("rerank_score", 0), 4) if "rerank_score" in d else None,
                "retrieval_type": d.get("retrieval_type", "?"),
            }
            for d in docs
        ]

    # ── 6. Full pipeline answer ───────────────────────────────────────────────
    full = await process_query(db, auth.tenant_id, agent_id, query, session_id="_test_query_")

    return {
        "query":               query,
        "kbAttachments":       att_decisions,
        "includedDocIds":      included_ids,
        "excludedDocIds":      excluded_ids,
        "rawSemanticResults":  _fmt(raw_semantic),
        "rawBm25Results":      _fmt(raw_bm25),
        "mergedResults":       _fmt(merged),
        "rerankedResults":     _fmt(reranked),
        "answer":              full.get("response", ""),
        "model":               full.get("model", ""),
        "documentsRetrieved":  full.get("documentsRetrieved", 0),
    }
