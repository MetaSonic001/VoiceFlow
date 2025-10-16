"""Demo orchestration script

This script demonstrates using the document-ingestion service to ingest a list
of websites (FR CRCE college related), waits for embeddings, creates a tenant
and agent in the backend, and exercises the agent-workflow to answer a sample
query. Logging is verbose and prints each step's input/output for auditing.

Adjust endpoints via environment variables if your services run on different
ports or hosts.

Usage:
  python backend/scripts/ingest_and_create_agent_demo.py

Requirements: requests
"""

import os
import time
import json
import requests
import subprocess
import pathlib
import io
import sys
from typing import List
from dotenv import load_dotenv

API_BACKEND = os.environ.get('BACKEND_URL', 'http://localhost:8000')
INGESTION = os.environ.get('INGESTION_URL', 'http://localhost:8002')
AGENT_WORKFLOW = os.environ.get('AGENT_WORKFLOW_URL', 'http://localhost:8001')




DEFAULT_FR_CRCE_URLS = [
    # A few likely public pages for FR CRCE (Bandra, Mumbai). Replace as needed.
    'https://frcrce.ac.in/',
    'https://frcrce.ac.in/about-us/',
    'https://frcrce.ac.in/department-of-computer-engineering/',
    'https://frcrce.ac.in/admissions/',
]

LOG_FILE = os.environ.get('DEMO_LOG', os.path.join(os.getcwd(), 'ingest_demo.log'))


def log(msg: str, obj=None):
    line = f"[DEMO] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as fh:
        fh.write(line + '\n')
        if obj is not None:
            try:
                fh.write(json.dumps(obj, ensure_ascii=False, default=str) + '\n')
            except Exception:
                fh.write(str(obj) + '\n')


# Attempt to load .env files from other folders in the repo so users who set envs
# in frontend/backend/agent-workflow have values available to this demo script.
try:
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    env_candidates = [
        repo_root / 'backend' / '.env',
        repo_root / 'voiceflow-ai-platform (1)' / '.env',
        repo_root / 'agent-workflow' / '.env',
        repo_root / 'document-ingestion' / '.env',
        repo_root / '.env',
    ]
    loaded = []
    for p in env_candidates:
        if p.exists():
            try:
                load_dotenv(dotenv_path=str(p))
                loaded.append(str(p))
            except Exception:
                pass
    if loaded:
        log('Loaded .env files for demo', {'files': loaded})
except Exception:
    # Non-fatal; continue with existing os.environ values
    pass

# Reload key endpoints and log path in case they were set in loaded .env files
API_BACKEND = os.environ.get('BACKEND_URL', API_BACKEND)
INGESTION = os.environ.get('INGESTION_URL', INGESTION)
AGENT_WORKFLOW = os.environ.get('AGENT_WORKFLOW_URL', AGENT_WORKFLOW)
LOG_FILE = os.environ.get('DEMO_LOG', LOG_FILE)


def ingest_urls(urls: List[str]):
    """Upload each URL to backend /upload/{tenant_id}/{agent_id} as a small text file so
    ingestion receives tenant and agent metadata. Returns list of returned document ids.

    Note: This function assumes tenant_id and agent_id have already been created and
    are available in the environment variables BACKEND_TENANT and BACKEND_AGENT or
    provided by the caller by setting global TENANT_ID and AGENT_ID before calling.
    """
    doc_ids = []
    tenant = os.environ.get('DEMO_TENANT_ID')
    agent = os.environ.get('DEMO_AGENT_ID')
    if not tenant or not agent:
        log('ingest_urls called before tenant/agent exist; aborting')
        return doc_ids

    for url in urls:
        log(f"Uploading URL to backend upload endpoint: {url}")
        try:
            # create an in-memory text file containing the URL
            file_content = url.encode('utf-8')
            files = {'file': ('url.txt', io.BytesIO(file_content), 'text/plain')}
            r = requests.post(f"{API_BACKEND}/upload/{tenant}/{agent}", files=files, timeout=120)
            r.raise_for_status()
            res = r.json()
            log(f"Upload response for {url}", res)
            doc_id = res.get('id') or res.get('document_id')
            if doc_id:
                doc_ids.append(doc_id)
            else:
                log(f"No document id returned for uploaded url {url}; server message: {res}")
        except Exception as e:
            log(f"Failed to upload {url}: {e}")
    return doc_ids


