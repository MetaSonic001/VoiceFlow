# AI Customer Service Platform - Complete Setup Guide

## Overview

This platform allows companies to create custom AI-powered customer service agents by uploading their standard operating procedures (SOPs), documents, or website content. The system creates intelligent voice and chat agents that can handle customer queries using the company's specific knowledge base.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Document      │    │    Knowledge     │    │   AI Customer   │
│   Ingestion     │───▶│     Base         │───▶│   Service       │
│   Workflow      │    │  (Vector DB)     │    │    Agents       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

**Core Components:**
- **n8n**: Workflow orchestration and automation
- **Ollama**: Local AI models for embeddings and text generation
- **Pinecone**: Vector database for semantic search
- **Custom Docker Image**: Web scraping and document processing
- **PostgreSQL**: Metadata storage

## System Requirements

- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 20GB free space
- **Docker Desktop**: Latest version
- **Internet**: Required for API access

## Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo>
cd ai-customer-service-platform
```

### 2. Create Required Files

**Create `docker-compose.yml`:**
```yaml
services:
  n8n:
    image: n8n-custom
    restart: always
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=password123
      - N8N_HOST=localhost
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - N8N_EXECUTIONS_DATA_SAVE_ON_SUCCESS=all
      - N8N_EXECUTIONS_DATA_SAVE_ON_ERROR=all
      - NODE_OPTIONS=--max-old-space-size=8192
      - N8N_EXECUTIONS_DATA_MAX_SIZE=100000000
      - N8N_EXECUTIONS_BUFFER_SIZE=500000000
      - N8N_DEFAULT_BINARY_DATA_MODE=filesystem
      - N8N_EXECUTIONS_DATA_SAVE_MANUAL_EXECUTIONS=true
      - N8N_LOG_LEVEL=debug
      - N8N_EXECUTIONS_PROCESS=main
      - N8N_PAYLOAD_SIZE_MAX=100000000
      - N8N_METRICS=false
      - N8N_DISABLE_PRODUCTION_MAIN_PROCESS=false
    volumes:
      - n8n_data:/home/node/.n8n
      - ./scripts:/app/scripts
      
  ollama:
    image: ollama/ollama
    restart: always
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
      
  postgres:
    image: postgres:15
    restart: always
    environment:
      - POSTGRES_DB=n8n_db
      - POSTGRES_USER=n8n_user
      - POSTGRES_PASSWORD=n8n_pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  n8n_data:
  postgres_data:
  ollama_data:
```

### 3. Build and Start Services

```bash
# Build custom n8n image with scraping capabilities
docker build -t n8n-custom .

# Start all services
docker-compose up -d

# Check if services are running
docker-compose ps
```

### 4. Setup AI Models

```bash
# Install required Ollama models
docker exec -it <ollama-container-id> ollama pull nomic-embed-text
docker exec -it <ollama-container-id> ollama pull llama3.2:1b
# docker exec -it f79d9dd4bc38 ollama pull llama3.2:1b

# Verify models are installed
docker exec -it <ollama-container-id> ollama list
```

### 5. Setup API Keys

You'll need accounts and API keys from:
- **Pinecone** (free tier): https://pinecone.io
- **OCR.space** (free tier): https://ocr.space/ocrapi

## Workflow Descriptions

### 1. Document Ingestion Workflow

**Purpose**: Processes and stores company knowledge from various sources

**Input Sources**:
- Website URLs (automatically scraped)
- PDF documents (OCR processed)
- DOCX files (text extracted)
- Audio files (speech-to-text)

**Process Flow**:
```
Webhook Input → File Type Detection → Content Processing → Text Chunking → 
Generate Embeddings → Store in Vector DB → Return Success
```

**Key Nodes**:
- **Webhook Trigger**: `POST /webhook/ingest-document`
- **File Type Detection**: Determines processing method
- **Execute Command**: Runs scraping scripts for websites
- **Text Processing**: Splits content into searchable chunks
- **Ollama Embeddings**: Creates semantic vectors (768 dimensions)
- **Pinecone Storage**: Stores vectors with metadata

**API Endpoint**: `http://localhost:5678/webhook/ingest-document`

**Example Usage**:
```bash
curl -X POST http://localhost:5678/webhook/ingest-document \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "your_company",
    "project_id": "knowledge_base",
    "url": "https://yourcompany.com/faq",
    "file_type": "website"
  }'
```

### 2. Runtime Agent Workflow

**Purpose**: Handles customer queries using stored knowledge

**Process Flow**:
```
Customer Query → Generate Query Embedding → Search Vector DB → 
Retrieve Context → Build AI Prompt → Generate Response → Return Answer
```

