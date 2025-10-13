#!/usr/bin/env python3
"""
Demo setup script: scrape FR CRCE websites, ingest documents and embeddings into ChromaDB,
and optionally run Twilio webhook updater to point an incoming number at the agent workflow.

Usage:
  python demo_setup_fr_crce.py [--run-twilio]

Config (via .env or environment):
  - CHROMA_DB_PATH (defaults to ../document-ingestion/chroma_db)
  - INGESTION_LOG_DIR (optional)
  - TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN optionally for webhook update
  - NGROK_PORT optionally

This script uses only code from the `document-ingestion` and `agent-workflow` folders.
"""

import os
import sys
import argparse
import asyncio
import logging
import uuid
import json
import subprocess
from datetime import datetime

# allow importing document-ingestion services
INGESTION_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'document-ingestion'))
if INGESTION_PATH not in sys.path:
    sys.path.insert(0, INGESTION_PATH)

try:
    from services.web_scraper import WebScraper
    from services.embedder import TextEmbedder
    from services.vector_store import VectorStore
    from services.database import DatabaseManager
except Exception as e:
    print("Failed to import document-ingestion services. Ensure you installed requirements and the repo layout is intact:", e)
    raise

try:
    import chromadb
    from chromadb.config import Settings
except Exception:
    chromadb = None

from dotenv import load_dotenv

load_dotenv()

# Setup logging
LOG_DIR = os.environ.get('INGESTION_LOG_DIR', os.path.join(os.getcwd(), 'ingestion_logs'))
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, f'demo_setup_{datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")}.log')

logger = logging.getLogger('demo_setup')
logger.setLevel(logging.INFO)
fh = logging.FileHandler(log_file)
fh.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)


async def scrape_and_store(urls, tenant_id: str, agent_id: str, collection_name: str = None):
    """Scrape given URLs, store raw document via DatabaseManager, create embeddings and store in ChromaDB."""
    logger.info(f"Starting demo ingestion for tenant={tenant_id} agent={agent_id}")

    scraper = WebScraper()
    embedder = TextEmbedder()
    dbm = DatabaseManager()

    # Setup Chroma client
    chroma_path = os.environ.get('CHROMA_DB_PATH', os.path.normpath(os.path.join(INGESTION_PATH, 'chroma_db')))
    logger.info(f"Using ChromaDB path: {chroma_path}")
    if chromadb is None:
        logger.error('chromadb package is not installed; embeddings storage will fail')
        raise RuntimeError('chromadb missing')

    client = chromadb.PersistentClient(path=chroma_path, settings=Settings(anonymized_telemetry=False))
    if not collection_name:
        collection_name = f"{tenant_id}_{agent_id}".replace('-', '_')
    logger.info(f"Target collection: {collection_name}")
    coll = client.get_or_create_collection(name=collection_name, metadata={})

    summary = []

    for idx, url in enumerate(urls, start=1):
        logger.info(f"[{idx}/{len(urls)}] Scraping URL: {url}")
        try:
            content = await scraper.scrape(url, wait_for_js=True)
            if not content:
                logger.warning(f"Empty content returned for {url}; skipping")
                continue
            logger.info(f"Scraped {len(content)} characters from {url}")

            # store raw document in ingestion DB (writes to backend via adapter or pending dir)
            filename = f"scrape_{uuid.uuid4().hex[:8]}.txt"
            metadata = { 'source': url, 'tenant_id': tenant_id, 'agent_id': agent_id }
            try:
                doc_id = await dbm.store_document(filename, content.encode('utf-8'), 'url', metadata)
                logger.info(f"Stored document id={doc_id} filename={filename}")
            except Exception:
                logger.exception('Failed to store document via DatabaseManager; writing to local pending dir fallback')
                # fallback: write to pending_documents directory
                pending_dir = os.path.join(INGESTION_PATH, 'pending_documents')
                os.makedirs(pending_dir, exist_ok=True)
                local_path = os.path.join(pending_dir, f"{uuid.uuid4().hex}.txt")
                with open(local_path, 'w', encoding='utf-8') as fh:
                    fh.write(content)
                doc_id = os.path.basename(local_path)
                logger.info(f"Wrote fallback pending document: {local_path}")

            # chunk and embed
            chunks = embedder.chunk_text(content)
            if not chunks:
                logger.warning(f"No chunks produced for {url}; skipping embeddings")
                summary.append({'url': url, 'doc_id': doc_id, 'chunks': 0})
                continue
            logger.info(f"Chunked into {len(chunks)} chunks; generating embeddings (this may take some time)...")
            embeddings = await embedder.embed_chunks(chunks)
            logger.info(f"Generated {len(embeddings)} embeddings")

            # prepare ids and metadata
            ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            docs = chunks
            metadatas = []
            for i, c in enumerate(chunks):
                metadatas.append({
                    'document_id': doc_id,
                    'chunk_index': i,
                    'source_url': url,
                    'tenant_id': tenant_id,
                    'agent_id': agent_id,
                    'timestamp': datetime.utcnow().isoformat()
                })

            # add to chroma
            logger.info(f"Adding {len(ids)} embeddings to Chroma collection {collection_name}")
            try:
                coll.add(ids=ids, embeddings=embeddings, documents=docs, metadatas=metadatas)
                logger.info(f"Added embeddings for document {doc_id} to collection {collection_name}")
            except Exception as e:
                logger.exception(f"Failed to add embeddings to chroma: {e}")

            summary.append({'url': url, 'doc_id': doc_id, 'chunks': len(chunks), 'ids_sample': ids[:3]})

        except Exception as e:
            logger.exception(f"Failed processing {url}: {e}")

    logger.info("Ingestion completed. Summary:")
    logger.info(json.dumps(summary, indent=2))
    logger.info(f"Chroma collection '{collection_name}' now has approx. {coll.count()} items (if supported)")
    return collection_name, summary


