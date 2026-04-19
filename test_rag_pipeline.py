"""End-to-end test: upload doc → ingest → RAG query."""
import requests, time, json

TENANT = "demo-tenant"
AGENT_ID = "9f807ac4-9928-49fa-b81b-7fe342c98c14"
BASE = "http://127.0.0.1:8040"
H = {"x-tenant-id": TENANT}

test_content = """VoiceFlow AI Platform - Product Overview

VoiceFlow is an enterprise AI-powered voice agent platform that enables businesses
to create, deploy, and manage intelligent voice assistants. The platform supports
multi-tenant architecture with per-tenant data isolation.

Key Features:
- Real-time voice synthesis with multiple voice types
- RAG-powered knowledge retrieval from company documents
- Hybrid search combining semantic embeddings and BM25 keyword matching
- Multi-channel deployment (phone, web widget, API)
- Analytics dashboard with call metrics and performance tracking
- Custom brand voice and personality configuration

Pricing Plans:
- Starter: $49/month - 1,000 minutes, 5 agents
- Professional: $199/month - 10,000 minutes, 25 agents
- Enterprise: Custom pricing - unlimited minutes and agents

Technical Stack:
- Backend: FastAPI with async support
- Database: PostgreSQL with SQLAlchemy ORM
- Vector Store: ChromaDB for semantic search
- LLM: Groq API with Llama 3.3 70B
- TTS: Custom text-to-speech service
- Frontend: Django with HTMX and Alpine.js
"""

# Step 1: Upload
print("=== Step 1: Upload document ===")
files = {"file": ("voiceflow_overview.txt", test_content.encode(), "text/plain")}
data = {"agentId": AGENT_ID}
r = requests.post(f"{BASE}/api/documents/upload", headers=H, files=files, data=data)
print(f"Upload: {r.status_code}")
resp = r.json()
print(json.dumps(resp, indent=2)[:500])
doc_id = resp.get("document", {}).get("id", "") or resp.get("id", "")
print(f"Document ID: {doc_id}")

# Step 2: Wait for ingestion
print("\n=== Step 2: Wait for ingestion (20s) ===")
time.sleep(20)

# Step 3: List documents
print("\n=== Step 3: List documents ===")
r = requests.get(f"{BASE}/api/documents", headers=H, params={"agentId": AGENT_ID})
print(f"Docs: {r.status_code}")
docs = r.json()
if isinstance(docs, list):
    doc_list = docs
else:
    doc_list = docs.get("documents", [])
for d in doc_list:
    print(f"  - {d.get('name', d.get('title', '?'))} | status={d.get('status')} | chunks={d.get('chunkCount', '?')}")

# Step 4: RAG Query
print("\n=== Step 4: RAG Query - 'What is the pricing?' ===")
r = requests.post(
    f"{BASE}/api/rag/query",
    headers={**H, "Content-Type": "application/json"},
    json={"agentId": AGENT_ID, "query": "What is the pricing for VoiceFlow?"},
)
print(f"Query: {r.status_code}")
qresp = r.json()
print(f"Documents retrieved: {qresp.get('documentsRetrieved', 0)}")
for doc in qresp.get("documents", [])[:3]:
    print(f"  [{doc.get('retrieval_type', '?')}] score={doc.get('score', 0):.3f}: {doc.get('content', '')[:120]}...")

# Step 5: RAG Chat via /query with features question
print("\n=== Step 5: RAG Query - 'Tell me about VoiceFlow features' ===")
r = requests.post(
    f"{BASE}/api/rag/query",
    headers={**H, "Content-Type": "application/json"},
    json={
        "agentId": AGENT_ID,
        "query": "Tell me about VoiceFlow features and pricing plans",
        "sessionId": "test-session-001",
    },
)
print(f"Chat: {r.status_code}")
cresp = r.json()
print(f"Documents retrieved: {cresp.get('documentsRetrieved', 0)}")
print(f"Model: {cresp.get('model', '?')}")
print(f"LLM Response: {cresp.get('response', '')[:500]}...")

print("\n=== DONE ===")
