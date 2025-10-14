"""
Text Embedding Service
Handles text chunking and embedding generation
"""

from sentence_transformers import SentenceTransformer
from typing import List
import logging
import numpy as np
import os
import pathlib
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class TextEmbedder:
    """
    Service for text chunking and embedding generation
    """
    
    def __init__(
        self,
        model_name: str = None,
        chunk_size: int = 800,
        chunk_overlap: int = 200
    ):
        """
        Initialize embedder with model
        
        Args:
            model_name: Sentence transformer model name
            chunk_size: Size of text chunks in characters (default tuned ~800 to target 300-1000 token sweet spot)
            chunk_overlap: Overlap between chunks in characters (default tuned ~25% overlap)
        """
        # Determine model source. Prefer a local directory if provided via
        # EMBEDDING_MODEL_PATH env var or if the provided model_name is a path.
        try:
            env_model_path = os.getenv('EMBEDDING_MODEL_PATH') or os.getenv('EMBEDDING_LOCAL_DIR')
            effective_model = model_name or os.getenv('EMBEDDING_MODEL') or 'all-MiniLM-L6-v2'
            # If env path provided and exists, use it
            if env_model_path:
                p = pathlib.Path(env_model_path)
                if p.exists():
                    logger.info(f"Loading local embedding model from path: {str(p)}")
                    self.model = SentenceTransformer(str(p))
                else:
                    # Directory doesn't exist yet; fall back to HF name but save to local later
                    logger.info(f"Local embedding path {str(p)} does not exist; will load model '{effective_model}' and save to {str(p)}")
                    self.model = SentenceTransformer(effective_model)
                    try:
                        p.parent.mkdir(parents=True, exist_ok=True)
                        self.model.save(str(p))
                        logger.info(f"Saved embedding model to {str(p)}")
                    except Exception:
                        logger.warning(f"Failed to save model to {str(p)}; continuing with cached model")
            else:
                # If model_name looks like a filesystem path, prefer it
                maybe_path = pathlib.Path(effective_model)
                if maybe_path.exists():
                    logger.info(f"Loading embedding model from local path: {str(maybe_path)}")
                    self.model = SentenceTransformer(str(maybe_path))
                else:
                    logger.info(f"Loading embedding model by name: {effective_model}")
                    self.model = SentenceTransformer(effective_model)
            # Enforce numeric types for sizes (defensive cast)
            try:
                self.chunk_size = int(chunk_size)
            except Exception:
                logger.warning("Invalid chunk_size provided, falling back to 512")
                self.chunk_size = 800

            try:
                self.chunk_overlap = int(chunk_overlap)
            except Exception:
                logger.warning("Invalid chunk_overlap provided, falling back to 50")
                self.chunk_overlap = int(self.chunk_size * 0.25)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}", exc_info=True)
            raise
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Input text to chunk
        
        Returns:
            List of text chunks
        """
        if not text or len(text.strip()) == 0:
            logger.warning("Empty text provided for chunking")
            return []
        
        logger.info(f"Chunking text of length {len(text)}")
        
        chunks = []
        start = 0
        text_length = len(text)

        try:
            # Main loop: produce overlapping chunks
            while start < text_length:
                prev_start = start
                end = min(start + self.chunk_size, text_length)

                # Try to break at sentence boundaries if we're not at the end
                if end < text_length:
                    sentence_endings = ['. ', '! ', '? ', '\n\n']
                    best_break = end
                    for ending in sentence_endings:
                        pos = text.rfind(ending, start, end)
                        if pos != -1 and pos > start:
                            best_break = pos + len(ending)
                            break
                    # Ensure best_break is an int and within bounds
                    if not isinstance(best_break, int) or best_break <= start:
                        best_break = end
                    end = min(best_break, text_length)

                chunk = text[start:end].strip()
                if chunk:
                    chunks.append(chunk)

                # Compute next start position with overlap
                next_start = end - self.chunk_overlap
                # Defensive guards: ensure numeric and progress forward
                try:
                    next_start = int(next_start)
                except Exception:
                    next_start = end

                if next_start <= start:
                    # If overlap would not progress, move to end
                    next_start = end

                start = next_start

            logger.info(f"Created {len(chunks)} chunks")
            return chunks

        except Exception as e:
            logger.error(f"Error while chunking text: {e}", exc_info=True)
            # Return any chunks we managed to create, or empty list
            return chunks
    
    async def embed_chunks(self, chunks: List[str]) -> List[List[float]]:
        """
        Generate embeddings for text chunks
        
        Args:
            chunks: List of text chunks
        
        Returns:
            List of embedding vectors
        """
        if not chunks:
            logger.warning("No chunks provided for embedding")
            return []
        
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        
        try:
            # Generate embeddings
            embeddings = self.model.encode(
                chunks,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            
            # Convert to list of lists
            embeddings_list = embeddings.tolist()
            
            logger.info(f"Generated {len(embeddings_list)} embeddings of dimension {len(embeddings_list[0])}")
            
            return embeddings_list
        
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}", exc_info=True)
            raise
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text
        
        Returns:
            Embedding vector
        """
        if not text or len(text.strip()) == 0:
            logger.warning("Empty text provided for embedding")
            return []
        
        logger.info("Generating single text embedding")
        
        try:
            embedding = self.model.encode(
                text,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            
            return embedding.tolist()
        
        except Exception as e:
            logger.error(f"Error generating text embedding: {e}", exc_info=True)
            raise
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings
        
        Returns:
            Embedding dimension
        """
        return self.model.get_sentence_embedding_dimension()