# Document Ingestion API

A comprehensive FastAPI service for ingesting documents, images, PDFs, and URLs with OCR, web scraping, embedding generation, and vector storage.

## Features

- 🔍 **Automatic File Type Detection**: Intelligently detects images, PDFs, documents, and URLs
- 📄 **OCR Processing**: Uses docTR for high-quality OCR on images and PDFs
- 🌐 **Advanced Web Scraping**: Powered by Crawl4AI with support for JavaScript, pagination, and dynamic content
- 🧠 **Vector Embeddings**: Generates embeddings using Sentence Transformers
- 💾 **Dual Storage**: Original documents in local Postgres (Docker), embeddings in ChromaDB
- 🔌 **Webhook Ready**: Designed for easy integration with external services
- 📊 **Full Logging**: Comprehensive logging for monitoring and debugging
- 🎯 **Modular Design**: Easy to extend and customize

## Architecture

```
Upload → File Detection → Processing (OCR/Scraping) → Chunking → Embedding → Storage
                                                                              ├── Postgres (Original)
                                                                              └── ChromaDB (Vectors)
```

## Installation

-### Prerequisites

- Python 3.9+
- Docker & docker-compose (we provide a compose file to run Postgres locally)
- System dependencies for python-magic:
  - **Ubuntu/Debian**: `sudo apt-get install libmagic1`
  - **macOS**: `brew install libmagic`
  - **Windows**: Install python-magic-bin instead

### Setup

1. **Clone and navigate to project**:
```bash
cd document-ingestion-api
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. **Create Postgres table** (the service will auto-create this on first run, but here's the SQL):
```sql
CREATE TABLE documents (
  id TEXT PRIMARY KEY,
  filename TEXT,
  file_type TEXT,
  file_size BIGINT,
  content BYTEA,
  metadata JSONB,
  status TEXT,
  error_message TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
```

## Running the Service

### Development
```bash
# For local development without auto-reload (recommended to avoid multi-process startup issues):
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Production
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### 1. Health Check
**GET** `/health`

Check if all services are running.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-10-01T12:00:00",
  "services": {
    "database": true,
    "vector_store": true,
    "ocr": true,
    "scraper": true
  }
}
```

### 2. File Upload Ingestion
**POST** `/ingest`

Upload and process any file (image, PDF, or text file with URL).

**Request:**
```bash
curl -X POST "http://localhost:8000/ingest" \
  -F "file=@document.pdf"
```

**Response:**
```json
{
  "status": "success",
  "message": "Document processed and stored successfully",
  "document_id": "123e4567-e89b-12d3-a456-426614174000",
  "chunks_created": 15,
  "processing_time": 3.45
}
```

### 3. URL Ingestion
**POST** `/ingest/url`

Scrape and process a URL.

**Request:**
```json
{
  "url": "https://example.com/article",
  "metadata": {
    "source": "blog",
    "category": "technology"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Document processed and stored successfully",
  "document_id": "123e4567-e89b-12d3-a456-426614174000",
  "chunks_created": 20,
  "processing_time": 5.23
}
```

### 4. Webhook Upload
**POST** `/webhook/upload`

Webhook endpoint for external services (same functionality as `/ingest`).

**Request:**
```bash
curl -X POST "http://localhost:8000/webhook/upload" \
  -F "file=@image.jpg"
```

### 5. Get Document
**GET** `/documents/{document_id}`

Retrieve document metadata and status.

**Response:**
```json
{
  "status": "success",
  "document": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "filename": "document.pdf",
    "file_type": "pdf",
    "status": "completed",
    "created_at": "2024-10-01T12:00:00",
    "metadata": {}
  }
}
```

### 6. Search Documents
**GET** `/search?query=your search query&limit=10`

Search documents using vector similarity.

**Response:**
```json
{
  "status": "success",
  "query": "machine learning",
  "results": [
    {
      "id": "doc_chunk_0",
      "document": "Text content about machine learning...",
      "metadata": {
        "document_id": "123e4567-e89b-12d3-a456-426614174000",
        "chunk_index": 0
      },
      "distance": 0.234
    }
  ]
}
```

## Frontend Integration

### Next.js Example

```typescript
// Upload file
const uploadFile = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  