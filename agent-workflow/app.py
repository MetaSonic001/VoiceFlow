"""
RAG Agent Workflow API
A FastAPI-based RAG system with ChromaDB and Groq LLM
Compatible with Twilio webhooks
"""

import os
import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import JSONResponse, StreamingResponse, Response
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import chromadb
import asyncio
from fastapi.websockets import WebSocketDisconnect
from chromadb.config import Settings
from groq import Groq
from collections import OrderedDict
import threading
import sys
from pathlib import Path
import socket
import ssl
from urllib.parse import urlparse
import base64
import os as _os
import uuid
import time
from twilio.rest import Client as TwilioRestClient
from twilio_media import MediaStreamBridge, VoskASR
# Optional cross-encoder reranker (lazy import)
CrossEncoder = None
# Hybrid retrieval imports
from typing import List, Dict, Any
# Import summarizer and whoosh from the document-ingestion services package
try:
    ingestion_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'document-ingestion'))
    if ingestion_path not in sys.path:
        sys.path.insert(0, ingestion_path)
    from services.summarizer import Summarizer
    from services.whoosh_index import WhooshIndex
except Exception:
    # If import fails, set to None and log later when attempted
    Summarizer = None  # type: ignore
    WhooshIndex = None  # type: ignore
import numpy as np

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _safe_truncate(text: str, length: int = 300) -> str:
    if text is None:
        return ""
    t = str(text)
    t = t.replace('\n', ' ').replace('\r', ' ')
    if len(t) > length:
        return t[:length] + "..."
    return t


def _sanitize_reply_for_customer(text: str, max_length: int = 600) -> str:
    """Sanitize model answers for customer-facing TwiML output.

    - Remove explicit 'Document N' citations (e.g., 'According to Document 1')
    - Strip URLs to avoid reading long links in TTS
    - Collapse whitespace and truncate to max_length
    """
    if not text:
        return ""
    t = str(text)
    try:
        import re

        # Remove common citation patterns like 'According to Document 1,' or 'Document 2:'
        t = re.sub(r"(?i)according to\s+document\s+\d+[:,]?\s*", "", t)
        t = re.sub(r"(?i)document\s+\d+[:,]?\s*", "", t)

        # Remove any URLs (http(s):// or www.)
        t = re.sub(r"https?://\S+", "", t)
        t = re.sub(r"www\.\S+", "", t)

        # Remove stray file-sharing links or parentheses that include urls
        t = re.sub(r"\[.*?https?://.*?\]", "", t)

        # Collapse whitespace
        t = re.sub(r"\s+", " ", t).strip()

        # Truncate safely
        if len(t) > max_length:
            t = t[:max_length].rsplit(' ', 1)[0] + '...'
    except Exception:
        # Fallback: simple truncation
        t = t[:max_length]
    return t


def log_interaction(source: str, session_id: Optional[str], user_text: str, reply_text: str, extra: Optional[Dict[str, Any]] = None):
    """Structured log for voice/SSE/WebSocket interactions.

    source: e.g. 'twilio_voice', 'twilio_media_ws', 'sms'
    session_id: CallSid or other session id
    user_text: user-provided/transcribed text
    reply_text: agent reply
    extra: optional metadata dict
    """
    try:
        payload = {
            "source": source,
            "session_id": session_id,
            "user_text": _safe_truncate(user_text, 400),
            "reply_text": _safe_truncate(reply_text, 800),
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }
        if extra:
            payload.update(extra)
        logger.info("INTERACTION %s", json.dumps(payload, ensure_ascii=False))
    except Exception:
        logger.exception("Failed to log interaction")

# Initialize FastAPI app
app = FastAPI(
    title="RAG Agent Workflow API",
    description="A RAG-based agent that searches vector database and generates contextual answers",
    version="1.0.0"
)

# In-memory dedupe cache for Twilio speech webhooks to avoid processing
# duplicate SpeechResult posts (Twilio may retry or deliver duplicates).
# Keys are (call_sid, speech_hash). Values are the epoch timestamp when
# the event was processed. Entries older than SPEECH_DEDUPE_WINDOW_SEC are
# pruned lazily.
processed_speech_cache = {}
# window in seconds to consider duplicate requests
SPEECH_DEDUPE_WINDOW_SEC = int(os.getenv('SPEECH_DEDUPE_WINDOW_SEC', '5'))
processed_cache_lock = asyncio.Lock()

