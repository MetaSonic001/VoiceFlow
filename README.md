# VoiceFlow Multi-Tenant RAG System

A multi-tenant RAG (Retrieval-Augmented Generation) system with real-time voice capabilities using Twilio Media Streams.

## Architecture

- **Frontend**: Next.js with Clerk authentication
- **API Gateway**: NestJS (TypeScript)
- **Database**: PostgreSQL with Prisma ORM
- **Vector DB**: Chroma (one collection per tenant)
- **Ingestion Service**: FastAPI (Python) for document processing
- **Object Storage**: MinIO (S3-compatible)
- **Cache/Queue**: Redis
- **LLM**: Groq Cloud
- **Voice**: Twilio Media Streams with Vosk/Coqui TTS

## Features

- Multi-tenant architecture (users can create multiple agents)
- Document ingestion from URLs and PDFs
- Real-time voice conversations via Twilio
- RAG with context-aware responses
- Configurable embeddings and LLM settings per agent

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your credentials
3. Run `docker-compose up --build`

## Services

- NestJS Backend: http://localhost:8000
- Ingestion Service: http://localhost:8001
- Chroma: http://localhost:8000
- MinIO: http://localhost:9001
- PostgreSQL: localhost:5432
- Redis: localhost:6379

## API Endpoints

### Agents
- `POST /agents` - Create agent
- `GET /agents?userId=...` - List user agents
- `PUT /agents/:id` - Update agent

### Documents
- `POST /documents` - Create document
- `GET /documents?agentId=...` - List agent documents

### RAG
- `POST /rag/query` - Query agent with RAG

### Ingestion
- `POST /ingest` - Ingest documents (FastAPI service)

## Voice Integration

1. Set up Twilio account
2. Configure webhook to point to your NestJS WebSocket endpoint
3. Call the Twilio number to start voice conversation

## Environment Variables

See `.env.example` for all required variables.

## Development

```bash
# Backend
cd nestjs-backend
npm install
npm run start:dev

# Ingestion
cd ingestion-service
pip install -r requirements.txt
python main.py

# Frontend (existing)
cd voiceflow-ai-platform
npm run dev
```

## Testing

Run tests for NestJS:
```bash
cd nestjs-backend
npm run test
```

## Testing Ingestion Service

To test the scraping and Chroma DB storage:

1. Start the services: `docker-compose up --build`
2. Run the test script:
   ```bash
   cd ingestion-service
   python test_ingestion.py
   ```

This will:
- Scrape common URLs (Wikipedia, BBC, GitHub)
- Process and chunk the content
- Generate embeddings
- Store in Chroma collection `tenant_test-tenant-123`
- Show progress and completion status

### Verify Storage

After testing, check Chroma DB persistence:
- Collection `tenant_test-tenant-123` should exist
- Documents should be stored with metadata (agentId, source, etc.)
- Data persists across container restarts

### Test URLs Used
- https://en.wikipedia.org/wiki/Artificial_intelligence
- https://www.bbc.com/news
- https://github.com/microsoft/vscode

## Deployment

Use the docker-compose.yml for production deployment. Make sure to:
- Set strong passwords
- Configure proper networking
- Set up SSL certificates
- Configure backups for databases