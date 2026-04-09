# Enhanced Ingestion Service

A comprehensive document ingestion service that handles web scraping, document processing, OCR, and vector embeddings for intelligent retrieval.

## 🚀 Features

### 🌐 **Advanced Web Scraping**
- **Crawl4AI**: AI-driven extraction with content waiting and overlay removal
- **Trafilatura**: Precision article extraction with table/image handling
- **Playwright**: Dynamic content rendering with smart element selection
- **Scrapy**: Framework-based scraping for complex sites
- **Automatic Fallback Chain**: Tries all methods for maximum success rate

### 📄 **Comprehensive Document Processing**

#### **Word Documents**
- **DOCX**: Full paragraph, table, and formatting extraction
- **DOC**: Legacy format support via unstructured library
- **Metadata**: Paragraph count, table count, word statistics

#### **Excel Spreadsheets**
- **Multi-sheet Support**: Processes all sheets with individual metadata
- **Structured Output**: Tabular data converted to readable text
- **Rich Metadata**: Row/column counts, sheet details, non-null statistics

#### **PowerPoint Presentations**
- **Slide-by-slide Extraction**: Detailed content breakdown
- **Element Analysis**: Titles, content shapes, text elements
- **Metadata**: Slide counts, content analysis, word statistics

#### **PDF Documents**
- **Text Extraction**: Native text layer processing
- **OCR Integration**: Automatic scanned document detection
- **DocTR Priority**: High-quality OCR with Tesseract fallback

#### **Image Documents**
- **OCR Processing**: Text extraction from images
- **Format Support**: PNG, JPG, JPEG, TIFF, BMP
- **Dual Engine**: DocTR + Tesseract for maximum accuracy

#### **Text & Code Files**
- **Format Detection**: TXT, MD, CSV, JSON, XML, HTML
- **Encoding Handling**: UTF-8 with Latin-1 fallback
- **Universal Processing**: Unstructured library for unknown formats

### 🧠 Smart Processing
- **Semantic Chunking**: Intelligent text splitting using LangChain
- **OCR Integration**: DocTR for high-quality OCR with Tesseract fallback
- **Rich Metadata**: Comprehensive document metadata storage
- **Vector Embeddings**: Sentence-transformers for semantic search
- **ChromaDB Storage**: Efficient vector database for retrieval

## 🛠️ Setup

### Prerequisites
```bash
pip install -r requirements.txt
```

### Environment Variables
```bash
# Database & Infrastructure
DATABASE_URL=postgresql://user:pass@localhost:5433/db
CHROMA_URL=http://localhost:8002
MINIO_ENDPOINT=http://localhost:9000
REDIS_HOST=localhost

# Service Configuration
HOST=0.0.0.0
PORT=8001
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Document Processing
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_FILE_SIZE_MB=50

# OCR Settings
ENABLE_OCR=true
OCR_MODEL=doctr  # or tesseract
```

### Running the Service
```bash
python main.py
```

## 📡 API Endpoints

### POST /ingest
Ingest documents and URLs for processing.

**Request Body:**
```json
{
  "tenantId": "string",
  "agentId": "string",
  "urls": ["https://example.com"],
  "s3_urls": ["s3://bucket/document.pdf"]
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "processing"
}
```

### GET /status/{job_id}
Check ingestion job status and progress.

**Response:**
```json
{
  "status": "completed|processing|failed",
  "progress": "100"
}
```

### GET /health
Service health check.

## 🧪 Testing

Run the comprehensive test suite:
```bash
python test_ingestion.py
```

## 📊 Supported File Types

| Category | Extensions | Processing Method | OCR Support | Metadata |
|----------|------------|------------------|-------------|----------|
| **PDF** | .pdf | Text extraction + OCR | ✅ Auto-detect | Page count, OCR status |
| **Word** | .docx, .doc | Full text + tables | ❌ | Paragraphs, tables, words |
| **Excel** | .xlsx, .xls | Multi-sheet processing | ❌ | Sheets, rows, columns |
| **PowerPoint** | .pptx, .ppt | Slide-by-slide | ❌ | Slides, elements, content |
| **Images** | .png, .jpg, .jpeg, .tiff, .bmp | OCR processing | ✅ Primary | Dimensions, format |
| **Text Files** | .txt, .md, .csv, .json, .xml, .html | Direct decoding | ❌ | File size, encoding |
| **Web Pages** | URLs | Multi-strategy scraping | ❌ | Content type, method |
| **Other** | Any | Unstructured library | Varies | Elements, structure |

## 🔧 OCR Configuration

The service uses **DocTR** for high-quality OCR:
- Automatic detection of scanned PDFs
- Image text extraction
- Fallback to Tesseract if DocTR unavailable

## 🗄️ Vector Storage

Documents are processed into:
- **Semantic chunks** using LangChain text splitters
- **Vector embeddings** using sentence-transformers
- **Rich metadata** including file type, processing method, OCR status
- **ChromaDB collections** organized by tenant

## 🚀 Smart Retrieval

The processed documents enable:
- **Semantic search** across all content types
- **Hybrid retrieval** combining keyword and vector search
- **Metadata filtering** by document type, source, etc.
- **Context-aware responses** in RAG applications

## 📈 Performance

- **Batch processing** with progress tracking
- **Asynchronous operations** for large documents
- **Memory efficient** streaming for large files
- **Error resilience** with individual file failure handling

## 🔒 Security

- **File type validation**
- **Size limits** (configurable)
- **Safe temporary file handling**
- **Input sanitization**

## 🤝 Integration

Works seamlessly with:
- **Agent Runner Service** for RAG applications
- **MinIO** for file storage
- **ChromaDB** for vector search
- **Redis** for job tracking
- **PostgreSQL** for metadata

## 📝 Usage Examples

### Ingest Web Content
```python
import requests

response = requests.post("http://localhost:8001/ingest", json={
    "tenantId": "my-tenant",
    "agentId": "my-agent",
    "urls": ["https://example.com/article"]
})
```

### Ingest Documents
```python
response = requests.post("http://localhost:8001/ingest", json={
    "tenantId": "my-tenant",
    "agentId": "my-agent",
    "s3_urls": ["s3://documents/manual.pdf", "s3://documents/chart.xlsx"]
})
```

### Check Processing Status
```python
status = requests.get("http://localhost:8001/status/job-uuid")
print(status.json())
```