# ========================
# Configuration
# ========================
class Config:
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "documents")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    MAX_RESULTS = int(os.getenv("MAX_RESULTS", "3"))
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))
    # When the top retrieval similarity is at or above this threshold,
    # we will nudge the LLM to use the retrieved context and avoid
    # returning the canned 'I don't have enough information' reply.
    RETRIEVAL_CONFIDENCE_THRESHOLD = float(os.getenv("RETRIEVAL_CONFIDENCE_THRESHOLD", "0.5"))
    # How many of the top-ranked documents to summarize (lazy summarization)
    SUMMARIZE_TOP_K = int(os.getenv("SUMMARIZE_TOP_K", "3"))
    # Maximum number of candidates to rerank (keeps latency bounded)
    MAX_RERANK_CANDIDATES = int(os.getenv("MAX_RERANK_CANDIDATES", "10"))
    # Dense embedding model to use for fast retrieval
    # Default upgraded to all-mpnet-base-v2 for better semantic quality
    DENSE_EMBEDDING_MODEL = os.getenv("DENSE_EMBEDDING_MODEL", "all-mpnet-base-v2")
    # Cross-encoder reranker model (optional - toggled via USE_CROSS_RERANK)
    CROSS_RERANK_MODEL = os.getenv("CROSS_RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

    @classmethod
    def validate(cls):
        if not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        if not os.path.exists(cls.CHROMA_DB_PATH):
            raise ValueError(f"ChromaDB path not found: {cls.CHROMA_DB_PATH}")


def _env_flag_true(name: str) -> bool:
    """Utility: interpret common truthy env var values as True."""
    return os.getenv(name, "false").lower() in ("1", "true", "yes", "on")


# Track active media websocket connections. Keys are connection ids.



# Monitor/fallback removed: in the minimal Start/Stream-only approach we
# rely on Twilio's media stream to attach and the websocket handler to drive
# the conversation. If you need a fallback for flaky tunnels, re-introduce
# a monitor that updates the live call to a Gather-based TwiML URL.

# ========================
# Pydantic Models
# ========================
class QueryRequest(BaseModel):
    query: str = Field(..., description="The user's question or query")
    user_id: Optional[str] = Field(None, description="Optional user identifier")
    stream: bool = Field(False, description="Enable streaming response")
    
class TwilioWebhookRequest(BaseModel):
    Body: str = Field(..., description="Message body from Twilio")
    From: Optional[str] = Field(None, description="Sender phone number")
    MessageSid: Optional[str] = Field(None, description="Twilio message ID")

class QueryResponse(BaseModel):
    success: bool
    query: str
    answer: Optional[str] = None
    sources: Optional[list] = None
    error: Optional[str] = None
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None

class StreamChunk(BaseModel):
    type: str  # "start", "content", "sources", "end", "error"
    content: Optional[str] = None
    sources: Optional[list] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# ========================
# RAG Agent Class
# ========================
class RAGAgent:
    def __init__(self):
        """Initialize the RAG Agent with ChromaDB and Groq client"""
        try:
            # Validate configuration
            Config.validate()
            
            # Initialize ChromaDB
            logger.info(f"Initializing ChromaDB at: {Config.CHROMA_DB_PATH}")
            self.chroma_client = chromadb.PersistentClient(
                path=Config.CHROMA_DB_PATH,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            try:
                self.collection = self.chroma_client.get_or_create_collection(
                    name=Config.COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"Loaded collection: {Config.COLLECTION_NAME}")
            except Exception as e:
                logger.error(f"Collection not found: {e}")
                raise ValueError(f"Collection '{Config.COLLECTION_NAME}' not found in ChromaDB")

            # Ensure we use the same embedder as ingestion (so embeddings line up)
            # Add document-ingestion services folder to path so we can import the embedder
            try:
                ingestion_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'document-ingestion'))
                if ingestion_path not in sys.path:
                    sys.path.insert(0, ingestion_path)
                from services.embedder import TextEmbedder
                # Instantiate embedder (loads SentenceTransformer model)
                # Use a fast MiniLM model for low-latency retrieval
                self.embedder = TextEmbedder(model_name=Config.DENSE_EMBEDDING_MODEL)
                logger.info("TextEmbedder initialized for agent (shared embedding model)")
            except Exception as e:
                logger.warning(f"Failed to initialize shared TextEmbedder: {e}")
                self.embedder = None
            # Initialize a small in-memory LRU cache for query embeddings to speed up repeated queries
            # Thread-safe via a lock for multi-threaded uvicorn workers
            self._emb_cache_max = int(os.getenv('EMBED_CACHE_SIZE', '1024'))
            self._emb_cache: "OrderedDict[str, List[float]]" = OrderedDict()
            self._emb_cache_lock = threading.Lock()
            # Initialize summarizer
            try:
                # prefer a small CPU-friendly summarizer
                self.summarizer = Summarizer()
            except Exception:
                logger.exception("Failed to initialize summarizer; summaries will be passthrough")
                self.summarizer = None

            # Initialize Whoosh index wrapper for BM25 (uses document-ingestion whoosh index)
            try:
                whoosh_dir = os.path.join(Config.CHROMA_DB_PATH, 'whoosh_index')
                self.whoosh = WhooshIndex(whoosh_dir)
            except Exception:
                logger.exception("Failed to initialize Whoosh index wrapper; BM25 disabled")
                self.whoosh = None
            
            # Initialize Groq client
            self.groq_client = Groq(api_key=Config.GROQ_API_KEY)
            logger.info("Groq client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG Agent: {e}")
            raise

    def _load_cross_encoder(self):
        """Lazily load the CrossEncoder model when needed."""
        global CrossEncoder
        if CrossEncoder is not None:
            return CrossEncoder
        try:
            from sentence_transformers import CrossEncoder as _CrossEncoder
            CrossEncoder = _CrossEncoder
            return CrossEncoder
        except Exception as e:
            logger.warning(f"Failed to import CrossEncoder: {e}")
            return None

    # ------------------
    # Embedding cache helpers
    # ------------------
    def _cache_get(self, key: str):
        with self._emb_cache_lock:
            try:
                if key in self._emb_cache:
                    # move to end (most recently used)
                    val = self._emb_cache.pop(key)
                    self._emb_cache[key] = val
                    return val
            except Exception:
                pass
        return None

    def _cache_set(self, key: str, value):
        with self._emb_cache_lock:
            try:
                if key in self._emb_cache:
                    self._emb_cache.pop(key)
                self._emb_cache[key] = value
                # evict oldest if over capacity
                while len(self._emb_cache) > self._emb_cache_max:
                    self._emb_cache.popitem(last=False)
            except Exception:
                pass

    def _embed_text(self, text: str):
        """Compute or retrieve cached embedding for a single text."""
        if not self.embedder or not hasattr(self.embedder, 'model'):
            return None
        key = f"t:{text}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        try:
            emb = self.embedder.model.encode(text, show_progress_bar=False, convert_to_numpy=True)
            # normalize to python list
            if hasattr(emb, 'tolist'):
                emb_list = emb.tolist()
                if isinstance(emb_list, list) and len(emb_list) > 0 and isinstance(emb_list[0], list):
                    emb_list = emb_list[0]
            else:
                emb_list = list(emb)
            self._cache_set(key, emb_list)
            return emb_list
        except Exception:
            logger.exception('Failed to compute embedding (sync)')
            return None

    async def _embed_text_async(self, text: str):
        """Async wrapper for embedding single text (uses thread to avoid blocking)."""
        if not self.embedder or not hasattr(self.embedder, 'model'):
            return None
        key = f"t:{text}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        try:
            emb = await asyncio.to_thread(self.embedder.model.encode, text, show_progress_bar=False, convert_to_numpy=True)
            if hasattr(emb, 'tolist'):
                emb_list = emb.tolist()
                if isinstance(emb_list, list) and len(emb_list) > 0 and isinstance(emb_list[0], list):
                    emb_list = emb_list[0]
            else:
                emb_list = list(emb)
            self._cache_set(key, emb_list)
            return emb_list
        except Exception:
            logger.exception('Failed to compute embedding (async)')
            return None

    async def _embed_texts_async(self, texts: List[str]):
        """Embed a batch of texts, leveraging cache where possible and computing the rest in one batch call."""
        results = [None] * len(texts)
        to_compute = []  # (index, text)
        for i, t in enumerate(texts):
            key = f"t:{t}"
            cached = self._cache_get(key)
            if cached is not None:
                results[i] = cached
            else:
                to_compute.append((i, t))

        if to_compute and self.embedder and hasattr(self.embedder, 'model'):
            batch_texts = [t for (_, t) in to_compute]
            try:
                emb_batch = await asyncio.to_thread(self.embedder.model.encode, batch_texts, show_progress_bar=False, convert_to_numpy=True)
                # normalize emb_batch to list of vectors
                if hasattr(emb_batch, 'tolist'):
                    emb_list_batch = emb_batch.tolist()
                else:
                    emb_list_batch = [list(e) for e in emb_batch]

                for (idx, _), emb_vec in zip(to_compute, emb_list_batch):
                    # if emb_vec is nested (single item), flatten
                    if isinstance(emb_vec, list) and len(emb_vec) > 0 and isinstance(emb_vec[0], list):
                        emb_vec = emb_vec[0]
                    results[idx] = emb_vec
                    self._cache_set(f"t:{texts[idx]}", emb_vec)
            except Exception:
                logger.exception('Batch embedding failed; falling back to per-item compute')
                for idx, txt in to_compute:
                    emb = await self._embed_text_async(txt)
                    results[idx] = emb

        return results

    def cross_rerank(self, candidates: List[Dict[str, Any]], query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Rerank candidate documents using a cross-encoder model. Expects
        `candidates` as a list of dicts with 'document' and 'metadata'.
        Returns the top_k reranked candidates with added 'score' field.
        """
        if not _env_flag_true('USE_CROSS_RERANK'):
            return candidates[:top_k]

        CE = self._load_cross_encoder()
        if CE is None:
            logger.warning('CrossEncoder not available; skipping cross-rerank')
            return candidates[:top_k]

        model_name = os.getenv('CROSS_RERANK_MODEL', Config.CROSS_RERANK_MODEL)
        try:
            ce_model = CE(model_name)
        except Exception as e:
            logger.exception(f'Failed to load CrossEncoder model {model_name}: {e}')
            return candidates[:top_k]

        # Build pairs (query, doc) for scoring
        docs = [c['document'] for c in candidates]
        pairs = [[query, d] for d in docs]
        try:
            scores = ce_model.predict(pairs)
        except Exception:
            logger.exception('CrossEncoder scoring failed')
            return candidates[:top_k]

        scored = []
        for c, s in zip(candidates, scores):
            new = c.copy()
            try:
                new['score'] = float(s)
            except Exception:
                new['score'] = 0.0
            scored.append(new)

        scored.sort(key=lambda x: x.get('score', 0.0), reverse=True)
        return scored[:top_k]
    
    def process_query(self, query: str) -> str:
        """
        Step 2: Process and clean the query
        """
        # Basic query processing - trim whitespace and validate
        processed = query.strip()
        if not processed:
            raise ValueError("Query cannot be empty")
        
        logger.info(f"Processed query: {processed}")
        return processed
    
    def search_embeddings(self, query: str) -> Dict[str, Any]:
        """
        Step 3: Search for relevant documents using vector similarity
        """
        try:
            # Prefer to compute the query embedding with the same embedder used by ingestion
            if self.embedder and hasattr(self.embedder, 'model'):
                try:
                    # Use cache-aware single-text embed helper
                    q_vec = self._embed_text(query)
                    if q_vec is None:
                        raise RuntimeError('Embedding unavailable')
                    results = self.collection.query(
                        query_embeddings=[q_vec],
                        n_results=Config.MAX_RESULTS,
                        include=["documents", "metadatas", "distances"]
                    )
                except Exception as e:
                    logger.warning(f"Failed to compute query embedding with shared embedder: {e}; falling back to text query")
                    results = self.collection.query(
                        query_texts=[query],
                        n_results=Config.MAX_RESULTS,
                        include=["documents", "metadatas", "distances"]
                    )
            else:
                # Fallback: query by text (less robust)
                results = self.collection.query(
                    query_texts=[query],
                    n_results=Config.MAX_RESULTS,
                    include=["documents", "metadatas", "distances"]
                )

            # Debug: log raw results for inspection
            try:
                logger.debug(f"Raw vector search results: {results}")
            except Exception:
                logger.debug("Raw results logging failed")

            # Check if we got any results
            if not results or not results.get('documents') or not results['documents'][0]:
                logger.warning("No documents found in vector search")
                return {
                    "found": False,
                    "documents": [],
                    "metadatas": [],
                    "distances": []
                }

            # Extract lists
            documents = results['documents'][0]
            metadatas = results.get('metadatas', [[]])[0] if results.get('metadatas') else [{}] * len(documents)
            distances = results.get('distances', [[]])[0] if results.get('distances') else [None] * len(documents)

            # Convert distances to similarity scores (assume distance in [0,1], smaller=closer)
            # similarity = 1 - distance. If distance is None, keep similarity as None.
            similarities = []
            for d in distances:
                try:
                    if d is None:
                        similarities.append(None)
                    else:
                        similarities.append(1.0 - float(d))
                except Exception:
                    similarities.append(None)

            # Build filtered results based on similarity threshold. If similarity is None, include the result.
            filtered_results = []
            for doc, meta, dist, sim in zip(documents, metadatas, distances, similarities):
                include = False
                if sim is None:
                    include = True
                else:
                    include = sim >= Config.SIMILARITY_THRESHOLD

                if include:
                    filtered_results.append({
                        "document": doc,
                        "metadata": meta,
                        "distance": dist,
                        "similarity": sim
                    })

            if not filtered_results:
                logger.warning(f"No documents passed similarity threshold ({Config.SIMILARITY_THRESHOLD}). Raw distances: {distances}, similarities: {similarities}")

                # FALLBACK: If no documents pass the similarity threshold, return
                # the top-N raw results instead of returning an empty set. This
                # prevents the agent from always answering with 'no information'
                # in situations where the corpus is small or similarity scores are
                # generally lower across environments. The environment variable
                # SIMILARITY_THRESHOLD still controls normal filtering behavior.
                logger.info("No documents passed threshold; falling back to top-N raw results (below threshold)")

                # Build fallback list from the original results (preserve order)
                fallback_results = []
                for doc, meta, dist, sim in zip(documents, metadatas, distances, similarities):
                    fallback_results.append({
                        "document": doc,
                        "metadata": meta,
                        "distance": dist,
                        "similarity": sim
                    })

                # Limit fallback to MAX_RESULTS
                fallback_results = fallback_results[: Config.MAX_RESULTS]

                return {
                    "found": True,
                    "documents": [r["document"] for r in fallback_results],
                    "metadatas": [r["metadata"] for r in fallback_results],
                    "distances": [r["distance"] for r in fallback_results],
                    # Indicate callers that fallback was used
                    "fallback_used": True
                }

            logger.info(f"Found {len(filtered_results)} relevant documents")
            return {
                "found": True,
                "documents": [r["document"] for r in filtered_results],
                "metadatas": [r["metadata"] for r in filtered_results],
                "distances": [r["distance"] for r in filtered_results]
            }
            
        except Exception as e:
            logger.error(f"Error during vector search: {e}")
            raise

    async def search_embeddings_async(self, query: str) -> Dict[str, Any]:
        """
        Async version of search_embeddings that runs the embedder.encode call
        in a thread so it doesn't block the event loop. Used by async streaming
        paths.
        """
        try:
            # Prefer to compute the query embedding with the same embedder used by ingestion
            if self.embedder and hasattr(self.embedder, 'model'):
                try:
                    # Run the blocking encode in a thread
                    q_vec = await self._embed_text_async(query)
                    if q_vec is None:
                        raise RuntimeError('Embedding unavailable (async)')
                    results = self.collection.query(
                        query_embeddings=[q_vec],
                        n_results=Config.MAX_RESULTS,
                        include=["documents", "metadatas", "distances"]
                    )
                except Exception as e:
                    logger.warning(f"Failed to compute query embedding with shared embedder (async): {e}; falling back to text query")
                    results = self.collection.query(
                        query_texts=[query],
                        n_results=Config.MAX_RESULTS,
                        include=["documents", "metadatas", "distances"]
                    )
            else:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=Config.MAX_RESULTS,
                    include=["documents", "metadatas", "distances"]
                )

            if not results or not results.get('documents') or not results['documents'][0]:
                logger.warning("No documents found in vector search")
                return {
                    "found": False,
                    "documents": [],
                    "metadatas": [],
                    "distances": []
                }

            documents = results['documents'][0]
            metadatas = results.get('metadatas', [[]])[0] if results.get('metadatas') else [{}] * len(documents)
            distances = results.get('distances', [[]])[0] if results.get('distances') else [None] * len(documents)

            similarities = []
            for d in distances:
                try:
                    if d is None:
                        similarities.append(None)
                    else:
                        similarities.append(1.0 - float(d))
                except Exception:
                    similarities.append(None)

            filtered_results = []
            for doc, meta, dist, sim in zip(documents, metadatas, distances, similarities):
                include = False
                if sim is None:
                    include = True
                else:
                    include = sim >= Config.SIMILARITY_THRESHOLD

                if include:
                    filtered_results.append({
                        "document": doc,
                        "metadata": meta,
                        "distance": dist,
                        "similarity": sim
                    })

            if not filtered_results:
                logger.warning(f"No documents passed similarity threshold ({Config.SIMILARITY_THRESHOLD}). Raw distances: {distances}, similarities: {similarities}")
                logger.info("No documents passed threshold; falling back to top-N raw results (below threshold)")
                fallback_results = []
                for doc, meta, dist, sim in zip(documents, metadatas, distances, similarities):
                    fallback_results.append({
                        "document": doc,
                        "metadata": meta,
                        "distance": dist,
                        "similarity": sim
                    })
                fallback_results = fallback_results[: Config.MAX_RESULTS]
                return {
                    "found": True,
                    "documents": [r["document"] for r in fallback_results],
                    "metadatas": [r["metadata"] for r in fallback_results],
                    "distances": [r["distance"] for r in fallback_results],
                    "fallback_used": True
                }

            logger.info(f"Found {len(filtered_results)} relevant documents")
            return {
                "found": True,
                "documents": [r["document"] for r in filtered_results],
                "metadatas": [r["metadata"] for r in filtered_results],
                "distances": [r["distance"] for r in filtered_results]
            }
        except Exception as e:
            logger.error(f"Error during async vector search: {e}")
            raise

    def _cosine_sim(self, a: List[float], b: List[float]) -> float:
        try:
            a_arr = np.array(a, dtype=np.float32)
            b_arr = np.array(b, dtype=np.float32)
            # normalize
            if np.linalg.norm(a_arr) == 0 or np.linalg.norm(b_arr) == 0:
                return 0.0
            return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))
        except Exception:
            return 0.0

    def hybrid_retrieve_and_rerank(self, query: str, top_k_bm25: int = 3, top_k_dense: int = 3) -> Dict[str, Any]:
        """Run BM25 and dense retrieval, union the top results, dedupe, limit to a bounded
        number of candidates, rerank by cosine similarity using the embedder, and lazily
        summarize only the top N results to keep latency low.

        Behavior:
        - BM25 top_k_bm25 + dense top_k_dense are retrieved
        - unioned (BM25 first), duplicates removed by exact text
        - candidates capped to Config.MAX_RERANK_CANDIDATES (<=10)
        - compute cosine between query embedding and candidate embeddings
        - sort descending and return up to MAX_RERANK_CANDIDATES results
        - summarize only top Config.SUMMARIZE_TOP_K documents (lazy summarization)
        """
        timings = {}
        t0 = time.time()

        # 1) BM25
        bm25_results = []
        if self.whoosh:
            try:
                bm25_results = self.whoosh.search(query, top_k_bm25)
            except Exception:
                logger.exception("BM25 search failed")
                bm25_results = []
        t1 = time.time()
        timings['bm25_ms'] = int((t1 - t0) * 1000)

        # 2) Dense
        dense_results = []
        q_emb = None
        if self.embedder and hasattr(self.embedder, 'model'):
            try:
                # compute query embedding using cache-aware helper
                q_emb = self._embed_text(query)
            except Exception:
                logger.exception("Query embedding failed")
                q_emb = None

        if q_emb is not None:
            try:
                dense_raw = self.collection.query(
                    query_embeddings=[q_emb],
                    n_results=top_k_dense,
                    include=['documents', 'metadatas', 'distances']
                )
                if dense_raw and dense_raw.get('documents'):
                    docs = dense_raw['documents'][0]
                    metas = dense_raw.get('metadatas', [[]])[0]
                    for i, doc in enumerate(docs):
                        dense_results.append({'document': doc, 'metadata': metas[i] if metas else {}, 'source': 'dense'})
            except Exception:
                logger.exception("Dense retrieval failed")
        t2 = time.time()
        timings['dense_ms'] = int((t2 - t1) * 1000)

        # 3) Union BM25 + Dense (BM25 first), dedupe by exact text
        combined = []
        seen_texts = set()
        for r in bm25_results:
            txt = r.get('document', '')
            if not txt or txt in seen_texts:
                continue
            seen_texts.add(txt)
            combined.append({'document': txt, 'metadata': r.get('metadata', {}), 'source': 'bm25'})
        for r in dense_results:
            txt = r.get('document', '')
            if not txt or txt in seen_texts:
                continue
            seen_texts.add(txt)
            combined.append({'document': txt, 'metadata': r.get('metadata', {}), 'source': 'dense'})
        # 4) Cap candidates to a bounded number for reranking
        # Keep the candidate set small to bound latency
        max_candidates = max(1, int(getattr(Config, 'MAX_RERANK_CANDIDATES', 10)))
        candidates = combined[: max_candidates]

        # 5) Optional cross-encoder rerank (better ranking at small scale)
        use_ce = _env_flag_true('USE_CROSS_RERANK')
        if use_ce:
            try:
                ce_top_k = max(1, min(len(candidates), int(os.getenv('CROSS_RERANK_TOP_K', '5'))))
                ce_scored = self.cross_rerank(candidates, query, top_k=ce_top_k)
                # ce_scored contains scored dicts; use it as final candidate set
                final = ce_scored
            except Exception:
                logger.exception('Cross-encoder rerank failed; falling back to embedder rerank')
                final = None
        else:
            final = None

        # 6) If cross-encoder wasn't used or failed, fallback to embedder cosine reranking
        if final is None:
            reranked = []
            if q_emb is not None and self.embedder and candidates:
                try:
                    docs_texts = [c['document'] for c in candidates]
                    # embed candidate documents using cache-aware batch helper
                    doc_embs = self._embed_texts(docs_texts)
                    for doc, emb in zip(candidates, doc_embs):
                        if emb is None:
                            sim = 0.0
                        else:
                            sim = self._cosine_sim(q_emb, emb)
                        reranked.append({'document': doc['document'], 'metadata': doc.get('metadata', {}), 'score': sim})
                except Exception:
                    logger.exception('Reranking failed using embedder')

            # Fallback if reranking failed
            if not reranked and candidates:
                reranked = [{'document': c['document'], 'metadata': c.get('metadata', {}), 'score': 0.0} for c in candidates]

            # Sort and trim to configured maximum
            reranked.sort(key=lambda x: x.get('score', 0.0), reverse=True)
            final = reranked[: max_candidates]

        t3 = time.time()
        timings['rerank_ms'] = int((t3 - t2) * 1000)

        # 6) Lazy summarization: only summarize top SUMMARIZE_TOP_K results
        summaries = []
        try:
            top_texts = [f"{i+1}. {r['document']}" for i, r in enumerate(final[: Config.SUMMARIZE_TOP_K])]
            if self.summarizer and top_texts:
                summaries_top = self.summarizer.summarize(top_texts, max_length=120)
            else:
                summaries_top = [t[:300] for t in top_texts]

            # Fill summaries array aligning with final results: summarized top-N and raw previews for the rest
            for i, r in enumerate(final):
                if i < len(summaries_top):
                    summaries.append(summaries_top[i])
                else:
                    txt = r['document']
                    summaries.append(txt[:300])
        except Exception:
            logger.exception('Summarization failed; using raw texts')
            summaries = [r['document'][:300] for r in final]

        return {
            'documents': [r['document'] for r in final],
            'metadatas': [r.get('metadata', {}) for r in final],
            'scores': [r.get('score', 0.0) for r in final],
            'summaries': summaries,
            'timings': timings,
            'found': bool(final)
        }
    
    def build_rag_prompt(self, query: str, search_results: Dict[str, Any]) -> str:
        """
        Step 3.2: Build RAG prompt with context from search results
        """
        # Support both legacy search_results (with 'found' boolean) and
        # hybrid results which contain 'summaries' and 'documents'.
        if not search_results:
            return None

        # If summaries are present (hybrid retrieval), use them as compressed context
        if isinstance(search_results, dict) and search_results.get('summaries'):
            context = "\n".join([f"Summary {i+1}: {s}" for i, s in enumerate(search_results.get('summaries', []))])
        else:
            # Build context from retrieved documents (legacy format)
            try:
                docs = search_results.get('documents') if isinstance(search_results, dict) else search_results['documents']
            except Exception:
                return None
            context_parts = []
            for i, doc in enumerate(docs, 1):
                context_parts.append(f"Document {i}:\n{doc}\n")
            context = "\n".join(context_parts)
        
        # Build the prompt
        prompt = f"""You are a helpful assistant that answers questions based ONLY on the provided context.

Context from knowledge base:
{context}

Instructions:
1. Answer the question using ONLY information from the context above
2. If the context doesn't contain enough information to answer the question, say "I don't have enough information in my knowledge base to answer that question."
3. Do not make up or infer information that isn't explicitly in the context
4. Be concise and accurate
5. If you reference information, indicate which document it came from

Question: {query}

Answer:"""
        
        logger.info("RAG prompt built successfully")
        return prompt
    
    def generate_answer(self, prompt: str) -> str:
        """
        Step 3.3: Generate answer using Groq LLM (non-streaming)
        """
        if not prompt:
            return "I don't have enough information in my knowledge base to answer that question."
        
        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions based only on provided context. Never hallucinate or make up information."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=Config.GROQ_MODEL,
                temperature=0.1,  # Low temperature for more factual responses
                max_tokens=1024,
                stream=False
            )
            
            answer = chat_completion.choices[0].message.content
            logger.info("Answer generated successfully")
            return answer
            
        except Exception as e:
            logger.error(f"Error generating answer with Groq: {e}")
            raise
    
    def generate_answer_stream(self, prompt: str):
        """
        Step 3.3: Generate answer using Groq LLM with streaming
        Yields chunks of text as they're generated
        """
        if not prompt:
            yield "I don't have enough information in my knowledge base to answer that question."
            return
        
        try:
            stream = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions based only on provided context. Never hallucinate or make up information."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=Config.GROQ_MODEL,
                temperature=0.1,
                max_tokens=1024,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
            
            logger.info("Streaming answer generated successfully")
            
        except Exception as e:
            logger.error(f"Error generating streaming answer with Groq: {e}")
            yield f"\n\n[Error: {str(e)}]"
    
    def format_answer(self, answer: str, search_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 4: Format the answer with metadata
        """
        formatted = {
            "answer": answer.strip(),
            "sources": []
        }
        # Add source information when available. Support both legacy and hybrid formats.
        try:
            if isinstance(search_results, dict) and search_results.get('documents'):
                # If distances present (legacy), convert to similarity
                if search_results.get('distances'):
                    for i, (doc, meta, dist) in enumerate(zip(
                        search_results.get('documents', []),
                        search_results.get('metadatas', []),
                        search_results.get('distances', [])
                    ), 1):
                        sim = None
                        try:
                            sim = round(1 - float(dist), 3) if dist is not None else None
                        except Exception:
                            sim = None
                        source = {
                            "document_number": i,
                            "similarity_score": sim,
                            "metadata": meta,
                            "preview": doc[:200] + "..." if len(doc) > 200 else doc
                        }
                        formatted["sources"].append(source)
                # If hybrid 'scores' exist (reranker), use them
                elif search_results.get('scores'):
                    for i, (doc, meta, score) in enumerate(zip(
                        search_results.get('documents', []),
                        search_results.get('metadatas', []),
                        search_results.get('scores', [])
                    ), 1):
                        source = {
                            "document_number": i,
                            "similarity_score": round(float(score), 3) if score is not None else None,
                            "metadata": meta,
                            "preview": doc[:200] + "..." if len(doc) > 200 else doc
                        }
                        formatted["sources"].append(source)
        except Exception:
            logger.exception("Failed to format sources from search_results")
        
        return formatted
    
    def process(self, query: str, user_id: Optional[str] = None) -> QueryResponse:
        """
        Main workflow: Execute all steps (non-streaming)
        """
        start_time = datetime.now()
        timings = {}
        
        try:
            # Step 1: Receive query (already done)
            logger.info(f"[STEP 1] Received query: {query[:100]}...")
            
            # Step 2: Process query
            logger.info("[STEP 2] Processing query...")
            t0 = datetime.now()
            processed_query = self.process_query(query)
            t1 = datetime.now()
            timings['process_query_ms'] = int((t1 - t0).total_seconds() * 1000)
            
            # Step 3: Search embeddings
            logger.info("[STEP 3.1] Searching vector database...")
            t2 = datetime.now()
            search_results = self.hybrid_retrieve_and_rerank(processed_query, top_k_bm25=3, top_k_dense=3)
            t3 = datetime.now()
            timings['vector_search_ms'] = int((t3 - t2).total_seconds() * 1000)
            
            # Check if we found relevant documents
            # hybrid_retrieve returns a dict with 'documents' list; treat empty as not found
            if not search_results or not search_results.get('documents'):
                logger.warning("No relevant documents found")
                return QueryResponse(
                    success=True,
                    query=query,
                    answer="I don't have enough information in my knowledge base to answer that question. Please ask something related to the documents I have access to.",
                    sources=[],
                    timestamp=datetime.now().isoformat(),
                    metadata={
                        "user_id": user_id,
                        "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000),
                        "documents_found": 0
                    }
                )
            
            # Step 3.2: Build RAG prompt
            logger.info("[STEP 3.2] Building RAG prompt...")
            t4 = datetime.now()
            # Build RAG prompt using summaries (compressed) when available
            try:
                summaries = search_results.get('summaries') if isinstance(search_results, dict) else None
                if summaries:
                    # Build a condensed context from summaries
                    context = "\n".join([f"Summary {i+1}: {s}" for i, s in enumerate(summaries)])
                    prompt = f"""You are a helpful assistant that answers questions based ONLY on the provided context.\n\nContext summaries from knowledge base:\n{context}\n\nInstructions:\n1. Answer the question using ONLY information from the context above\n2. If the context doesn't contain enough information to answer the question, say \"I don't have enough information in my knowledge base to answer that question.\"\n3. Do not make up or infer information that isn't explicitly in the context\n4. Be concise and accurate\n5. Do NOT include raw document URLs or citations in the spoken response\n\nQuestion: {processed_query}\n\nAnswer:"""
                else:
                    prompt = self.build_rag_prompt(processed_query, search_results)
            except Exception:
                logger.exception('Failed to build prompt from summaries; falling back to full context')
                prompt = self.build_rag_prompt(processed_query, search_results)
            # Compute top similarity (if distances are present) so we can
            # decide whether to instruct the LLM more strongly to use the
            # retrieved context. Distances returned by Chroma are used to
            # compute similarity as (1 - distance) when available.
            top_similarity = None
            try:
                dlist = search_results.get('distances')
                if dlist and len(dlist) > 0 and dlist[0] is not None:
                    top_similarity = 1.0 - float(dlist[0])
            except Exception:
                top_similarity = None

            # Always log the top similarity (if available) for observability
            try:
                if top_similarity is not None:
                    logger.info(f"Top retrieval similarity: {top_similarity:.3f}")
                else:
                    logger.info("Top retrieval similarity: unavailable")
            except Exception:
                pass

            # If the top similarity meets or exceeds the configured threshold,
            # add an explicit instruction in the prompt to prioritize using the
            # provided context and to avoid replying with a canned refusal.
            try:
                if top_similarity is not None and top_similarity >= Config.RETRIEVAL_CONFIDENCE_THRESHOLD:
                    # Strong, explicit instruction when retrieval confidence is high.
                    # For a customer-facing assistant we want short, relevant answers
                    # using the retrieved context. Do NOT mention or cite document
                    # identifiers; respond in concise, customer-friendly language.
                    prompt += (
                        f"\n\n[RETRIEVAL_CONFIDENCE={top_similarity:.2f}] IMPORTANT: The context above is highly relevant. "
                        "Answer the user's question directly and succinctly using ONLY the provided context. "
                        "Do not mention or cite document names, numbers, or sources. "
                        "If the information needed is present in the context, provide it in a short, customer-facing sentence or two. "
                        "If the retrieved content is ambiguous or conflicting, give a concise summary of the key points without referencing which document said what. "
                        "Only use a refusal like 'I don't have enough information' if the answer truly cannot be found in the provided context."
                    )
                    logger.info(f"Top retrieval similarity {top_similarity:.3f} >= threshold; applying strong prompt instruction to use context (no citations)")
            except Exception:
                logger.exception("Failed to adjust prompt for retrieval confidence")

            t5 = datetime.now()
            timings['prompt_build_ms'] = int((t5 - t4).total_seconds() * 1000)
            
            # Step 3.3: Generate answer
            logger.info("[STEP 3.3] Generating answer with LLM...")
            t6 = datetime.now()
            raw_answer = self.generate_answer(prompt)
            t7 = datetime.now()
            timings['llm_ms'] = int((t7 - t6).total_seconds() * 1000)
            
            # Step 4: Format answer
            logger.info("[STEP 4] Formatting answer...")
            t8 = datetime.now()
            formatted = self.format_answer(raw_answer, search_results)
            t9 = datetime.now()
            timings['format_ms'] = int((t9 - t8).total_seconds() * 1000)

            # If the LLM returned the canned 'I don't have enough information' reply
            # but we actually retrieved one or more documents, surface a short
            # preview from the top result so callers (or Twilio) can see that
            # there is some relevant context available. This helps avoid cases
            # where the LLM declines to answer even though retrieval found text.
            try:
                canned_msg = "I don't have enough information in my knowledge base to answer that question."
                if isinstance(raw_answer, str) and canned_msg in raw_answer and (isinstance(search_results, dict) and search_results.get('documents')):
                    # Do not append previews in customer-facing output; set metadata flag
                    logger.info("LLM returned canned refusal but retrieval found documents; setting metadata flag")
                    timings['fallback_retrieval_found_but_llm_refused'] = True
            except Exception:
                logger.exception("Failed to detect canned LLM refusal with retrieval present")
            
            # Step 5: Return response
            logger.info("[STEP 5] Returning response")
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return QueryResponse(
                success=True,
                query=query,
                answer=formatted["answer"],
                sources=formatted["sources"],
                timestamp=datetime.now().isoformat(),
                metadata={
                    "user_id": user_id,
                    "processing_time_ms": processing_time,
                    "timings_ms": timings,
                    "documents_found": len(search_results["documents"]),
                    **({"top_similarity": round(top_similarity, 3)} if 'top_similarity' in locals() and top_similarity is not None else {})
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return QueryResponse(
                success=False,
                query=query,
                error=str(e),
                timestamp=datetime.now().isoformat(),
                metadata={"user_id": user_id}
            )
    
    async def process_stream(self, query: str, user_id: Optional[str] = None):
        """
        Main workflow with streaming: Execute all steps and stream the response
        Yields JSON chunks as Server-Sent Events
        """
        start_time = datetime.now()
        timings = {}

        try:
            # Step 1: Receive query
            logger.info(f"[STREAM] Received query: {query[:100]}...")

            # Send start event
            yield {
                "type": "start",
                "metadata": {
                    "query": query,
                    "timestamp": datetime.now().isoformat()
                }
            }

            # Step 2: Process query
            logger.info("[STREAM] Processing query...")
            t0 = datetime.now()
            processed_query = self.process_query(query)
            t1 = datetime.now()
            timings['process_query_ms'] = int((t1 - t0).total_seconds() * 1000)

            # Step 3: Hybrid retrieval (BM25 + dense) - do sync call (fast)
            logger.info("[STREAM] Running hybrid retrieval (BM25 + dense)...")
            t2 = datetime.now()
            search_results = self.hybrid_retrieve_and_rerank(processed_query, top_k_bm25=3, top_k_dense=3)
            t3 = datetime.now()
            timings['vector_search_ms'] = int((t3 - t2).total_seconds() * 1000)

            # Check if we found relevant documents
            if not search_results["found"]:
                logger.warning("No relevant documents found")
                yield {
                    "type": "content",
                    "content": "I don't have enough information in my knowledge base to answer that question. Please ask something related to the documents I have access to."
                }
                # Send an explicit empty sources event so clients expecting a sources event
                # always receive a consistent event stream format.
                yield {
                    "type": "sources",
                    "sources": []
                }
                yield {
                    "type": "end",
                    "metadata": {
                        "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000),
                        "documents_found": 0
                    }
                }
                return
            # Emit an immediate retrieval-preview chunk so clients receive
            # useful context quickly while the LLM generates the full answer.
            # Sending this before prompt build reduces time-to-first-byte.
            try:
                # Send compressed summaries as preview if available
                previews = search_results.get('summaries') or []
                preview_text = "\n".join(previews[:3])
                yield {"type": "content", "content": preview_text}
            except Exception:
                yield {"type": "content", "content": ""}

            # Step 3.2: Build RAG prompt
            logger.info("[STREAM] Building RAG prompt...")
            t4 = datetime.now()
            prompt = self.build_rag_prompt(processed_query, search_results)
            t5 = datetime.now()
            timings['prompt_build_ms'] = int((t5 - t4).total_seconds() * 1000)

            # Step 3.3: Stream answer generation
            logger.info("[STREAM] Streaming answer generation...")

            full_answer = ""
            t6 = datetime.now()
            for chunk in self.generate_answer_stream(prompt):
                if 'llm_start' not in timings:
                    # Mark time to first LLM chunk
                    timings['llm_start_ms'] = int((datetime.now() - start_time).total_seconds() * 1000)
                full_answer += chunk
                yield {
                    "type": "content",
                    "content": chunk
                }
            t7 = datetime.now()
            timings['llm_ms'] = int((t7 - t6).total_seconds() * 1000)

            # Step 4: Send sources
            logger.info("[STREAM] Sending sources...")
            formatted = self.format_answer(full_answer, search_results)

            yield {
                "type": "sources",
                "sources": formatted["sources"]
            }

            # Step 5: Send completion event
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            yield {
                "type": "end",
                "metadata": {
                    "user_id": user_id,
                    "processing_time_ms": processing_time,
                    "documents_found": len(search_results["documents"]),
                    "timings_ms": timings
                }
            }

            logger.info("[STREAM] Stream completed")

        except Exception as e:
            logger.error(f"Error in streaming: {e}")
            yield {
                "type": "error",
                "error": str(e)
            }

# ========================
# Initialize Agent
# ========================
try:
    agent = RAGAgent()
    logger.info("RAG Agent initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize RAG Agent: {e}")
    agent = None

# ========================
# API Endpoints
# ========================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "RAG Agent Workflow API",
        "version": "1.0.0",
        "agent_ready": agent is not None
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler: for Twilio webhook paths return valid TwiML
    so Twilio does not receive JSON/HTML (which causes Document parse failures).
    For other paths, return a JSON error.
    """
    try:
        logger.exception(f"Unhandled exception for request {request.url.path}: {exc}")
    except Exception:
        logger.exception("Unhandled exception (logging failed)")

    # If Twilio hit our webhook, respond with TwiML so Twilio can parse it
    path = request.url.path if hasattr(request, 'url') else ''
    if path.startswith('/webhook/twilio') or path.startswith('/twiml'):
        twiml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            "<Response>"
            "<Say voice=\"alice\">An internal error occurred. Please try again later.</Say>"
            "</Response>"
        )
        return Response(content=twiml, media_type='application/xml')

    # Default JSON response for other endpoints
    return JSONResponse(status_code=500, content={"error": "Internal server error", "message": str(exc)})

@app.get("/health")
async def health_check():
    """Detailed health check"""
    if agent is None:
        raise HTTPException(status_code=503, detail="RAG Agent not initialized")
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "chroma_db_path": Config.CHROMA_DB_PATH,
        "collection_name": Config.COLLECTION_NAME,
        "model": Config.GROQ_MODEL
    }

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Main query endpoint for the RAG agent
    Supports both regular and streaming responses
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="RAG Agent not initialized")
    
    start_time = time.time()
    logger.info(f"Received query from user: {request.user_id} (stream={request.stream})")
    
    # If streaming is requested, redirect to stream endpoint
    if request.stream:
        raise HTTPException(
            status_code=400, 
            detail="For streaming, use POST /query/stream endpoint"
        )
    
    response = agent.process(request.query, request.user_id)
    total_ms = int((time.time() - start_time) * 1000)
    try:
        # Log the interaction for API queries
        log_interaction('api_query', session_id=request.user_id, user_text=request.query, reply_text=(response.answer if response else ''), extra={"processing_ms": total_ms})
    except Exception:
        pass
    return response

@app.post("/query/stream")
async def query_stream_endpoint(request: QueryRequest):
    """
    Streaming query endpoint - returns Server-Sent Events (SSE)
    Provides real-time streaming of the LLM response
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="RAG Agent not initialized")
    
    start_time = time.time()
    logger.info(f"Received streaming query from user: {request.user_id}")
    
    async def event_generator():
        """Generate SSE events"""
        try:
            async for chunk in agent.process_stream(request.query, request.user_id):
                # Convert dict to JSON and send as SSE
                yield {
                    "event": chunk["type"],
                    "data": json.dumps(chunk)
                }
            # Stream finished; log total time
            total_ms = int((time.time() - start_time) * 1000)
            try:
                log_interaction('api_query_stream', session_id=request.user_id, user_text=request.query, reply_text='(streamed)', extra={"processing_ms": total_ms})
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Error in stream generator: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"type": "error", "error": str(e)})
            }
    
    # Explicitly set media_type and disable buffering so clients receive SSE events promptly
    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/webhook/twilio")
