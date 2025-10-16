"""
Utility to check document status and embeddings for a given document ID.

Usage (from project root):
    python tools\check_document.py 6b9d6cd8-17c8-490c-a0e8-ccac76118a3f

This will print the document record (status, metadata) from Postgres and the
number of chunks/embeddings found in ChromaDB for that document.

Make sure your environment variables (POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, CHROMA_PERSIST_DIR)
are set or provide a .env in the project root. Run this with the same Python
environment you use for the ingestion service.
"""

import sys
import asyncio
import os
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# Add project root to path so services can be imported when running from tools/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.database import DatabaseManager
from services.vector_store import VectorStore


def print_separator():
    print("\n" + "-" * 60 + "\n")


async def main(document_id: str):
    print(f"Checking document: {document_id}\n")

    # Instantiate managers (these match what main.py uses)
    db = DatabaseManager()
    vs = VectorStore()

    # Fetch document metadata from Postgres
    print("Querying database for document metadata...")
    try:
        doc = await db.get_document(document_id)
        if not doc:
            print(f"Document {document_id} not found in database.")
        else:
            print_separator()
            print("Document metadata:")
            # Print key fields
            keys = ["id", "filename", "file_type", "file_size", "status", "created_at", "updated_at"]
            for k in keys:
                if k in doc:
                    print(f"  {k}: {doc.get(k)}")

            # Print metadata summary
            metadata = doc.get("metadata")
            if metadata:
                print("\n  metadata:")
                # Keep it short
                for mk, mv in (list(metadata.items())[:10]):
                    print(f"    {mk}: {mv}")
            print_separator()
    except Exception as e:
        print(f"Failed to query database: {e}")

    # Query Chroma for chunks/embeddings
    print("Querying Chroma vector store for chunks/embeddings...")
    try:
        chunks = await vs.get_by_document_id(document_id)
        if not chunks:
            print(f"No chunks/embeddings found in ChromaDB for document {document_id}.")
            print("If you expect embeddings, consider calling the /admin/sync endpoint or re-ingesting the document.")
        else:
            print_separator()
            print(f"Found {len(chunks)} chunks/embeddings for document {document_id}:")
            # Show a small sample
            for i, c in enumerate(chunks[:5]):
                meta = c.get("metadata", {})
                print(f"  [{i}] id={c.get('id')} chunk_index={meta.get('chunk_index')} total_chunks={meta.get('total_chunks')}")
                snippet = c.get("document")
                if snippet:
                    snippet = snippet[:120].replace("\n", " ")
                    print(f"       snippet: {snippet}...")
            print_separator()
    except Exception as e:
        print(f"Failed to query vector store: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools\\check_document.py <document_id>")
        sys.exit(2)

    doc_id = sys.argv[1]
    asyncio.run(main(doc_id))
