# VoiceFlow AI Platform

A comprehensive multi-tenant AI agent platform with voice capabilities, advanced analytics, and enterprise-grade features. Built with modern web technologies for scalable, secure, and intelligent conversational AI.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Next.js       │    │   Express.js    │    │   FastAPI       │
│   Frontend      │◄──►│   Backend API   │◄──►│   Ingestion     │
│   (Port 3000)   │    │   (Port 3001)   │    │   Service       │
└─────────────────┘    └─────────────────┘    │   (Port 8001)   │
                                              └─────────────────┘
                                                     │
                                                     ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Redis       │    │     MinIO       │
│   Database      │    │     Cache       │    │   File Storage  │
│   (Port 5433)   │    │   (Port 6379)   │    │   (Port 9000)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                     │
                                                     ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    ChromaDB     │    │   External APIs │    │   Third-party   │
│  Vector Store   │    │   (OpenAI,      │    │  Integrations   │
│                 │    │    Groq, etc.)  │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Key Features

### Core AI Capabilities
- **Intelligent Agents** - Create custom AI agents for voice and chat interactions
- **RAG (Retrieval-Augmented Generation)** - Context-aware responses using vector search
- **Voice Processing** - Speech-to-text and text-to-speech with multiple providers
- **Multi-modal Conversations** - Support for voice, text, and file uploads

### Enterprise Features
- **Multi-tenant Architecture** - Complete isolation between organizations
- **Advanced Analytics** - Real-time dashboards and comprehensive reporting
- **Audit Logging** - Complete audit trails for compliance
- **Backup & Recovery** - Automated data backup with point-in-time restore
- **Billing & Usage Tracking** - Detailed cost analysis and subscription management
- **Team Collaboration** - User roles, permissions, and workspace management

### Developer Experience
- **Modern Tech Stack** - Next.js 15, TypeScript, Tailwind CSS
- **API Documentation** - Interactive Swagger docs with testing
- **Real-time Updates** - WebSocket connections for live features
- **Comprehensive Testing** - Unit, integration, and E2E test coverage
- **CI/CD Ready** - Docker containers and deployment scripts

## 📋 Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local development)
- PostgreSQL 15+
- Redis 7+
- MinIO or S3-compatible storage

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd VoiceFlow
```

### 2. Environment Configuration
```bash
# Copy environment files
cp voiceflow-ai-platform/.env.example voiceflow-ai-platform/.env.local
cp new_backend/.env.example new_backend/.env
cp document-ingestion/.env.example document-ingestion/.env
```

### 3. Launch with Docker
```bash
docker-compose up --build
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:3001/api-docs
- **MinIO Console**: http://localhost:9001
- **PostgreSQL**: localhost:5433
- **Redis**: localhost:6379

## 🛠️ Development Setup

### Frontend (Next.js)
```bash
cd voiceflow-ai-platform
npm install
npm run dev
```

### Backend API (Express.js)
```bash
cd new_backend
npm install
npm run dev
```

### Ingestion Service (FastAPI)
```bash
cd document-ingestion
pip install -r requirements.txt
python main.py
```

## 📊 Services & Ports

| Service | Technology | Port | Description |
|---------|------------|------|-------------|
| Frontend | Next.js | 3000 | User interface and dashboards |
| Backend API | Express.js | 3001 | Main REST API and business logic |
| Ingestion | FastAPI | 8001 | Document processing and embeddings |
| Database | PostgreSQL | 5433 | Primary data storage |
| Cache | Redis | 6379 | Session storage and caching |
| Storage | MinIO | 9000 | File storage (S3-compatible) |
| Vector DB | ChromaDB | - | Vector embeddings for RAG |

## 🔧 Configuration

### Environment Variables

#### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:3001
NEXT_PUBLIC_PUBLIC_BASE_URL=http://localhost:3000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_key
```

#### Backend (.env)
```env
DATABASE_URL=postgresql://user:pass@localhost:5433/voiceflow
REDIS_URL=redis://localhost:6379
JWT_SECRET=your_jwt_secret
OPENAI_API_KEY=your_openai_key
```

#### Ingestion Service (.env)
```env
CHROMA_HOST=localhost
POSTGRES_URL=postgresql://user:pass@localhost:5433/voiceflow
GROQ_API_KEY=your_groq_key
```

## 🔐 Authentication & Security

- **Clerk Integration** - User authentication and session management
- **JWT Tokens** - API authentication with role-based access
- **Tenant Isolation** - Complete data separation between organizations
- **PII Protection** - Automatic data sanitization and encryption
- **Rate Limiting** - Redis-based API rate limiting
- **Audit Logging** - Comprehensive activity tracking

## 📈 Monitoring & Analytics

- **Real-time Dashboards** - Usage metrics and performance monitoring
- **System Health Checks** - Automated monitoring and alerting
- **Error Tracking** - Sentry integration for error reporting
- **Performance Metrics** - Response times and throughput analysis
- **Cost Tracking** - API usage and billing analytics

## 🔗 API Documentation

### Main API (Express.js)
- **Swagger UI**: http://localhost:3001/api-docs
- **OpenAPI Spec**: http://localhost:3001/api-docs.json
- **Health Check**: http://localhost:3001/health

### Ingestion Service (FastAPI)
- **API Docs**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI**: http://localhost:8001/openapi.json

## 🧪 Testing

```bash
# Frontend tests
cd voiceflow-ai-platform && npm run test

# Backend tests
cd new_backend && npm run test

# Ingestion tests
cd document-ingestion && python -m pytest

# E2E tests
npm run test:e2e
```

## 🚀 Deployment

### Production Checklist
- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Database backups scheduled
- [ ] Monitoring and alerting set up
- [ ] CDN configured for static assets
- [ ] Load balancer configured

### Docker Deployment
```bash
# Build and deploy
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose logs -f
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📚 Documentation

- [API Reference](./docs/api/)
- [Deployment Guide](./docs/deployment/)
- [Contributing](./docs/contributing/)
- [Troubleshooting](./docs/troubleshooting/)
- [Architecture](./docs/architecture/)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs.voiceflow.ai](https://docs.voiceflow.ai)
- **Issues**: [GitHub Issues](https://github.com/your-org/voiceflow/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/voiceflow/discussions)

---

## 🔄 Recent Updates

- ✅ **Complete Dashboard Redesign** - Enterprise-grade UI with advanced features
- ✅ **Multi-tenant Architecture** - Secure tenant isolation and management
- ✅ **Real-time Features** - WebSocket connections and live updates
- ✅ **Advanced Analytics** - Comprehensive reporting and monitoring
- ✅ **Backup & Recovery** - Automated data protection and restore
- ✅ **Third-party Integrations** - Extensible integration framework
- ✅ **Audit & Compliance** - Complete audit trails and logging
- ✅ **Billing System** - Usage tracking and cost management
- ✅ **Team Collaboration** - User management and permissions
- ✅ **API Documentation** - Interactive docs with testing capabilities
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