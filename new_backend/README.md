# VoiceFlow Backend

Complete multi-tenant RAG system with NestJS backend and FastAPI ingestion service.

## Quick Start

1. **Start infrastructure services:**
   ```bash
   cd new_backend
   docker-compose up -d
   ```

2. **Run setup script (Windows):**
   ```bash
   setup.bat
   ```

   Or manually:
   ```bash
   # Install NestJS dependencies
   cd nestjs-backend && npm install && cd ..

   # Install FastAPI dependencies
   cd ingestion-service && pip install -r requirements.txt && cd ..

   # Run database migrations
   cd nestjs-backend && npx prisma migrate dev --name init && cd ..
   ```

3. **Start applications in separate terminals:**

   **Terminal 1 - NestJS Backend:**
   ```bash
   start_nestjs.bat
   ```
   Or manually:
   ```bash
   cd nestjs-backend && npm run start:dev
   ```

   **Terminal 2 - FastAPI Ingestion:**
   ```bash
   start_fastapi.bat
   ```
   Or manually:
   ```bash
   cd ingestion-service && python main.py
   ```

## Services

- **NestJS Backend**: http://localhost:8000 (run locally)
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
cd nestjs-backend
npm run test
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