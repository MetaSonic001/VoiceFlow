from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import uuid
from datetime import datetime
import redis
import chromadb
from chromadb.config import Settings
import trafilatura
from bs4 import BeautifulSoup
import asyncio
from playwright.async_api import async_playwright
from pdfminer.high_level import extract_text
import boto3
from sentence_transformers import SentenceTransformer
import groq
from groq import Groq
import io
from crawl4ai import AsyncWebCrawler

app = FastAPI(title="Ingestion Service", version="1.0.0")

# Initialize clients
redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=int(os.getenv("REDIS_PORT", 6379)), decode_responses=True)
chroma_client = chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", "./chroma_db"))
s3_client = boto3.client(
    's3',
    endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
    aws_access_key_id=os.getenv("MINIO_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("MINIO_SECRET_KEY")
)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Load embedding model
embedding_model = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))

class IngestRequest(BaseModel):
    tenantId: str
    agentId: str
    urls: Optional[List[str]] = []
    s3_urls: Optional[List[str]] = []

class IngestResponse(BaseModel):
    job_id: str
    status: str

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ingestion-service", "timestamp": datetime.now().isoformat()}

@app.post("/ingest", response_model=IngestResponse)
async def ingest_documents(request: IngestRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    redis_client.set(f"job:{job_id}", "processing")
    redis_client.set(f"job:{job_id}:progress", "0")

    background_tasks.add_task(process_ingestion, job_id, request.tenantId, request.agentId, request.urls or [], request.s3_urls or [])

    return IngestResponse(job_id=job_id, status="processing")

@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    status = redis_client.get(f"job:{job_id}")
    progress = redis_client.get(f"job:{job_id}:progress")
    return {"status": status, "progress": progress}

async def process_ingestion(job_id: str, tenant_id: str, agent_id: str, urls: List[str], s3_urls: List[str]):
    try:
        collection_name = f"tenant_{tenant_id}"
        collection = chroma_client.get_or_create_collection(name=collection_name)

        total_items = len(urls) + len(s3_urls)
        processed = 0

        # Process URLs
        for url in urls:
            try:
                content = await scrape_url(url)
                if content:
                    chunks = chunk_text(content, url)
                    embeddings = embedding_model.encode(chunks)
                    ids = [f"{agent_id}_{url}_{i}" for i in range(len(chunks))]
                    metadatas = [{"agentId": agent_id, "source": url, "chunk": i} for i in range(len(chunks))]
                    collection.add(ids=ids, embeddings=embeddings.tolist(), metadatas=metadatas, documents=chunks)
            except Exception as e:
                print(f"Error processing URL {url}: {e}")

            processed += 1
            redis_client.set(f"job:{job_id}:progress", str(int(processed / total_items * 100)))

        # Process S3 URLs
        for s3_url in s3_urls:
            try:
                content = await download_from_s3(s3_url)
                if content:
                    chunks = chunk_text(content, s3_url)
                    embeddings = embedding_model.encode(chunks)
                    ids = [f"{agent_id}_{s3_url}_{i}" for i in range(len(chunks))]
                    metadatas = [{"agentId": agent_id, "source": s3_url, "chunk": i} for i in range(len(chunks))]
                    collection.add(ids=ids, embeddings=embeddings.tolist(), metadatas=metadatas, documents=chunks)
            except Exception as e:
                print(f"Error processing S3 URL {s3_url}: {e}")

            processed += 1
            redis_client.set(f"job:{job_id}:progress", str(int(processed / total_items * 100)))

        redis_client.set(f"job:{job_id}", "completed")

    except Exception as e:
        redis_client.set(f"job:{job_id}", f"failed: {str(e)}")

async def scrape_url(url: str) -> Optional[str]:
    try:
        # Try Crawl4AI first for AI-driven scraping
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            if result and result.markdown:
                return result.markdown

        # Fallback to trafilatura for static pages
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            content = trafilatura.extract(downloaded)
            if content and len(content) > 100:
                return content

        # Last fallback to Playwright for dynamic content
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            html = await page.content()
            await browser.close()

            soup = BeautifulSoup(html, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            text = soup.get_text()
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            return text
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

async def download_from_s3(s3_url: str) -> Optional[str]:
    try:
        # Parse S3 URL: s3://bucket/key
        if s3_url.startswith("s3://"):
            parts = s3_url[5:].split("/", 1)
            bucket = parts[0]
            key = parts[1]

            response = s3_client.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read()

            # Check if PDF
            if key.lower().endswith('.pdf'):
                text = extract_text(io.BytesIO(content))
                return text
            else:
                # Assume text file
                return content.decode('utf-8')
    except Exception as e:
        print(f"Error downloading from S3 {s3_url}: {e}")
        return None

def chunk_text(text: str, source: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = ' '.join(words[start:end])
        chunks.append(chunk)
        start = end - overlap
        if start >= len(words):
            break
    return chunks

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)