**Key Nodes**:
- **Webhook Trigger**: `POST /webhook/agent-chat`
- **Query Processing**: Extracts and validates input
- **Ollama Query Embeddings**: Converts query to vector
- **Vector Search**: Finds relevant knowledge chunks
- **RAG Prompt Builder**: Constructs context-aware prompt
- **LLM Generation**: Generates intelligent response
- **Response Formatter**: Structures final output

**API Endpoint**: `http://localhost:5678/webhook/agent-chat`

**Example Usage**:
```bash
curl -X POST http://localhost:5678/webhook/agent-chat \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "your_company",
    "query": "What are your business hours?",
    "conversation_id": "conv_123"
  }'
```

## Platform Access

### n8n Dashboard
- **URL**: http://localhost:5678
- **Username**: admin
- **Password**: password123

### Ollama API
- **URL**: http://localhost:11434
- **Health Check**: `curl http://localhost:11434/api/tags`

### PostgreSQL Database
- **Host**: localhost:5432
- **Database**: n8n_db
- **Username**: n8n_user
- **Password**: n8n_pass

## Configuration Files

### Scripts Directory Structure
```
scripts/
├── scraper.js          # Puppeteer-based web scraper
├── static_scraper.py   # Python-based text extractor
└── requirements.txt    # Python dependencies
```

### Custom Dockerfile Features
- **Multi-language support**: Node.js, Python, Bun runtime
- **Web scraping**: Chromium + Puppeteer for dynamic content
- **Text extraction**: Trafilatura for clean content extraction
- **AI capabilities**: Sentence transformers for embeddings
- **File processing**: Support for various document formats

## API Reference

### Document Ingestion API

**Endpoint**: `POST /webhook/ingest-document`

**Request Body**:
```json
{
  "company_id": "string",     // Required: Company identifier
  "project_id": "string",     // Required: Project identifier  
  "url": "string",           // For website scraping
  "file_data": "string",     // Base64 encoded file
  "file_type": "string",     // pdf|docx|audio|website
  "text_content": "string"  // Direct text input
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Document processed and stored",
  "chunks_created": 15,
  "company_id": "your_company",
  "project_id": "knowledge_base"
}
```

### Chat Agent API

**Endpoint**: `POST /webhook/agent-chat`

**Request Body**:
```json
{
  "company_id": "string",      // Required: Company identifier
  "query": "string",           // Required: Customer question
  "conversation_id": "string", // Optional: Session tracking
  "channel": "string"          // Optional: chat|voice|whatsapp
}
```

**Response**:
```json
{
  "success": true,
  "response": "Based on your company policy...",
  "conversation_id": "conv_123",
  "company_id": "your_company",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

## Troubleshooting

### Common Issues

**1. "Docker not found"**
```bash
# Restart Docker Desktop and try again
docker --version
```

**2. "Port already in use"**
```bash
# Change ports in docker-compose.yml
# n8n: 5678 → 5679
# ollama: 11434 → 11435
```

**3. "Ollama models not found"**
```bash
# Re-install models
docker exec -it $(docker ps -q --filter ancestor=ollama/ollama) ollama pull nomic-embed-text
```

**4. "Vector search returns empty results"**
- Check if documents were successfully ingested
- Verify Pinecone index has vectors
- Ensure company_id matches between ingestion and queries

**5. "n8n workflows not working"**
- Import workflow JSON files through n8n interface
- Check node connections and configuration
- Verify API keys are properly set

### Debug Commands

```bash
# View container logs
docker-compose logs n8n
docker-compose logs ollama

# Check service health
curl http://localhost:5678/healthz  # n8n
curl http://localhost:11434/api/tags  # ollama

# Access container shell
docker exec -it n8n-n8n-1 /bin/bash
```

### Performance Optimization

**For Production Use**:
- Increase memory allocation in docker-compose.yml
- Use GPU acceleration for Ollama (add runtime: nvidia)
- Set up load balancing for multiple n8n instances
- Configure database connection pooling
- Implement caching for frequent queries

## Security Considerations

- Change default passwords in production
- Use environment variables for API keys
- Implement authentication middleware
- Set up SSL/TLS certificates
- Configure firewall rules
- Regular backup of vector database

## Scaling and Deployment

**Development**: Current setup handles 10-50 concurrent users
**Production**: Requires additional infrastructure:
- Load balancers
- Database clustering  
- Container orchestration (Kubernetes)
- Monitoring and logging systems
- CDN for static assets

## Support

For issues and questions:
1. Check troubleshooting section
2. Review Docker logs
3. Test individual components
4. Verify API connectivity

This platform provides a complete foundation for building AI-powered customer service solutions with your own data and requirements.