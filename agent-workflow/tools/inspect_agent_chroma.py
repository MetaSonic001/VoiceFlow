import os
import sys
import chromadb
from chromadb.config import Settings

# Path should match what the agent uses by default or via CHROMA_DB_PATH env
chroma_path = os.getenv('CHROMA_DB_PATH', '../document-ingestion/chroma_db')
chroma_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', chroma_path))
print('Using chroma path:', chroma_path)

client = chromadb.PersistentClient(path=chroma_path, settings=Settings(anonymized_telemetry=False))

# List collections
try:
    cols = client.list_collections()
    print('Collections:', [c['name'] for c in cols])
except Exception as e:
    print('list_collections failed:', e)

# Try to get the documents collection
try:
    coll = client.get_or_create_collection(name='documents', metadata={'hnsw:space':'cosine'})
    print('Collection count:', coll.count())

    # Try to get a small sample
    try:
        res = coll.get(limit=5)
        print('Get keys:', list(res.keys()))
        docs = res.get('documents')
        ids = res.get('ids')
        metas = res.get('metadatas')
        print('Sample ids count:', len(ids) if ids else 0)
    except Exception as e:
        print('collection.get failed:', e)

    # Try a text query
    try:
        qres = coll.query(query_texts=['What information do you have?'], n_results=3, include=['documents','metadatas','distances'])
        print('Query by text results keys:', list(qres.keys()))
        print('documents:', qres.get('documents'))
        print('distances:', qres.get('distances'))
    except Exception as e:
        print('query by text failed:', e)

except Exception as e:
    print('Failed to access collection:', e)
