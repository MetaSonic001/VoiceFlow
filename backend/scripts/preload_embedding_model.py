"""Preload sentence-transformers embedding model to a local directory and validate it

This script downloads the model (if needed), saves it to `./models/<model>` and
performs a small embedding to validate everything works.

Usage:
  python backend/scripts/preload_embedding_model.py

Environment variables:
  EMBEDDING_MODEL - model name (default: all-MiniLM-L6-v2)
  EMBEDDING_MODEL_PATH - optional local path to save the model (default: ./models/<model>)
"""
import os
import pathlib
import sys
import time
import logging

from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('preload')


def main():
    model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    target_dir = os.getenv('EMBEDDING_MODEL_PATH')
    if not target_dir:
        target_dir = pathlib.Path(__file__).resolve().parents[2] / 'models' / model_name
    else:
        target_dir = pathlib.Path(target_dir)

    logger.info(f"Using model name: {model_name}")
    logger.info(f"Target local model dir: {str(target_dir)}")

    try:
        # Load model (this will download if necessary)
        logger.info("Loading model (this may download weights)...")
        model = SentenceTransformer(model_name)
        logger.info("Model loaded successfully")

        # Try to save to target dir for later local loads
        try:
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            model.save(str(target_dir))
            logger.info(f"Model saved to {str(target_dir)}")
        except Exception as e:
            logger.warning(f"Failed to save model to {str(target_dir)}: {e}")

        # Validate by encoding a small sample
        sample = ["This is a test.", "The quick brown fox jumps over the lazy dog."]
        start = time.time()
        embeddings = model.encode(sample, show_progress_bar=False)
        elapsed = time.time() - start
        logger.info(f"Generated {len(embeddings)} embeddings in {elapsed:.2f}s; dim={len(embeddings[0])}")
        print("OK")
        return 0

    except Exception as e:
        logger.exception("Failed to preload or validate embedding model")
        return 2


if __name__ == '__main__':
    sys.exit(main())