def check_envs() -> bool:
    """Log and validate environment variables and service reachability.

    Returns True if critical services appear reachable or DEMO_FORCE_RUN is set.
    """
    env_snapshot = {
        'BACKEND_URL': API_BACKEND,
        'INGESTION_URL': INGESTION,
        'AGENT_WORKFLOW_URL': AGENT_WORKFLOW,
        'TWILIO_ACCOUNT_SID': bool(os.getenv('TWILIO_ACCOUNT_SID')),
        'TWILIO_AUTH_TOKEN': bool(os.getenv('TWILIO_AUTH_TOKEN')),
        'TWILIO_PHONE_SID': os.getenv('TWILIO_PHONE_SID'),
        'TWILIO_AUTO_SELECT_FIRST': os.getenv('TWILIO_AUTO_SELECT_FIRST'),
    }
    log('Effective environment snapshot', env_snapshot)

    # Quick HTTP health checks (non-blocking, short timeout)
    services = [
        ('backend', API_BACKEND),
        ('ingestion', INGESTION),
        ('agent_workflow', AGENT_WORKFLOW),
    ]
    ok = True
    for name, url in services:
        try:
            # prefer /health when available
            health_url = url.rstrip('/') + '/health'
            r = requests.get(health_url, timeout=3)
            if r.status_code == 200:
                log(f'{name} health OK', {'url': health_url})
                continue
            else:
                # try root
                r2 = requests.get(url, timeout=3)
                if r2.status_code == 200:
                    log(f'{name} root reachable', {'url': url})
                    continue
                log(f'{name} returned non-200 health/root', {'health_status': r.status_code, 'root_status': r2.status_code})
                ok = False
        except Exception as e:
            log(f'{name} health check failed', str(e))
            ok = False

    if not ok:
        force = os.getenv('DEMO_FORCE_RUN', '').lower() in ('1', 'true', 'yes')
        if force:
            log('One or more services failed health check but DEMO_FORCE_RUN is set; continuing')
            return True
        else:
            log('One or more services failed health check; set DEMO_FORCE_RUN=true to override and continue')
            return False

    return True


def wait_for_embeddings(doc_id: str, max_retries: int = 30, retry_delay: float = 3.0):
    """Poll /documents/{id}/embeddings until embeddings_count > 0 or max retries reached"""
    log(f"Starting embeddings polling for document {doc_id} (max {max_retries} retries, {retry_delay}s delay)")

    for attempt in range(max_retries):
        try:
            r = requests.get(f"{INGESTION}/documents/{doc_id}/embeddings", timeout=30)
            if r.status_code == 200:
                j = r.json()
                embeddings_count = j.get('embeddings_count', 0)
                status = j.get('status', 'unknown')

                log(f"Embeddings status for {doc_id} (attempt {attempt + 1}/{max_retries}): {embeddings_count} embeddings, status: {status}")

                if embeddings_count > 0:
                    log(f"✅ Embeddings completed successfully for document {doc_id}")
                    return True, j
                elif status in ['failed', 'error']:
                    log(f"❌ Embeddings failed for document {doc_id} with status: {status}")
                    return False, j
            else:
                log(f"⚠️  Non-200 response from embeddings endpoint for {doc_id} (attempt {attempt + 1}/{max_retries}): {r.status_code} - {r.text}")

        except Exception as e:
            log(f"⚠️  Error polling embeddings for {doc_id} (attempt {attempt + 1}/{max_retries}): {e}")

        if attempt < max_retries - 1:  # Don't sleep after the last attempt
            log(f"⏳ Waiting {retry_delay}s before next attempt...")
            time.sleep(retry_delay)

    log(f"❌ Embeddings polling timed out for document {doc_id} after {max_retries} attempts")
    return False, None


