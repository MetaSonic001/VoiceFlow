"""
Simple Whoosh-based BM25 index wrapper for sparse retrieval.

Provides a minimal API used by the agent: add_documents, delete_by_document_id, search
"""
import os
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

try:
    from whoosh import index
    from whoosh.fields import Schema, TEXT, ID, STORED
    from whoosh.analysis import StemmingAnalyzer
    from whoosh.qparser import MultifieldParser, OrGroup
    _WHOOSH_AVAILABLE = True
except Exception:
    _WHOOSH_AVAILABLE = False


class WhooshIndex:
    def __init__(self, index_dir: str):
        if not _WHOOSH_AVAILABLE:
            raise RuntimeError("whoosh package is not available; install 'whoosh' to enable BM25")

        self.index_dir = os.path.abspath(index_dir)
        os.makedirs(self.index_dir, exist_ok=True)

        schema = Schema(
            id=ID(stored=True, unique=True),
            doc_id=ID(stored=True),
            document=TEXT(stored=True, analyzer=StemmingAnalyzer()),
            metadata=STORED
        )

        if index.exists_in(self.index_dir):
            self.ix = index.open_dir(self.index_dir)
        else:
            self.ix = index.create_in(self.index_dir, schema)

    def add_documents(self, ids: List[str], texts: List[str], metadatas: List[Dict[str, Any]]):
        """Add or update documents in the Whoosh index.

        ids: unique ids for the chunk (e.g. document_chunk_{i})
        texts: chunk text
        metadatas: per-chunk metadata dict (must contain 'document_id' if available)
        """
        try:
            writer = self.ix.writer()
            for _id, txt, meta in zip(ids, texts, metadatas):
                doc_id = meta.get('document_id') if isinstance(meta, dict) else ''
                writer.update_document(id=str(_id), doc_id=str(doc_id), document=txt or '', metadata=json.dumps(meta or {}))
            writer.commit()
        except Exception:
            logger.exception("Failed to add documents to Whoosh index")

    def delete_by_document_id(self, document_id: str):
        """Delete all index entries for a given document_id."""
        try:
            writer = self.ix.writer()
            # Whoosh supports delete_by_term on stored ID fields; we stored doc_id separately
            writer.delete_by_term('doc_id', str(document_id))
            writer.commit()
        except Exception:
            logger.exception("Failed to delete entries by document_id in Whoosh index")

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Run a BM25 search and return top_k results with stored fields."""
        results = []
        try:
            with self.ix.searcher() as s:
                parser = MultifieldParser(['document'], schema=self.ix.schema, group=OrGroup)
                q = parser.parse(query)
                hits = s.search(q, limit=top_k)
                for h in hits:
                    meta = {}
                    try:
                        meta = json.loads(h.get('metadata') or '{}')
                    except Exception:
                        meta = {"raw_metadata": h.get('metadata')}
                    results.append({
                        'id': h.get('id'),
                        'document': h.get('document'),
                        'metadata': meta
                    })
        except Exception:
            logger.exception('Whoosh search failed')
        return results
