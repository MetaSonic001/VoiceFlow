import os
import logging
import pathlib
import sys

logger = logging.getLogger(__name__)


# Prefer to reuse the VectorStore/Chroma instance from the document-ingestion package
def _get_ingestion_chroma_client():
    try:
        repo_root = pathlib.Path(__file__).resolve().parents[2]
        ingestion_path = repo_root / 'document-ingestion'
        if str(ingestion_path) not in sys.path and ingestion_path.exists():
            sys.path.insert(0, str(ingestion_path))
        # Try to import the VectorStore and use its PersistentClient
        from services.vector_store import VectorStore
        vs = VectorStore()
        client = getattr(vs, 'client', None)
        # If VectorStore uses a single collection named 'documents', client may still be useful
        return client
    except Exception:
        return None


def _local_client(persist_directory: str = None):
    try:
        import chromadb
        from chromadb.config import Settings
    except Exception:
        raise

    if persist_directory is None:
        base = pathlib.Path(__file__).resolve().parents[2] / 'document-ingestion' / 'chroma_db'
        persist_directory = os.getenv('CHROMA_DB_PATH', str(base))
    os.makedirs(persist_directory, exist_ok=True)
    client = chromadb.PersistentClient(path=persist_directory, settings=Settings(anonymized_telemetry=False, allow_reset=True))
    return client


def collection_name(tenant_id: str, agent_id: str) -> str:
    return f"{tenant_id}_{agent_id}".replace('-', '_')


def _get_client():
    c = _get_ingestion_chroma_client()
    if c:
        return c
    return _local_client()


def ensure_collection(tenant_id: str, agent_id: str, embedding_dim: int = None):
    client = _get_client()
    name = collection_name(tenant_id, agent_id)
    metadata = {"embedding_dim": embedding_dim} if embedding_dim else {}
    coll = client.get_or_create_collection(name=name, metadata=metadata)
    logger.info(f"Ensured collection {name} (metadata={metadata})")
    return coll


def delete_collection(tenant_id: str, agent_id: str):
    client = _get_client()
    name = collection_name(tenant_id, agent_id)
    try:
        client.delete_collection(name)
        logger.info(f"Deleted collection {name}")
        return True
    except Exception:
        logger.exception(f"Failed to delete collection {name}")
        return False


def list_collections():
    client = _get_client()
    try:
        return client.list_collections()
    except Exception:
        logger.exception("Failed to list collections")
        return []
