"""
voiceflow.knowledge_base — Developer-facing KnowledgeBase class.

A developer instantiates this with a folder path of documents and gets
semantic search back with one method call. ChromaDB, multilingual embeddings,
and chunking are handled internally.

Example:
    from voiceflow import KnowledgeBase

    kb = KnowledgeBase(collection_name="dental_clinic_kb")
    kb.add("./docs/")                     # ingest all files in a directory
    kb.add("./faq.pdf")                   # single file
    kb.add("https://example.com/policy")  # URL

    results = await kb.search("what are your hours?", top_k=5)
    print(results)   # plain text context ready to inject into LLM prompt
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger("voiceflow.knowledge_base")

_DEFAULT_EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


class KnowledgeBase:
    """
    Semantic knowledge base backed by ChromaDB + multilingual embeddings.
    Developers never touch ChromaDB, embeddings, or chunking directly.
    """

    def __init__(
        self,
        collection_name: str = "voiceflow_kb",
        embed_model: str = _DEFAULT_EMBED_MODEL,
        chroma_host: str = "localhost",
        chroma_port: int = 8030,
    ):
        self.collection_name = collection_name
        self.embed_model = embed_model
        self.chroma_host = chroma_host
        self.chroma_port = chroma_port
        self._client = None
        self._collection = None
        self._encoder = None

    def _get_encoder(self):
        if self._encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._encoder = SentenceTransformer(self.embed_model)
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required. "
                    "Install with: pip install sentence-transformers"
                )
        return self._encoder

    def _get_collection(self):
        if self._collection is None:
            try:
                import chromadb
                self._client = chromadb.HttpClient(
                    host=self.chroma_host, port=self.chroma_port
                )
                self._collection = self._client.get_or_create_collection(
                    self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            except ImportError:
                raise ImportError(
                    "chromadb is required. Install with: pip install chromadb"
                )
        return self._collection

    def add(self, source: Union[str, Path], **kwargs) -> "KnowledgeBase":
        """
        Add a knowledge source synchronously.
        source: directory path, file path, or URL.
        """
        asyncio.get_event_loop().run_until_complete(self.add_async(source, **kwargs))
        return self

    async def add_async(self, source: Union[str, Path], **kwargs) -> int:
        """
        Async version of add(). Returns the number of chunks indexed.
        """
        source = Path(source) if not str(source).startswith("http") else source
        texts: list[str] = []

        if isinstance(source, Path):
            if source.is_dir():
                for ext in ("*.txt", "*.md", "*.pdf", "*.docx"):
                    for file in source.glob(ext):
                        texts.extend(await self._read_file(file))
            elif source.is_file():
                texts.extend(await self._read_file(source))
        else:
            # URL
            texts.extend(await self._read_url(str(source)))

        if not texts:
            return 0

        return await self._index_chunks(texts)

    async def _read_file(self, path: Path) -> list[str]:
        """Read and chunk a file into text segments."""
        loop = asyncio.get_event_loop()
        try:
            if path.suffix.lower() == ".pdf":
                def _read():
                    try:
                        import pypdf
                        reader = pypdf.PdfReader(str(path))
                        return "\n\n".join(
                            page.extract_text() or "" for page in reader.pages
                        )
                    except ImportError:
                        return path.read_text(errors="ignore")
                text = await loop.run_in_executor(None, _read)
            else:
                text = path.read_text(errors="ignore")
            return _chunk_text(text, source=str(path))
        except Exception as exc:
            logger.warning("[kb] could not read %s: %s", path, exc)
            return []

    async def _read_url(self, url: str) -> list[str]:
        """Fetch a URL and chunk its text content."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                # Simple HTML stripping
                import re
                text = re.sub(r"<[^>]+>", " ", resp.text)
                text = re.sub(r"\s+", " ", text).strip()
            return _chunk_text(text, source=url)
        except Exception as exc:
            logger.warning("[kb] could not fetch %s: %s", url, exc)
            return []

    async def _index_chunks(self, chunks: list[str]) -> int:
        """Embed and index text chunks into ChromaDB."""
        if not chunks:
            return 0
        loop = asyncio.get_event_loop()
        encoder = self._get_encoder()
        embeddings = await loop.run_in_executor(None, lambda: encoder.encode(chunks).tolist())
        collection = self._get_collection()
        ids = [f"chunk_{id(collection)}_{i}_{hash(c)}" for i, c in enumerate(chunks)]
        collection.upsert(
            documents=chunks,
            embeddings=embeddings,
            ids=ids,
        )
        logger.info("[kb] indexed %d chunks into '%s'", len(chunks), self.collection_name)
        return len(chunks)

    async def search(self, query: str, top_k: int = 5) -> str:
        """
        Semantic search. Returns relevant context as a plain-text string
        ready to be injected into the LLM prompt.
        """
        if not query:
            return ""
        loop = asyncio.get_event_loop()
        encoder = self._get_encoder()
        query_emb = await loop.run_in_executor(None, lambda: encoder.encode([query]).tolist())
        collection = self._get_collection()
        results = collection.query(query_embeddings=query_emb, n_results=min(top_k, 10))
        docs = (results.get("documents") or [[]])[0]
        if not docs:
            return ""
        return "\n\n---\n\n".join(docs)

    def clear(self) -> None:
        """Delete all documents from this knowledge base."""
        try:
            col = self._get_collection()
            # Delete all items
            all_ids_result = col.get(include=[])
            ids = all_ids_result.get("ids", [])
            if ids:
                col.delete(ids=ids)
        except Exception as exc:
            logger.warning("[kb] clear failed: %s", exc)


def _chunk_text(text: str, source: str = "", chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping chunks.
    Tries to split on sentence boundaries first, then character count.
    """
    import re
    text = text.strip()
    if not text:
        return []

    # Split on double newlines (paragraphs) first
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) < chunk_size:
            current = (current + " " + para).strip()
        else:
            if current:
                chunks.append(current)
            # Para is too long → split by sentence
            if len(para) >= chunk_size:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sent in sentences:
                    if len(current) + len(sent) < chunk_size:
                        current = (current + " " + sent).strip()
                    else:
                        if current:
                            chunks.append(current)
                        current = sent
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks
