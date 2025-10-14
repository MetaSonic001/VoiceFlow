#!/usr/bin/env python3
"""
Complete VoiceFlow Demo Script

This script demonstrates the full VoiceFlow pipeline:
1. Takes a URL as input
2. Extracts content using document ingestion API
3. Stores in ChromaDB with embeddings
4. Sets up agent workflow
5. Configures Twilio with phone number and VOSK integration
6. Makes the agent callable via phone

Usage:
  python complete_demo.py <url>

Example:
  python complete_demo.py https://example.com

Requirements: requests, python-dotenv
"""

import os
import sys
import time
import json
import requests
import argparse
import subprocess
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Attempt to load .env files from other folders in the repo so users who set envs
# in frontend/backend/agent-workflow have values available to this demo script.
try:
    import pathlib
    repo_root = pathlib.Path(__file__).resolve().parents[1]  # Go up one level from complete_demo.py
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
        print(f'[DEMO] Loaded .env files: {loaded}')
except Exception:
    # Non-fatal; continue with existing os.environ values
    pass

# API endpoints (reload after .env loading)
API_BACKEND = os.environ.get('BACKEND_URL', 'http://localhost:8000')
INGESTION = os.environ.get('INGESTION_URL', 'http://localhost:8002')
AGENT_WORKFLOW = os.environ.get('AGENT_WORKFLOW_URL', 'http://localhost:8001')

# Twilio configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')

# Demo configuration
TENANT_NAME = os.environ.get('DEMO_TENANT_NAME', 'VoiceFlow Demo Tenant')
AGENT_NAME = os.environ.get('DEMO_AGENT_NAME', 'voiceflow-demo-agent')

LOG_FILE = os.environ.get('DEMO_LOG', 'complete_demo.log')


def log(msg: str, obj=None):
    """Log message to console and file"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f"[DEMO] {timestamp} - {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as fh:
        fh.write(line + '\n')
        if obj:
            fh.write(f"[DEMO] {timestamp} - Data: {json.dumps(obj, indent=2)}\n")


def check_services():
    """Check if all required services are running"""
    log("Checking service health...")

    services = [
        ("Backend", f"{API_BACKEND}/health"),
        ("Ingestion", f"{INGESTION}/health"),
        ("Agent Workflow", f"{AGENT_WORKFLOW}/health")
    ]

    for name, url in services:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                log(f"✅ {name} service is healthy")
            else:
                log(f"❌ {name} service returned status {response.status_code}")
                return False
        except Exception as e:
            log(f"❌ {name} service is not accessible: {e}")
            return False

    return True


def create_tenant_and_agent(tenant_name: str = TENANT_NAME, agent_name: str = AGENT_NAME):
    """Create tenant and agent on backend"""
    log(f"Creating tenant: {tenant_name}")
    try:
        response = requests.post(f"{API_BACKEND}/tenants", json={'name': tenant_name}, timeout=30)
        response.raise_for_status()
        tenant_id = response.json().get('id')
        log("Tenant created", {'tenant_id': tenant_id})
    except Exception as e:
        log(f"Failed to create tenant: {e}")
        raise

    log(f"Creating agent: {agent_name}")
    try:
        response = requests.post(f"{API_BACKEND}/agents", json={'tenant_id': tenant_id, 'name': agent_name}, timeout=30)
        response.raise_for_status()
        agent_data = response.json()
        agent_id = agent_data.get('id')
        log("Agent created", {'agent_id': agent_id})
    except Exception as e:
        log(f"Failed to create agent: {e}")
        raise

    return tenant_id, agent_id


def upload_url_to_backend(url: str, tenant_id: str, agent_id: str):
    """Upload URL to backend for processing"""
    log(f"Uploading URL to backend: {url}")

    # Create a simple text file containing the URL
    files = {'file': (f'url_{int(time.time())}.txt', url.encode('utf-8'), 'text/plain')}

    upload_url = f"{API_BACKEND}/upload/{tenant_id}/{agent_id}"
    log(f"Uploading to: {upload_url}")

    try:
        response = requests.post(upload_url, files=files, timeout=60)
        response.raise_for_status()
        result = response.json()
        doc_id = result.get('id')
        log("URL uploaded successfully", {'doc_id': doc_id})
        return doc_id
    except Exception as e:
        log(f"Failed to upload URL: {e}")
        raise


def wait_for_embeddings(doc_id: str, max_retries: int = 60, retry_delay: float = 5.0):
    """Wait for document embeddings to be created"""
    log(f"Waiting for embeddings on document {doc_id}")

    for attempt in range(max_retries):
        try:
            response = requests.get(f"{INGESTION}/documents/{doc_id}/embeddings", timeout=30)
            if response.status_code == 200:
                data = response.json()
                embeddings_count = data.get('embeddings_count', 0)
                status = data.get('status', 'unknown')

                log(f"Embeddings status (attempt {attempt + 1}/{max_retries}): {embeddings_count} embeddings, status: {status}")

                if embeddings_count > 0:
                    log(f"✅ Embeddings completed for document {doc_id}")
                    return True, data
                elif status in ['failed', 'error']:
                    log(f"❌ Embeddings failed for document {doc_id}")
                    return False, data
            else:
                log(f"⚠️ Non-200 response: {response.status_code} - {response.text}")

        except Exception as e:
            log(f"⚠️ Error checking embeddings: {e}")

        if attempt < max_retries - 1:
            log(f"⏳ Waiting {retry_delay}s before next check...")
            time.sleep(retry_delay)

    log(f"❌ Embeddings timeout after {max_retries} attempts")
    return False, None


def test_agent_workflow(question: str, tenant_id: str, agent_id: str):
    """Test the agent workflow with a sample question"""
    log(f"Testing agent workflow with question: {question}")

    payload = {
        'query': question,
        'user_id': 'demo-user',
        'tenant_id': tenant_id,
        'agent_id': agent_id
    }

    try:
        response = requests.post(f"{AGENT_WORKFLOW}/query/stream", json=payload, timeout=60, stream=True)
        if response.status_code == 200:
            log("✅ Agent workflow query successful")
            # For streaming response, just check that we get a response
            # In a real implementation, you'd process the SSE stream
            content = response.text[:500]  # Get first 500 chars for logging
            log(f"Response preview: {content}...")
            return True
        else:
            log(f"❌ Agent workflow query failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        log(f"❌ Agent workflow test failed: {e}")
        return False


def setup_twilio_webhook(agent_id: str):
    """Setup Twilio webhook for the agent"""
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        log("⚠️ Twilio credentials not configured, skipping webhook setup")
        return None

    log("Setting up Twilio webhook...")

    try:
        # Import and run the Twilio setup script
        script_path = os.path.join(os.path.dirname(__file__), '..', 'agent-workflow', 'scripts', 'update_twilio_webhook.py')
        if not os.path.exists(script_path):
            log(f"⚠️ Twilio setup script not found: {script_path}")
            return None

        # Run the script
        cmd = [sys.executable, script_path, '--agent-id', agent_id]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            log("✅ Twilio webhook setup completed")
            # Extract phone number from output if available
            for line in result.stdout.split('\n'):
                if 'phone number' in line.lower() or 'Phone number' in line:
                    return line.split(':')[-1].strip()
            return TWILIO_PHONE_NUMBER  # Fallback
        else:
            log(f"❌ Twilio setup failed: {result.stderr}")
            return None

    except Exception as e:
        log(f"❌ Twilio setup error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='Complete VoiceFlow Demo')
    parser.add_argument('url', help='URL to extract content from')
    parser.add_argument('--skip-twilio', action='store_true', help='Skip Twilio setup')
    args = parser.parse_args()

    log("🚀 Starting Complete VoiceFlow Demo")
    log(f"📋 Target URL: {args.url}")

    # Check services
    if not check_services():
        log("❌ Service health check failed. Please ensure all services are running.")
        return 1

    try:
        # 1. Create tenant and agent
        log("📝 Step 1: Creating tenant and agent")
        tenant_id, agent_id = create_tenant_and_agent()

        # 2. Upload URL for processing
        log("📤 Step 2: Uploading URL for content extraction")
        doc_id = upload_url_to_backend(args.url, tenant_id, agent_id)

        # 3. Wait for embeddings
        log("⏳ Step 3: Waiting for content extraction and embeddings")
        success, embedding_data = wait_for_embeddings(doc_id)

        if not success:
            log("❌ Failed to create embeddings. Demo cannot continue.")
            return 1

        # 4. Test agent workflow
        log("🧠 Step 4: Testing agent workflow")
        test_question = f"What information can you provide about the content from {args.url}?"
        result = test_agent_workflow(test_question, tenant_id, agent_id)

        if result:
            log("✅ Agent workflow test successful")
        else:
            log("⚠️ Agent workflow test had issues, but continuing...")

        # 5. Setup Twilio (optional)
        phone_number = None
        if not args.skip_twilio:
            log("📞 Step 5: Setting up Twilio integration")
            phone_number = setup_twilio_webhook(agent_id)

        # 6. Summary
        log("🎉 Demo completed successfully!")
        log("📊 Summary:", {
            'tenant_id': tenant_id,
            'agent_id': agent_id,
            'document_id': doc_id,
            'phone_number': phone_number,
            'url_processed': args.url
        })

        if phone_number:
            print(f"\n🎯 CALL THIS NUMBER TO TEST: {phone_number}")
            print("The agent is now ready to answer questions about the extracted content!")
        else:
            print("\n✅ Demo completed! Agent is ready to answer questions about the extracted content.")
            print("💡 To enable phone calling, configure Twilio credentials and run again without --skip-twilio")

        return 0

    except Exception as e:
        log(f"💥 Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())