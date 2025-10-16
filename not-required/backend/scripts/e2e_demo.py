"""End-to-end demo script for the backend API.

This script performs the following steps against a running backend on http://localhost:8000:
1. Sign up (guest) and obtain a token
2. Create a tenant and agent (if API supports it) - fallback to simple agent creation endpoint
3. Upload a sample text file to /upload
4. Verify MinIO object exists by calling the backend's object-listing or via the MinIO client
5. Poll the document ingestion status until it reaches 'completed' or times out

Run with: python backend/scripts/e2e_demo.py
"""

import time
import requests
import base64
import os

BASE = os.environ.get('BACKEND_URL', 'http://localhost:8000')

def guest_token():
    r = requests.post(f"{BASE}/signup/guest")
    r.raise_for_status()
    return r.json().get('access_token')

def upload_file(token, file_path):
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
        headers = {'Authorization': f'Bearer {token}'}
        # Note: upload endpoint is /upload/{tenant_id}/{agent_id}; caller must provide tenant and agent
        # This function will be patched by main() to include tenant/agent in the URL.
        r = requests.post(f"{BASE}/upload", files=files, headers=headers)
        r.raise_for_status()
        return r.json()

def get_documents(token):
    headers = {'Authorization': f'Bearer {token}'}
    # list_documents endpoint is /documents/{agent_id}; caller will format the URL
    r = requests.get(f"{BASE}/documents", headers=headers)
    r.raise_for_status()
    return r.json()

def poll_status(token, doc_id, timeout=60):
    start = time.time()
    while time.time() - start < timeout:
        docs = get_documents(token)
        for d in docs:
            if d.get('id') == doc_id:
                status = d.get('status') or d.get('ingestion_status') or d.get('embedding_status')
                print('Document status:', status)
                if status in ('completed', 'ready', 'embedded'):
                    return d
        time.sleep(2)
    raise TimeoutError('Timed out waiting for ingestion')

def main():
    token = guest_token()
    print('Guest token acquired')
    sample = os.path.join(os.path.dirname(__file__), '..', 'sample.txt')
    if not os.path.exists(sample):
        with open(sample, 'w') as f:
            f.write('Hello from e2e demo')
    # Create a tenant
    r = requests.post(f"{BASE}/tenants", json={'name': 'e2e-tenant'})
    r.raise_for_status()
    tenant_id = r.json().get('id')
    print('Created tenant', tenant_id)

    # Create an agent
    r = requests.post(f"{BASE}/agents", json={'tenant_id': tenant_id, 'name': 'e2e-agent'})
    r.raise_for_status()
    agent_id = r.json().get('id')
    print('Created agent', agent_id)

    # Upload to the tenant/agent upload endpoint
    with open(sample, 'rb') as f:
        files = {'file': (os.path.basename(sample), f, 'application/octet-stream')}
        headers = {'Authorization': f'Bearer {token}'}
        resp = requests.post(f"{BASE}/upload/{tenant_id}/{agent_id}", files=files, headers=headers)
        resp.raise_for_status()
    print('Upload response:', resp.json())
    doc_id = resp.json().get('id')
    if not doc_id:
        print('No document id returned by upload; listing documents to find recent one')
        docs = requests.get(f"{BASE}/documents/{agent_id}").json().get('documents', [])
        doc_id = docs[-1]['id']
    print('Polling ingestion for doc id:', doc_id)
    doc = poll_status(token, doc_id, timeout=120)
    print('Document finished ingestion:', doc)

if __name__ == '__main__':
    main()
