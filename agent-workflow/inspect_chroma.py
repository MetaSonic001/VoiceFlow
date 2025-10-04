"""inspect_chroma.py
Quick script to inspect the Chroma DB used by the agent-workflow service.
Run from the repository root: python .\agent-workflow\inspect_chroma.py
"""
import os
import sys
import json
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
except Exception as e:
    print(f"chromadb not installed or import failed: {e}")
    sys.exit(1)


def pretty(obj):
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)


def main():
    db_path = os.getenv('CHROMA_DB_PATH', None)
    if not db_path:
        # default used by agent
        db_path = os.path.join(os.path.dirname(__file__), '..', 'document-ingestion', 'chroma_db')
    db_path = os.path.normpath(db_path)

    print(f"CHROMA_DB_PATH: {db_path}")
    p = Path(db_path)
    if not p.exists():
        print("Chroma DB path does not exist on disk.")
        sys.exit(1)

    # list files in directory
    print("Files in CHROMA_DB_PATH:")
    for child in p.iterdir():
        try:
            print(f" - {child.name}  size={child.stat().st_size}")
        except Exception:
            print(f" - {child.name}")

    # open client
    try:
        client = chromadb.PersistentClient(path=db_path, settings=Settings(anonymized_telemetry=False))
    except Exception as e:
        print(f"Failed to open PersistentClient: {e}")
        sys.exit(1)

    # list collections
    try:
        collections = client.list_collections()
        print(f"Found {len(collections)} collection(s)")
    except Exception as e:
        print(f"client.list_collections() failed: {e}")
        collections = []

    if collections:
        import re
        for col in collections:
            # Try common shapes: dict with 'name', object with attribute 'name', or string repr like "Collection(name=documents)"
            name = None
            if isinstance(col, dict) and 'name' in col:
                name = col['name']
            else:
                # try attribute access
                try:
                    name = getattr(col, 'name')
                except Exception:
                    name = None

            if not name:
                s = str(col)
                m = re.search(r"name=([^\)]+)", s)
                if m:
                    name = m.group(1)
                else:
                    name = s

            print(f"\nCollection: {name}")
            try:
                collection = client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
            except Exception as e:
                print(f"  get_or_create_collection failed for {name}: {e}")
                continue

            # Try to get a count
            count = None
            try:
                count = collection.count()
            except Exception:
                try:
                    res = collection.get(include=["ids"])
                    ids = res.get('ids') if isinstance(res, dict) else None
                    if ids and isinstance(ids, list):
                        count = len(ids[0]) if isinstance(ids[0], list) else len(ids)
                except Exception:
                    count = None

            print(f"  count (approx): {count}")

            # Show a small sample of documents and metadatas
            try:
                sample = collection.get(include=['documents','metadatas'], limit=5)
                print("  sample documents:")
                docs = sample.get('documents', [])
                metas = sample.get('metadatas', [])
                # results are usually nested per-query; try robust printing
                if docs:
                    first = docs[0] if isinstance(docs, list) and docs else docs
                    if isinstance(first, list):
                        for i, d in enumerate(first[:5], 1):
                            meta = metas[0][i-1] if metas and isinstance(metas[0], list) and len(metas[0])>=i else {}
                            print(f"    [{i}] meta={pretty(meta)}\n         preview={str(d)[:200]}\n")
                    else:
                        for i, d in enumerate(first[:5], 1):
                            print(f"    [{i}] preview={str(d)[:200]}\n")
                else:
                    print("    (no documents returned by collection.get())")
            except Exception as e:
                print(f"  collection.get() failed: {e}")

    else:
        # No collections found — try to probe the default collection name 'documents'
        default_name = os.getenv('COLLECTION_NAME', 'documents')
        print(f"No collections found via list_collections(); probing default collection '{default_name}'")
        try:
            collection = client.get_or_create_collection(name=default_name, metadata={"hnsw:space": "cosine"})
            try:
                count = collection.count()
            except Exception:
                res = collection.get(include=['documents','metadatas','ids'], limit=5)
                ids = res.get('ids') if isinstance(res, dict) else None
                count = (len(ids[0]) if ids and isinstance(ids[0], list) else (len(res.get('documents', [])[0]) if res.get('documents') else 0))
            print(f"Default collection '{default_name}' count (approx): {count}")
        except Exception as e:
            print(f"Failed to probe default collection: {e}")


if __name__ == '__main__':
    main()
