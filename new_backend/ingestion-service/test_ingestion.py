#!/usr/bin/env python3
"""
Enhanced test script for the ingestion service
Tests various document types, OCR capabilities, and web scraping
"""

import requests
import time
import json
from pathlib import Path

# Test configuration
INGESTION_URL = "http://localhost:8001"

# Test URLs for web scraping
test_urls = [
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://www.bbc.com/news",
    "https://github.com/microsoft/vscode",
]

# Test S3 URLs (add your actual test files here)
test_s3_urls = [
    # Document files
    # "s3://documents/sample.pdf",      # PDF with text
    # "s3://documents/scanned.pdf",    # Scanned PDF (will use OCR)
    # "s3://documents/document.docx",  # Word document
    # "s3://documents/legacy.doc",     # Legacy Word document
    # "s3://documents/spreadsheet.xlsx", # Excel spreadsheet
    # "s3://documents/presentation.pptx", # PowerPoint presentation

    # Image files (OCR)
    # "s3://documents/text_page.png",  # Image with text
    # "s3://documents/scanned_doc.jpg", # Scanned document image

    # Text files
    # "s3://documents/article.txt",    # Plain text
    # "s3://documents/data.csv",       # CSV data
    # "s3://documents/readme.md",      # Markdown
]

def test_health():
    """Test service health"""
    print("🏥 Testing service health...")
    try:
        response = requests.get(f"{INGESTION_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Service healthy: {data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to service: {e}")
        return False

def test_url_ingestion():
    """Test URL ingestion with web scraping"""
    print("\n🌐 Testing URL ingestion...")

    test_data = {
        "tenantId": "test-tenant-enhanced",
        "agentId": "test-agent-web",
        "urls": test_urls,
        "s3_urls": []
    }

    response = requests.post(f"{INGESTION_URL}/ingest", json=test_data)
    if response.status_code == 200:
        job_id = response.json()["job_id"]
        print(f"✅ URL ingestion started with job ID: {job_id}")

        # Poll for completion
        poll_status(job_id)
        return job_id
    else:
        print(f"❌ Failed to start URL ingestion: {response.status_code}, {response.text}")
        return None

def test_document_ingestion():
    """Test document ingestion with various file types"""
    print("\n📁 Testing document ingestion...")

    if not test_s3_urls:
        print("⚠️ No test S3 URLs configured. Add file URLs to test_s3_urls list.")
        return None

    test_data = {
        "tenantId": "test-tenant-enhanced",
        "agentId": "test-agent-docs",
        "urls": [],
        "s3_urls": test_s3_urls
    }

    response = requests.post(f"{INGESTION_URL}/ingest", json=test_data)
    if response.status_code == 200:
        job_id = response.json()["job_id"]
        print(f"✅ Document ingestion started with job ID: {job_id}")

        # Poll for completion
        poll_status(job_id)
        return job_id
    else:
        print(f"❌ Failed to start document ingestion: {response.status_code}, {response.text}")
        return None

def poll_status(job_id):
    """Poll job status until completion"""
    while True:
        status_response = requests.get(f"{INGESTION_URL}/status/{job_id}")
        if status_response.status_code == 200:
            status_data = status_response.json()
            status = status_data['status']
            progress = status_data.get('progress', 'N/A')

            print(f"📊 Status: {status}, Progress: {progress}%")

            if status in ['completed', 'failed']:
                if status == 'completed':
                    print("✅ Job completed successfully!")
                else:
                    print("❌ Job failed!")
                break
        else:
            print(f"❌ Error checking status: {status_response.status_code}")
            break

        time.sleep(3)  # Check every 3 seconds

def show_capabilities():
    """Display enhanced service capabilities"""
    print("\n🎯 Enhanced Ingestion Service Capabilities:")
    print("=" * 60)

    print("🌐 Web Scraping (4-Strategy Approach):")
    print("   • Crawl4AI: AI-driven with content waiting & overlay removal")
    print("   • Trafilatura: Precision article extraction with tables")
    print("   • Playwright: Dynamic/SPA with smart element selection")
    print("   • Scrapy: Framework-based for complex scraping needs")
    print()

    print("� Document Processing (Enterprise-Grade):")
    print("   • PDFs: Text extraction + automatic OCR for scanned docs")
    print("   • Word: DOCX (full text/tables) + DOC (legacy support)")
    print("   • Excel: Multi-sheet processing with detailed metadata")
    print("   • PowerPoint: Slide-by-slide extraction with content analysis")
    print("   • Images: Dual OCR engines (DocTR + Tesseract)")
    print("   • Text Files: Multiple formats with encoding detection")
    print("   • Universal: Unstructured library for any document type")
    print()

    print("🧠 Smart Processing:")
    print("   • Semantic chunking with LangChain RecursiveCharacterTextSplitter")
    print("   • Rich metadata extraction for all document types")
    print("   • Automatic OCR detection and processing")
    print("   • Vector embeddings with sentence-transformers")
    print("   • ChromaDB for efficient semantic retrieval")
    print()

    print("🔧 Advanced Features:")
    print("   • Multi-strategy web scraping with automatic fallbacks")
    print("   • Comprehensive error handling and recovery")
    print("   • Batch processing with real-time progress tracking")
    print("   • Memory-efficient streaming for large files")
    print("   • File type auto-detection and appropriate processing")

def main():
    """Main test function"""
    print("🧪 Enhanced Ingestion Service Test Suite")
    print("=" * 50)

    if not test_health():
        return

    # Test URL ingestion
    url_job = test_url_ingestion()

    # Test document ingestion (if configured)
    doc_job = test_document_ingestion()

    # Show capabilities
    show_capabilities()

    print("\n📋 Test Summary:")
    print(f"   • URL ingestion job: {url_job or 'Not run'}")
    print(f"   • Document ingestion job: {doc_job or 'Not run'}")
    print("\n💡 To test document ingestion:")
    print("   1. Upload test files to MinIO bucket")
    print("   2. Add S3 URLs to test_s3_urls list")
    print("   3. Re-run this test")

    print("\n✨ Test completed!")

if __name__ == "__main__":
    main()