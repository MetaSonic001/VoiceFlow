# VoiceFlow Multi-Tenant RAG Backend

A comprehensive multi-tenant RAG (Retrieval-Augmented Generation) backend system with voice capabilities, built with TypeScript/Express.js, FastAPI, and Next.js.

## Architecture

- **Frontend**: Next.js with Clerk authentication
- **Backend API**: Express.js with TypeScript
- **Ingestion Service**: FastAPI with Chroma vector database
- **Database**: PostgreSQL with Prisma ORM
- **Cache/Queue**: Redis
- **File Storage**: MinIO S3-compatible storage
- **Authentication**: Clerk JWT
- **LLM**: Groq API
- **Voice**: Vosk ASR + Mozilla/Coqui TTS

## Features

- ✅ Multi-tenant architecture with tenant isolation
- ✅ Clerk authentication integration
- ✅ MinIO S3 file storage with tenant isolation
- ✅ PII protection and data sanitization
- ✅ Rate limiting with Redis
- ✅ Comprehensive error handling and logging
- ✅ Swagger API documentation
- ✅ Voice transcription (Whisper API)
- ✅ Text-to-speech (Mozilla TTS)
- ✅ Real-time WebSocket communication
- ✅ Document ingestion and processing
- ✅ RAG with Chroma vector search

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your credentials
3. Run `docker-compose up --build`

## Services

- Express Backend: http://localhost:8000
- API Documentation: http://localhost:8000/api-docs
- Ingestion Service: http://localhost:8001
- MinIO Console: http://localhost:9001
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Next.js Frontend: http://localhost:3000

## API Endpoints

### Authentication
All endpoints require Clerk JWT authentication.

### Agents
- `GET /api/agents` - List agents
- `POST /api/agents` - Create agent
- `GET /api/agents/:id` - Get agent details
- `PUT /api/agents/:id` - Update agent
- `DELETE /api/agents/:id` - Delete agent

### Documents
- `GET /api/documents` - List documents
- `POST /api/documents/upload` - Upload document file
- `GET /api/documents/:id` - Get document
- `DELETE /api/documents/:id` - Delete document

### Voice/Chat
- `POST /api/runner/chat` - Chat with agent
- `GET /api/runner/agent/:id` - Get agent info

### Ingestion
- `POST /api/ingestion` - Start document ingestion

## Prerequisites

- Node.js 18+
- Python 3.8+
- PostgreSQL
- Redis
- MinIO (or compatible S3 service)
- Clerk account
- Groq API key
- OpenAI API key (for Whisper)

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd voiceflow-backend
```

### 2. Environment Configuration

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:
- Database connection string
- Clerk keys
- API keys (Groq, OpenAI)
- MinIO/S3 credentials
- Redis connection

### 3. Database Setup

```bash
# Install dependencies
npm install

# Generate Prisma client
npx prisma generate

# Run database migrations
npx prisma db push

# Seed initial data
npm run db:seed
```

### 4. Start Services

#### Option A: Docker Compose (Recommended)

```bash
docker-compose up -d
```

#### Option B: Manual Setup

Start each service individually:

```bash
# Start PostgreSQL
# Start Redis
# Start MinIO

# Start Express backend
npm run dev

# Start FastAPI ingestion service
cd ../document-ingestion
pip install -r requirements.txt
python main.py

# Start Next.js frontend
cd ../voiceflow-ai-platform
npm install
npm run dev
```

### 5. Access the Application

- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8000/api-docs
- **MinIO Console**: http://localhost:9001

## Development

### Project Structure

```
├── express-backend/          # Main API server
│   ├── src/
│   │   ├── middleware/       # Auth, rate limiting, error handling
│   │   ├── routes/          # API route handlers
│   │   ├── services/        # Business logic (MinIO, voice, RAG)
│   │   ├── utils/           # Helpers (PII, swagger)
│   │   └── index.ts         # Server entry point
│   ├── prisma/              # Database schema and seeds
│   └── docker-compose.yml
├── document-ingestion/       # FastAPI ingestion service
├── voiceflow-ai-platform/    # Next.js frontend
└── docker-compose.yml        # Full system orchestration
```

### Key Components

#### Multi-Tenant Architecture
- Tenant isolation in all database queries
- Separate file storage per tenant in MinIO
- Rate limiting per tenant
- Clerk user synchronization

#### Voice Processing
- ASR: OpenAI Whisper API integration
- TTS: Mozilla TTS with espeak-ng fallback
- Real-time audio processing via WebSocket

#### Security
- JWT authentication via Clerk
- PII detection and redaction
- Rate limiting and request validation
- CORS and helmet security headers

### Testing

```bash
# Backend tests
npm test

# Ingestion service tests
cd ../document-ingestion
pytest

# Frontend tests
cd ../voiceflow-ai-platform
npm test
```

### Deployment

#### Production Checklist
- [ ] Set `NODE_ENV=production`
- [ ] Configure production database
- [ ] Set up Redis cluster
- [ ] Configure MinIO/S3 bucket
- [ ] Set up monitoring (Sentry, etc.)
- [ ] Configure load balancer
- [ ] Set up SSL certificates

#### Docker Deployment

```bash
# Build all services
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Common Issues

1. **Clerk Authentication Issues**
   - Verify `CLERK_SECRET_KEY` in environment
   - Check Clerk application configuration

2. **Database Connection**
   - Ensure PostgreSQL is running
   - Verify `DATABASE_URL` format

3. **MinIO Connection**
   - Check MinIO credentials
   - Verify bucket creation

4. **Voice Services**
   - Ensure OpenAI API key for Whisper
   - Check espeak-ng installation for TTS fallback

### Logs

Check logs for each service:
```bash
# Express backend
docker logs voiceflow-backend

# FastAPI ingestion
docker logs document-ingestion

# Next.js frontend
docker logs voiceflow-frontend
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Deployment

Use the docker-compose.yml for production deployment. Make sure to:
- Set strong passwords
- Configure proper networking
- Set up SSL certificates
- Configure backups for databases