async def twilio_webhook(request: Request):
    """
    Twilio-compatible webhook endpoint
    Accepts form data from Twilio and returns TwiML response
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="RAG Agent not initialized")
    
    try:
        # Parse form data from Twilio
        form_data = await request.form()
        message_body = form_data.get("Body", "")
        from_number = form_data.get("From", "")
        message_sid = form_data.get("MessageSid", "")
        
        logger.info(f"Twilio webhook received from {from_number}: {message_body[:100]}")
        
        # Process the query
        response = agent.process(message_body, from_number)
        
        # Return TwiML response
        if response.success and response.answer:
            twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{response.answer}</Message>
</Response>"""
        else:
            error_msg = response.error or "Sorry, I couldn't process your request."
            twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{error_msg}</Message>
</Response>"""
        
        return Response(content=twiml_response, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error processing Twilio webhook: {e}")
        error_twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>Sorry, an error occurred while processing your message.</Message>
</Response>"""
        # Return raw XML; use Response so body is not JSON-encoded
        return Response(content=error_twiml, media_type="application/xml")

@app.post("/webhook/twilio/json")
async def twilio_webhook_json(request: Request):
    """
    Alternative Twilio webhook endpoint that returns JSON instead of TwiML
    Useful for testing and debugging
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="RAG Agent not initialized")
    
    try:
        # Parse form data from Twilio
        form_data = await request.form()
        message_body = form_data.get("Body", "")
        from_number = form_data.get("From", "")
        
        logger.info(f"Twilio JSON webhook received from {from_number}")
        
        # Process the query
        response = agent.process(message_body, from_number)
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing Twilio JSON webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/twilio/voice")
async def twilio_voice_start(request: Request):
    """
    Twilio Voice webhook to start a speech gather.
    Returns TwiML with <Gather input="speech"> so Twilio will POST the
    transcribed speech to /webhook/twilio/voice/result.
    """
    try:
        # Parse incoming form to read CallSid for logging (optional)
        form = await request.form()
        call_sid = form.get('CallSid') or form.get('CallSid'.lower()) or None

        # If USE_MEDIA_STREAM is enabled, return TwiML that starts a Twilio
        # Media Stream to our websocket endpoint instead of doing a Gather.
        use_media = _env_flag_true('USE_MEDIA_STREAM')
        if use_media:
            ws_url = os.getenv('MEDIA_STREAM_WS_URL')
            if not ws_url:
                # construct from host
                host = request.headers.get('host')
                scheme = 'wss' if request.url.scheme == 'https' else 'ws'
                ws_url = f"{scheme}://{host}/ws/twilio_media"

            greeting = os.getenv('TWILIO_GREETING') or "Hello, connecting you to our assistant now."
            twiml = (
                "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                "<Response>"
                f"<Say>{greeting}</Say>"
                f"<Start><Stream url=\"{ws_url}\"/></Start>"
                "</Response>"
            )
            logger.info(f"Returning Start Stream TwiML for call {call_sid} with url={ws_url}")
            return Response(content=twiml, media_type="application/xml")

        # Fallback: use Twilio's built-in Gather speech recognition (legacy flow)
        continue_flag = request.query_params.get('continue')
        if continue_flag and continue_flag == '1':
            greeting = ""
        else:
            greeting = os.getenv('TWILIO_GREETING') or "Hello, thank you for calling. How can I help you today? Please speak after the tone."
        twiml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            "<Response>"
                # If this request is a continuation (redirect from our own TwiML),
                # do not replay the initial greeting. The Redirect we send after
                # answering includes ?continue=1 so subsequent gathers are silent.
                f"<Gather input=\"speech\" action=\"/webhook/twilio/voice/result\" method=\"POST\" timeout=\"60\" speechTimeout=\"auto\">"
                f"<Say>{greeting}</Say>"
            "</Gather>"
            "<Say>I did not receive any input. Goodbye.</Say>"
            "<Hangup/>"
            "</Response>"
        )
        logger.info(f"Returning Gather TwiML for call {call_sid}")
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error in twilio_voice_start: {e}")
        raise HTTPException(status_code=500, detail=str(e))


    @app.get("/webhook/twilio/voice/stream_start")
    async def twilio_voice_stream_start(request: Request):
        """
        TwiML endpoint that instructs Twilio to Start a Media Stream to the
        configured WebSocket URL. Useful for low-latency realtime audio streaming.

        The target WebSocket URL should be set via the environment variable
        MEDIA_STREAM_WS_URL (e.g. "wss://<public-host>/ws/twilio_media"). If not
        set, this handler will attempt to construct a URL from the request host
        but for local development it's recommended to set MEDIA_STREAM_WS_URL to
        the ngrok `wss://` address.
        """
        try:
            ws_url = os.getenv('MEDIA_STREAM_WS_URL')
            if not ws_url:
                # Try to build from Host header (may not be secure/wss)
                host = request.headers.get('host')
                scheme = 'wss' if request.url.scheme == 'https' else 'ws'
                ws_url = f"{scheme}://{host}/ws/twilio_media"

            twiml = (
                "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                "<Response>"
                f"<Start><Stream url=\"{ws_url}\"/></Start>"
                "</Response>"
            )
            logger.info(f"Returning Stream Start TwiML with url={ws_url}")
            return Response(content=twiml, media_type='application/xml')
        except Exception as e:
            logger.error(f"Error building stream start TwiML: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.websocket("/ws/twilio_media")
    async def twilio_media_ws(websocket: WebSocket):
        """
        WebSocket endpoint to receive Twilio Media Streams frames.
        Expects Twilio to connect as a client. This handler will:
        - accept the websocket
        - instantiate a Vosk ASR (if available)
        - feed inbound media frames to the ASR via MediaStreamBridge
        - when a transcript is available, call the RAG agent synchronously
          and then update the live Call via Twilio REST API to speak the
          answer (low-latency playback via TwiML <Say>) and then redirect
          back to /webhook/twilio/voice/stream_start to resume streaming.

        Note: Real-time outbound audio (streaming TTS) over the websocket is
        possible with Twilio's protocol but is not implemented here. This
        approach uses a quick call.update(twiml=...) to play TTS and then
        re-start the stream.
        """
        await websocket.accept()
        twilio_client = None
        bridge = None
        call_sid = None
        try:
            # Prepare ASR bridge if Vosk available
            try:
                asr = VoskASR() if VoskASR is not None else None
                bridge = MediaStreamBridge(asr) if asr is not None else None
            except Exception as e:
                logger.warning(f"Vosk ASR not available or failed to init: {e}")
                bridge = None

            # Twilio credentials (used for call.update)
            account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            if account_sid and auth_token:
                twilio_client = TwilioRestClient(account_sid, auth_token)
            else:
                logger.warning("TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN not set; call updates (TTS playback) will be disabled")

            # Main receive loop
            while True:
                data = await websocket.receive_text()
                try:
                    frame = json.loads(data)
                except Exception:
                    logger.debug("Non-JSON websocket message received; ignoring")
                    continue

                evt = frame.get('event')
                # Capture callSid from the start event if present
                if evt == 'start' or evt == 'connected':
                    # Twilio includes start.callSid in many versions; try both
                    call_sid = frame.get('start', {}).get('callSid') or frame.get('start', {}).get('callSid'.lower()) or frame.get('connected', {}).get('callSid') or call_sid
                    logger.info(f"Twilio Media Stream connected for callSid={call_sid}")

                # Process inbound media frames
                if evt == 'media':
                    if bridge:
                        # This will put transcripts on bridge.queue when available
                        await bridge.handle_twilio_frame(frame)
                        # Non-blocking check for any ready transcripts
                        try:
                            # Use get_nowait to avoid blocking the websocket loop
                            while not bridge.queue.empty():
                                transcript = bridge.queue.get_nowait()
                                logger.info(f"Transcript from media stream: {transcript}")
                                # Call agent in background so we continue processing audio
                                if agent:
                                    async def process_and_respond(t, sid, ws=websocket):
                                        try:
                                            resp = agent.process(t, user_id=sid)
                                            answer = resp.answer if resp and resp.success else "I'm sorry, I don't have an answer for that."
                                            # Build TwiML that speaks the answer then redirects to stream_start
                                            safe_answer = _sanitize_reply_for_customer(answer, max_length=600).replace('&', 'and')
                                            # If outbound streaming TTS is enabled, synthesize and stream via websocket
                                            if _env_flag_true('ENABLE_OUTBOUND_TTS'):
                                                try:
                                                    from twilio_media import synthesize_text_to_pcm16, stream_pcm16_to_twilio_ws
                                                    pcm = synthesize_text_to_pcm16(safe_answer)
                                                    # stream in background so we don't block processing next frames
                                                    asyncio.create_task(stream_pcm16_to_twilio_ws(ws, pcm))
                                                    logger.info(f"Streaming outbound TTS to websocket for call {sid}")
                                                except Exception:
                                                    logger.exception("Failed to stream outbound TTS; falling back to call.update")
                                                    if twilio_client and sid:
                                                        twiml = (
                                                            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                                                            "<Response>"
                                                            f"<Say voice=\"alice\">{safe_answer}</Say>"
                                                            "<Pause length=\"0.5\"/>"
                                                            "<Redirect>/webhook/twilio/voice/stream_start</Redirect>"
                                                            "</Response>"
                                                        )
                                                        try:
                                                            twilio_client.calls(sid).update(twiml=twiml)
                                                        except Exception:
                                                            logger.exception(f"Failed to update Twilio call {sid} for fallback TTS")
                                            else:
                                                twiml = (
                                                    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                                                    "<Response>"
                                                    f"<Say voice=\"alice\">{safe_answer}</Say>"
                                                    "<Pause length=\"0.5\"/>"
                                                    "<Redirect>/webhook/twilio/voice/stream_start</Redirect>"
                                                    "</Response>"
                                                )
                                                if twilio_client and sid:
                                                    try:
                                                        # Update live call to play the TwiML (TTS) then resume streaming
                                                        twilio_client.calls(sid).update(twiml=twiml)
                                                        logger.info(f"Updated call {sid} with TTS TwiML")
                                                    except Exception as e:
                                                        logger.exception(f"Failed to update Twilio call {sid}: {e}")
                                                else:
                                                    logger.info(f"Would speak to call {sid}: {safe_answer}")
                                        except Exception:
                                            logger.exception("Failed to process transcript and respond")

                                    # Schedule background task
                                    asyncio.create_task(process_and_respond(transcript, call_sid))
                        except Exception:
                            # ignore queue empty or other issues
                            pass
                    else:
                        # No ASR bridge available; just log media frames
                        logger.debug("Media frame received but no ASR bridge configured")

                if evt == 'closed':
                    logger.info(f"Twilio media stream closed for callSid={call_sid}")
                    break

        except WebSocketDisconnect:
            logger.info("twilio_media websocket disconnected")
        except Exception as e:
            logger.exception(f"Error in twilio media websocket: {e}")
        finally:
            try:
                await websocket.close()
            except Exception:
                pass


@app.post("/webhook/twilio/voice/result")
async def twilio_voice_result(request: Request):
    """
    Twilio will POST the result of the speech gather here. The form data
    includes 'SpeechResult' (the transcribed text). We call the agent and
    respond with TwiML <Say> to speak the agent's answer, then redirect
    back to /webhook/twilio/voice to continue the conversation.
    """
    try:
        form = await request.form()
        speech_text = form.get('SpeechResult', '')
        caller = form.get('From')
        call_sid = form.get('CallSid') or form.get('CallSid'.lower())

        # De-duplicate near-duplicate webhook deliveries: normalize the
        # speech_text and use (call_sid, caller, normalized_text) as key.
        norm = (speech_text or '').strip().lower()
        cache_key = (call_sid, caller, norm)
        now_ts = time.time()
        try:
            async with processed_cache_lock:
                # Prune old entries
                expired = [k for k, v in processed_speech_cache.items() if now_ts - v > SPEECH_DEDUPE_WINDOW_SEC]
                for k in expired:
                    processed_speech_cache.pop(k, None)

                if cache_key in processed_speech_cache:
                    logger.info(f"Duplicate SpeechResult received for call {call_sid}; skipping processing")
                    # Return an empty Response (no Say) to avoid re-speaking
                    # the same reply. Twilio will accept the 200 and not retry.
                    empty_twiml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response></Response>"
                    return Response(content=empty_twiml, media_type="application/xml")

                # Mark as processed
                processed_speech_cache[cache_key] = now_ts
        except Exception:
            logger.exception("Failed to check/process dedupe cache; proceeding with processing")

        logger.info(f"Received SpeechResult from Twilio: {speech_text}")

        if not speech_text:
            twiml = (
                "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                "<Response>"
                "<Say voice=\"alice\">Sorry, I did not catch that. Please try again.</Say>"
                "<Redirect>/webhook/twilio/voice</Redirect>"
                "</Response>"
            )
            # Return raw XML; use Response instead of JSONResponse
            return Response(content=twiml, media_type="application/xml")

        # Call the agent synchronously (agent.process is synchronous)
        try:
            t0 = time.time()
            response = agent.process(speech_text, user_id=caller)
            t1 = time.time()
            answer = response.answer if response and response.success else "I'm sorry, I don't have an answer for that."
            # Build small metadata for logging
            extra = {
                "processing_ms": int((t1 - t0) * 1000)
            }
            try:
                docs = getattr(response, 'metadata', {}).get('documents_found') if response and response.metadata else None
                if docs is not None:
                    extra['documents_found'] = docs
            except Exception:
                pass
            # Top source previews if present on response.sources
            try:
                if response and getattr(response, 'sources', None):
                    previews = [s.get('preview') for s in response.sources[:3]]
                    extra['source_previews'] = [ _safe_truncate(p, 200) for p in previews if p ]
            except Exception:
                pass
            # Log the interaction
            log_interaction('twilio_voice', session_id=caller, user_text=speech_text, reply_text=answer, extra=extra)
        except Exception as e:
            logger.error(f"Error calling agent from Twilio voice result: {e}")
            answer = "An error occurred while processing your request."
            log_interaction('twilio_voice', session_id=caller, user_text=speech_text, reply_text=answer, extra={"error": str(e)})

        # Build TwiML that speaks the answer and then re-gathers to continue
        # the conversation. If the answer is long, Twilio will speak it.
        # Note: keep Say content reasonably short to avoid long blocking TTS.
        # Sanitize the answer for Twilio TTS: strip doc citations, URLs, and
        # truncate to a safe length. Also replace ampersands to avoid XML issues.
        safe_answer = _sanitize_reply_for_customer(answer, max_length=600).replace('&', 'and')

        twiml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            "<Response>"
            f"<Say voice=\"alice\">{safe_answer}</Say>"
            "<Pause length=\"0.5\"/>"
            # Redirect back to the voice start but indicate continuation so
            # the start handler won't replay the original greeting.
            "<Redirect>/webhook/twilio/voice?continue=1</Redirect>"
            "</Response>"
        )

        return Response(content=twiml, media_type="application/xml")

    except Exception as e:
        logger.error(f"Error in twilio_voice_result: {e}")
        twiml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            "<Response>"
            "<Say voice=\"alice\">An internal error occurred. Please try again later.</Say>"
            "</Response>"
        )
        return Response(content=twiml, media_type="application/xml")


@app.post("/webhook/twilio/voice/recorded")
async def twilio_voice_recorded(request: Request):
    """
    Callback endpoint called by Twilio after the caller leaves a recording
    when no speech was detected by Gather. Logs the recording URL and
    returns a simple TwiML acknowledgment.
    """
    try:
        form = await request.form()
        recording_url = form.get('RecordingUrl') or form.get('RecordingUrl64')
        recording_sid = form.get('RecordingSid')
        caller = form.get('From')

        logger.info(f"Received recorded voicemail from {caller}; recording_sid={recording_sid}; url={recording_url}")

        # TODO: enqueue the recording for ASR or agent processing if desired

        twiml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            "<Response>"
            "<Say voice=\"alice\">Thank you. We received your message and will follow up shortly.</Say>"
            "</Response>"
        )
        return Response(content=twiml, media_type="application/xml")

    except Exception as e:
        logger.error(f"Error handling recorded voicemail callback: {e}")
        twiml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            "<Response>"
            "<Say voice=\"alice\">An internal error occurred handling your message. Please try again later.</Say>"
            "</Response>"
        )
        return Response(content=twiml, media_type="application/xml")


@app.websocket("/ws/query")
async def websocket_query(websocket: WebSocket):
    """
    WebSocket endpoint for low-latency streaming queries.
    Client should send a JSON message with {"query": "...", "user_id": "..."}
    The server will stream JSON chunks (same schema as SSE) back to the client.
    """
    await websocket.accept()
    try:
        while True:
            msg = await websocket.receive_text()
            try:
                payload = json.loads(msg)
            except Exception:
                continue

            # Expect a JSON message: {"query": "...", "user_id": "...", "stream": false}
            q = payload.get('query')
            uid = payload.get('user_id')
            stream = payload.get('stream', False)

            if not q:
                await websocket.send_json({"type": "error", "error": "no query provided"})
                continue

            if stream:
                # Stream chunks from agent.process_stream
                try:
                    async for chunk in agent.process_stream(q, uid):
                        await websocket.send_json({"type": chunk.get('type'), "data": chunk})
                except Exception as e:
                    logger.error(f"Error streaming over websocket: {e}")
                    await websocket.send_json({"type": "error", "error": str(e)})
            else:
                try:
                    response = agent.process(q, uid)
                    await websocket.send_json({"type": "response", "answer": response.answer if response else ""})
                except Exception as e:
                    logger.error(f"Error processing websocket query: {e}")
                    await websocket.send_json({"type": "error", "error": str(e)})

                # Optionally send a concise agent summary to the client
                try:
                    await websocket.send_json({"type": "agent", "answer": response.answer if response else ""})
                except Exception:
                    logger.exception("Failed to send agent reply over websocket")

    except WebSocketDisconnect:
        logger.info("websocket_query disconnected")
    except Exception as e:
        logger.error(f"Error in websocket_query: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# Media streams and local ASR removed for minimal low-latency Gather-based flow.
# ========================
# Run the application
# ========================
if __name__ == "__main__":
    import uvicorn

    # Enable reload when running `python app.py` for a developer-friendly
    # experience. Set UVICORN_RELOAD=false in the environment to disable.
    try:
        reload_env = os.getenv('UVICORN_RELOAD')
        if reload_env is None:
            reload_flag = True
        else:
            reload_flag = _env_flag_true('UVICORN_RELOAD')
    except Exception:
        reload_flag = True

    # If reload is requested, uvicorn requires an import string (module:app).
    # To make that work even when running `python app.py` from another cwd,
    # change the working directory to the script directory and pass the
    # module import string using the script stem (usually 'app'). This
    # avoids the warning: "You must pass the application as an import string
    # to enable 'reload' or 'workers'."
    if reload_flag:
        try:
            script_path = Path(__file__).resolve()
            script_dir = str(script_path.parent)
            module_name = script_path.stem
            logger.info(f"Reload enabled: switching cwd to {script_dir} and running uvicorn with import string {module_name}:app")
            # Change working dir so the reloader can import the module by name
            os.chdir(script_dir)
            uvicorn.run(f"{module_name}:app", host="0.0.0.0", port=8001, reload=True, log_level="info")
        except Exception as e:
            logger.error(f"Failed to start uvicorn with reload import string: {e}; falling back to running app object without reload")
            uvicorn.run(app, host="0.0.0.0", port=8001, reload=False, log_level="info")
    else:
        uvicorn.run(app, host="0.0.0.0", port=8001, reload=False, log_level="info")
