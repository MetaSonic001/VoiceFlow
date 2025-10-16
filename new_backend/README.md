# VoiceFlow Backend Services

This directory contains the complete backend infrastructure for VoiceFlow, including the Express.js API backend, FastAPI ingestion service, and all required infrastructure services.

## Architecture

- **Express Backend** (Port 8000): Main API server with authentication, agent management, and orchestration
- **Ingestion Service** (Port 8001): Document processing and vector embedding service
- **PostgreSQL** (Port 5433): Primary database for application data
- **MinIO** (Ports 9000/9001): Object storage for documents and files
- **ChromaDB** (Port 8002): Vector database for embeddings
- **Redis** (Port 6379): Caching and session management

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Bun (for faster package management)
- Python 3.11+ (for local development)

### 1. Environment Setup

Copy the environment file and fill in your API keys:

```bash
cp .env.example .env
# Edit .env with your Clerk and Groq API keys
```

### 2. Start All Services

```bash
# Start all services with Docker Compose
docker-compose up -d

# Or use the convenience script
./start_all.bat
```

### 3. Verify Services

Check that all services are running:

```bash
docker-compose ps
```

Expected services:
- `postgres` - Database
- `minio` - Object storage
- `chroma` - Vector database
- `redis` - Cache
- `express-backend` - API server
- `ingestion-service` - Document processing

### 4. Database Setup

Run database migrations and seed data:

```bash
cd express-backend
bun run db:seed
```

### 5. Start Frontend

In a separate terminal:

```bash
cd ../voiceflow-ai-platform (1)
npm install
npm run dev
```

## Service Endpoints

| Service | URL | Description |
|---------|-----|-------------|
| Express Backend | http://localhost:8000 | Main API |
| Ingestion Service | http://localhost:8001 | Document processing |
| MinIO Console | http://localhost:9001 | Storage admin |
| ChromaDB | http://localhost:8002 | Vector database |
| PostgreSQL | localhost:5433 | Database |

## API Documentation

- Express Backend: http://localhost:8000/api-docs
- Ingestion Service: http://localhost:8001/docs

## Development

### Local Development (without Docker)

1. Start infrastructure services:
```bash
docker-compose up -d postgres minio chroma redis
```

2. Start Express backend:
```bash
cd express-backend
bun run dev
```

3. Start Ingestion service:
```bash
cd ../ingestion-service
python main.py
```

### Testing

```bash
# Backend tests
cd express-backend
bun test

# Ingestion service tests
cd ../ingestion-service
python test_ingestion.py
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://vf_admin:vf_secure_2025!@localhost:5433/voiceflow_prod` |
| `REDIS_HOST` | Redis hostname | `redis` (docker) / `localhost` (local) |
| `MINIO_ENDPOINT` | MinIO server URL | `http://minio:9000` |
| `CHROMA_URL` | ChromaDB server URL | `http://chroma:8000` |
| `FASTAPI_URL` | Ingestion service URL | `http://ingestion-service:8001` |
| `CLERK_SECRET_KEY` | Clerk authentication secret | Required |
| `GROQ_API_KEY` | Groq API key for embeddings | Required |

## Troubleshooting

### Service Health Checks

```bash
# Check all services
docker-compose ps

# View logs
docker-compose logs [service-name]

# Restart a service
docker-compose restart [service-name]
```

### Common Issues

1. **Port conflicts**: Ensure ports 8000-8002, 9000-9001, 5433, 6379 are available
2. **Database connection**: Wait for PostgreSQL to be healthy before starting other services
3. **MinIO access**: Use `minioadmin` / `minioadmin` for console access
4. **API keys**: Ensure Clerk and Groq API keys are properly set

### Reset Everything

```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Rebuild and restart
docker-compose up -d --build
```

## Integration with Frontend

The frontend (`voiceflow-ai-platform (1)`) is configured to call:
- API: `http://localhost:8000` (configured in `NEXT_PUBLIC_API_URL`)
- Authentication: Clerk (configured in `.env`)

All frontend actions (login, agent creation, document upload, chat) now connect to real backend APIs instead of using mock data.

- **Express Backend**: http://localhost:8000 (run locally)
- **FastAPI Ingestion**: http://localhost:8001 (run locally)
- **PostgreSQL**: localhost:5432 (Docker)
- **MinIO**: http://localhost:9000 (Docker)
- **Chroma DB**: http://localhost:8002 (Docker)
- **Redis**: localhost:6379 (run locally)

## Environment Setup

The `.env` files are configured for local development with Docker infrastructure services. Update the following placeholders:

- `GROQ_API_KEY`: Your Groq Cloud API key
- `TWILIO_ACCOUNT_SID`: Your Twilio account SID
- `TWILIO_AUTH_TOKEN`: Your Twilio auth token
- `TWILIO_PHONE_NUMBER`: Your Twilio phone number

Make sure Redis is installed and running locally:
```bash
# On macOS with Homebrew
brew install redis
brew services start redis

# On Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis

# On Windows (using WSL or Chocolatey)
choco install redis-64
redis-server
```

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
- `POST /ingestion/start` - Start document ingestion
- `GET /ingestion/status/:jobId` - Check ingestion status

### Runner (for frontend)
- `POST /runner/chat` - Chat with agent

## Testing

### Backend Tests
```bash
cd express-backend
npm test
```

### Scraping Test
```bash
cd ingestion-service
python test_scraping.py
```

### Full Ingestion Test
```bash
cd ingestion-service
python test_ingestion.py
```

## Frontend Integration

The backend is ready to connect with your Next.js frontend. The API endpoints match the expected frontend routes.

Update your frontend `.env`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Architecture

- **Multi-tenant**: Each user gets isolated Chroma collections (`tenant_<userId>`)
- **RAG Pipeline**: Chroma retrieval + Groq LLM generation
- **Voice**: Twilio Media Streams with real-time ASR/TTS
- **Ingestion**: URL scraping with Crawl4AI + Playwright fallback
- **Persistence**: All data stored in Docker volumes</content>
<parameter name="filePath">c:\VoiceFlow\new_backend\README.md