def create_tenant_and_agent(tenant_name: str = 'FRCRCE Demo Tenant', agent_name: str = 'frcrce-demo-agent'):
    """Create tenant and agent on backend and return (tenant_id, agent_id)"""
    log('Creating tenant', {'name': tenant_name})
    r = requests.post(f"{API_BACKEND}/tenants", json={'name': tenant_name}, timeout=30)
    r.raise_for_status()
    tenant_id = r.json().get('id')
    log('Tenant created', {'tenant_id': tenant_id})

    log('Creating agent', {'tenant_id': tenant_id, 'name': agent_name})
    r2 = requests.post(f"{API_BACKEND}/agents", json={'tenant_id': tenant_id, 'name': agent_name}, timeout=30)
    r2.raise_for_status()
    agent_id = r2.json().get('id')
    log('Agent created', {'agent_id': agent_id})
    # Export tenant/agent ids for downstream helper functions
    os.environ['DEMO_TENANT_ID'] = str(tenant_id)
    os.environ['DEMO_AGENT_ID'] = str(agent_id)
    return tenant_id, agent_id


def run_twilio_updater():
    """Run the agent-workflow's Twilio updater script if Twilio env vars are present.
    Parses stdout for a printed phone number and returns it if found.
    """
    account = os.getenv('TWILIO_ACCOUNT_SID')
    token = os.getenv('TWILIO_AUTH_TOKEN')
    if not account or not token:
        log('Twilio env vars not set; skipping Twilio updater')
        return None

    updater = pathlib.Path(__file__).resolve().parents[2] / 'agent-workflow' / 'scripts' / 'update_twilio_webhook.py'
    if not updater.exists():
        log('Twilio updater script not found', {'path': str(updater)})
        return None

    log('Running Twilio updater script', {'script': str(updater)})
    try:
        # Prepare environment for the updater script. Ensure NGROK_PORT points
        # to the agent-workflow service port so the public tunnel will forward
        # to the correct service. Also set webhook paths explicitly.
        env = os.environ.copy()
        # Derive port from AGENT_WORKFLOW (e.g. http://localhost:8001)
        try:
            aw = AGENT_WORKFLOW
            # naive parse: take last ':' segment as port when present
            port = '8001'
            if aw and aw.startswith('http'):
                parts = aw.rsplit(':', 1)
                if len(parts) == 2:
                    port_candidate = parts[1]
                    if port_candidate.isdigit():
                        port = port_candidate
        except Exception:
            port = '8001'

        env['NGROK_PORT'] = port
        env.setdefault('TWILIO_VOICE_WEBHOOK_PATH', '/webhook/twilio/voice')
        env.setdefault('TWILIO_MESSAGE_WEBHOOK_PATH', '/webhook/twilio')

        # Run the updater from its directory so relative operations behave
        # the same as running the script directly.
        proc = subprocess.run([sys.executable, str(updater)], capture_output=True, text=True, timeout=300, env=env, cwd=str(updater.parent))
        out = proc.stdout + '\n' + proc.stderr
        log('Twilio updater output', out)
        # Try to parse the friendly summary printed by the updater
        for line in out.splitlines():
            line = line.strip()
            if line.startswith('✓ Updated phone number:') or 'Updated phone number:' in line:
                # extract +E.164 number from the line
                parts = line.split(':', 1)
                if len(parts) > 1:
                    phone = parts[1].split('(')[0].strip()
                    log('Parsed phone number from updater output', {'phone': phone})
                    return phone
        # Fallback: search for + followed by digits
        import re
        m = re.search(r"\+\d{6,15}", out)
        if m:
            phone = m.group(0)
            log('Found phone number in updater output (fallback)', {'phone': phone})
            return phone
        log('No phone number parsed from Twilio updater output')
        return None
    except subprocess.TimeoutExpired:
        log('Twilio updater timed out')
        return None
    except Exception as e:
        log('Error running Twilio updater', str(e))
        return None


def attach_documents_to_agent(agent_id: str, doc_ids: List[str]):
    """Associate ingested documents with agent by creating Document rows under that agent.
    This script assumes ingestion stored documents independently; if ingestion stored with generic tenant/agent mapping,
    you may need to reassign or add metadata. Here we simply log the step and rely on ingestion metadata.
    """
    log('Attaching documents to agent (informational)', {'agent_id': agent_id, 'doc_ids': doc_ids})
    # If backend has a special endpoint to attach documents to agent, call it here.
    # Example placeholder: POST /agents/{agent_id}/documents/attach
    url = f"{API_BACKEND}/agents/{agent_id}/attach_documents"
    try:
        r = requests.post(url, json={'document_ids': doc_ids}, timeout=30)
        if r.status_code in (200, 201):
            log('Documents attached to agent', r.json())
        else:
            log('No attach endpoint or attach failed; proceeding anyway', {'status': r.status_code, 'text': r.text})
    except Exception as e:
        log('Attach endpoint absent or error; continuing', str(e))


def query_agent_workflow(question: str, tenant_id: str = None, agent_id: str = None, top_k: int = 3):
    """Query the agent-workflow /query endpoint and return the result"""
    log('Querying agent-workflow', {'question': question, 'tenant_id': tenant_id, 'agent_id': agent_id})
    try:
        payload = {'query': question, 'user_id': 'demo'}
        if tenant_id:
            payload['tenant_id'] = tenant_id
        if agent_id:
            payload['agent_id'] = agent_id
        r = requests.post(f"{AGENT_WORKFLOW}/query", json=payload, timeout=60)
        r.raise_for_status()
        res = r.json()
        log('Agent workflow response', res)
        return res
    except Exception as e:
        log('Agent workflow query failed', str(e))
        return None


def main(urls: List[str] = None):
    if urls is None:
        urls = DEFAULT_FR_CRCE_URLS


    log('Demo start', {'backend': API_BACKEND, 'ingestion': INGESTION, 'agent_workflow': AGENT_WORKFLOW, 'urls': urls})

    # Validate envs and service reachability before proceeding
    if not check_envs():
        return

    # 1) Create tenant and agent first
    tenant_id, agent_id = create_tenant_and_agent()

    # 2) Upload each URL to backend /upload/{tenant_id}/{agent_id} as a text file
    doc_ids = ingest_urls(urls)
    if not doc_ids:
        log('No documents were uploaded; aborting demo')
        return

    # 3) Wait for embeddings for each doc
    ready_docs = []
    for did in doc_ids:
        ok, info = wait_for_embeddings(did, max_retries=30, retry_delay=3.0)
        if ok:
            ready_docs.append({'id': did, 'info': info})
        else:
            log(f'❌ Embeddings failed or timed out for {did} after 30 attempts')

    log('Embeddings readiness summary', {'ready_count': len(ready_docs), 'total': len(doc_ids)})

    # 4) Attach documents to agent (best-effort)
    attach_documents_to_agent(agent_id, [d['id'] for d in ready_docs])

    # 5) Query the agent-workflow to ensure content is searchable
    sample_q = 'What is Fr. Conceicao Rodrigues College of Engineering (FRCRCE) known for?'
    res = query_agent_workflow(sample_q, tenant_id, agent_id)
    if res:
        log('Sample query result', res)
    else:
        log('No response from agent-workflow')

    # 6) Run Twilio updater script and print phone number for calling
    phone_number = run_twilio_updater()
    if phone_number:
        log('Demo complete: phone number available for calling', {'phone_number': phone_number})
        print(f"\n[DEMO] Call this number to test the agent: {phone_number}\n")
    else:
        log('Demo complete: Twilio phone number not available (see logs for details)')

    log('Demo complete', {'tenant_id': tenant_id, 'agent_id': agent_id, 'phone_number': phone_number})


if __name__ == '__main__':
    main()
