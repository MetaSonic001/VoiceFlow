import os
import sys
import numpy as np
from chromadb.config import Settings
import chromadb

# Ensure we can import the ingestion embedder
ingestion_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'document-ingestion'))
if ingestion_path not in sys.path:
    sys.path.insert(0, ingestion_path)

try:
    from services.embedder import TextEmbedder
except Exception as e:
    print('Failed to import TextEmbedder:', e)
    raise

# Load embedder (SentenceTransformer)
embedder = TextEmbedder()
print('Embedder model dim:', embedder.get_embedding_dimension())

# Prepare query
query = 'What information do you have?'
q_emb = embedder.model.encode(query, show_progress_bar=False, convert_to_numpy=True)
if q_emb.ndim == 2:
    q_vec = q_emb[0]
else:
    q_vec = q_emb

# Connect to Chroma
chroma_path = os.getenv('CHROMA_DB_PATH', '../document-ingestion/chroma_db')
chroma_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', chroma_path))
print('Using chroma path:', chroma_path)
client = chromadb.PersistentClient(path=chroma_path, settings=Settings(anonymized_telemetry=False))
coll = client.get_or_create_collection(name='documents', metadata={'hnsw:space':'cosine'})

# Query by embedding
res = coll.query(query_embeddings=[q_vec.tolist()], n_results=5, include=['documents', 'metadatas', 'distances'])
print('Query results keys:', list(res.keys()))
print('Distances:', res.get('distances'))

# Compute similarity as 1 - distance and show
dists = res.get('distances')[0]
sims = [1.0 - float(d) if d is not None else None for d in dists]
print('Similarities (1 - distance):', sims)

# Also compare cosine manually: fetch the first stored embedding if available
if res.get('embeddings'):
    stored_emb = res['embeddings'][0][0]
    stored_vec = np.array(stored_emb)
    dot = float(np.dot(stored_vec, q_vec))
    norm = float(np.linalg.norm(stored_vec) * np.linalg.norm(q_vec))
    cos_sim = dot / norm if norm != 0 else None
    print('Manual cosine similarity between query and first result:', cos_sim)
else:
    print('No stored embeddings returned in response')