def run_twilio_updater(run_script: bool = True):
    """Run the update_twilio_webhook.py script in the agent-workflow/scripts folder as a subprocess and stream its output."""
    script_path = os.path.normpath(os.path.join(os.path.dirname(__file__), 'update_twilio_webhook.py'))
    if not os.path.exists(script_path):
        # the script is one level up in scripts; fall back
        script_path = os.path.normpath(os.path.join(os.path.dirname(__file__), 'update_twilio_webhook.py'))
    if not os.path.exists(script_path):
        logger.error("update_twilio_webhook.py not found in scripts folder; cannot update Twilio webhooks")
        return False

    logger.info(f"Running Twilio webhook updater script: {script_path}")
    try:
        # Run the script and stream stdout/stderr
        proc = subprocess.Popen([sys.executable, script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=os.environ.copy())
        # stream output
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                logger.info(f"[twilio-updater] {line.strip()}")
        ret = proc.wait()
        logger.info(f"Twilio updater exited with code {ret}")
        return ret == 0
    except Exception as e:
        logger.exception(f"Failed to run twilio updater: {e}")
        return False


async def main(urls, run_twilio=False, collection_name=None):
    # generate tenant and agent ids for demo
    tenant_id = os.environ.get('DEMO_TENANT_ID') or str(uuid.uuid4())
    agent_id = os.environ.get('DEMO_AGENT_ID') or str(uuid.uuid4())

    logger.info(f"Demo tenant_id={tenant_id} agent_id={agent_id}")

    coll, summary = await scrape_and_store(urls, tenant_id, agent_id, collection_name=collection_name)

    if run_twilio:
        ok = run_twilio_updater(True)
        if ok:
            logger.info('Twilio webhook update completed successfully')
        else:
            logger.warning('Twilio webhook update failed or was aborted')

    logger.info('Demo script finished')
    logger.info(f"Chroma collection name: {coll}")
    logger.info(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Demo setup: scrape FR CRCE sites and create agent embeddings')
    parser.add_argument('--run-twilio', action='store_true', help='Run Twilio webhook updater after ingest')
    parser.add_argument('--collection', help='Override target Chroma collection name')
    parser.add_argument('urls', nargs='*', help='Optional list of URLs to scrape (overrides internal default)')
    args = parser.parse_args()

    # default list of FR CRCE URLs (example; replace/add as needed)
    default_urls = [
        'https://frcrce.ac.in/',
        'https://frcrce.ac.in/department/department-of-computer-engineering/',
    ]
    urls = args.urls if args.urls else default_urls

    logger.info(f"Starting demo with {len(urls)} URLs")
    try:
        asyncio.run(main(urls, run_twilio=args.run_twilio, collection_name=args.collection))
    except KeyboardInterrupt:
        logger.warning('Interrupted by user')
    except Exception as e:
        logger.exception(f"Demo script error: {e}")
        sys.exit(1)
