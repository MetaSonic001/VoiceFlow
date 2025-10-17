# VoiceFlow Backend API

The main backend service for VoiceFlow, built with Express.js and TypeScript. Provides REST APIs for agent management, user authentication, analytics, and system administration.

## 🚀 Features

- **Agent Management** - CRUD operations for AI agents
- **User Authentication** - Clerk JWT integration
- **Multi-tenant Support** - Organization-based data isolation
- **Real-time Analytics** - Usage metrics and performance data
- **File Management** - Integration with MinIO for document storage
- **Audit Logging** - Comprehensive activity tracking
- **API Documentation** - Swagger/OpenAPI documentation
- **Rate Limiting** - Redis-based request throttling
- **Error Handling** - Structured error responses and logging

## 🏗️ Architecture

```
Express.js Backend (Port 3001)
├── Authentication (Clerk)
├── API Routes
│   ├── Agents (/api/agents)
│   ├── Users (/api/users)
│   ├── Analytics (/api/analytics)
│   ├── Audit (/api/audit)
│   ├── Backup (/api/backup)
│   └── Settings (/api/settings)
├── Middleware
│   ├── Authentication
│   ├── Rate Limiting
│   ├── Error Handling
│   └── Logging
├── Database (PostgreSQL)
├── Cache (Redis)
└── Storage (MinIO)
```

## 📋 Prerequisites

- Node.js 18+ and npm/bun
- PostgreSQL database
- Redis instance
- MinIO storage
- Clerk account for authentication

## 🚀 Quick Start

### 1. Install Dependencies
```bash
npm install
# or
bun install
```

### 2. Environment Configuration
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5433/voiceflow

# Redis
REDIS_URL=redis://localhost:6379

# Clerk Authentication
CLERK_SECRET_KEY=your_clerk_secret
CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key

# External APIs
OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key

# MinIO Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Application
PORT=3001
NODE_ENV=development
JWT_SECRET=your_jwt_secret
```

### 3. Database Setup
```bash
# Run database migrations
npm run db:migrate

# Seed initial data (optional)
npm run db:seed
```

### 4. Start Development Server
```bash
npm run dev
# or
bun run dev
```

The API will be available at http://localhost:3001

## 📊 API Documentation

### Swagger UI
Access interactive API documentation at: http://localhost:3001/api-docs

### OpenAPI Specification
Download the OpenAPI spec at: http://localhost:3001/api-docs.json

### Health Check
```bash
curl http://localhost:3001/health
```

## 🔧 Available Scripts

```bash
# Development
npm run dev          # Start development server with hot reload
npm run build        # Build for production
npm run start        # Start production server

# Database
npm run db:migrate   # Run database migrations
npm run db:generate  # Generate Prisma client
npm run db:seed      # Seed database with initial data
npm run db:studio    # Open Prisma Studio

# Testing
npm run test         # Run unit tests
npm run test:watch   # Run tests in watch mode
npm run test:cov     # Run tests with coverage

# Linting & Formatting
npm run lint         # Run ESLint
npm run format       # Format code with Prettier
```

## 🔐 Authentication

The API uses Clerk for authentication. All protected routes require a valid JWT token in the Authorization header:

```
Authorization: Bearer <clerk-jwt-token>
```

## 📡 API Endpoints

### Core Resources
- `GET/POST/PUT/DELETE /api/agents` - Agent management
- `GET/POST/PUT/DELETE /api/users` - User management
- `GET /api/analytics/*` - Analytics and reporting
- `GET /api/audit/*` - Audit logs and compliance
- `POST/GET /api/backup/*` - Backup and restore operations

### System Endpoints
- `GET /health` - Health check
- `GET /api-docs` - API documentation
- `GET /metrics` - Application metrics (Prometheus)

## 🧪 Testing

### Unit Tests
```bash
npm run test
```

### Integration Tests
```bash
npm run test:integration
```

### API Testing
```bash
# Using curl
curl -H "Authorization: Bearer <token>" http://localhost:3001/api/agents

# Using the Swagger UI at http://localhost:3001/api-docs
```

## 🚀 Deployment

### Docker
```bash
# Build the image
docker build -t voiceflow-backend .

# Run the container
docker run -p 3001:3001 voiceflow-backend
```

### Environment Variables for Production
```env
NODE_ENV=production
PORT=3001
DATABASE_URL=postgresql://user:pass@db-host:5432/voiceflow
REDIS_URL=redis://redis-host:6379
CLERK_SECRET_KEY=your_production_clerk_secret
```

## 📊 Monitoring

### Health Checks
- `/health` - Application health status
- `/metrics` - Prometheus metrics
- `/ready` - Readiness probe

### Logging
- Structured JSON logging
- Log levels: ERROR, WARN, INFO, DEBUG
- Request/response logging middleware

## 🔒 Security

- **Authentication**: Clerk JWT validation
- **Authorization**: Role-based access control
- **Rate Limiting**: Redis-based request throttling
- **Input Validation**: Zod schema validation
- **CORS**: Configured for allowed origins
- **Helmet**: Security headers
- **Data Sanitization**: PII protection and filtering

## 🤝 Contributing

1. Follow the existing code style
2. Add tests for new features
3. Update API documentation
4. Ensure all tests pass
5. Create a pull request with a clear description

## 📄 License

MIT License - see LICENSE file for details.
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