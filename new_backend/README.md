# VoiceFlow Backend

Backend services for the VoiceFlow AI platform. Contains the Express.js API server, FastAPI ingestion service, and Docker infrastructure.

## Services

| Service | Port | Technology | Description |
|---|---|---|---|
| Express Backend | 8000 | Node.js + TypeScript | Main API: auth, agents, RAG, voice, Twilio |
| Ingestion Service | 8001 | Python + FastAPI | Web scraping, document processing, embeddings |
| PostgreSQL | 5433 | Docker | Primary database |
| Redis | 6379 | Docker | Cache, rate limits, call sessions, job tracking |
| MinIO | 9000/9001 | Docker | S3-compatible file + TTS cache storage |
| ChromaDB | 8002 | Docker | Vector embeddings (per-tenant collections) |

## Quick Start

### 1. Start Infrastructure

```bash
cd new_backend
docker-compose up -d
```

### 2. Configure Environment

```bash
cp express-backend/.env.example express-backend/.env
cp ingestion-service/.env.example ingestion-service/.env
```

Fill in `CLERK_SECRET_KEY` and `CREDENTIALS_ENCRYPTION_KEY` in `express-backend/.env`.
`GROQ_API_KEY` is optional — each tenant can enter their own Groq key in Settings → Integrations.

Generate the encryption key:
```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

### 3. Start Express Backend

```bash
cd express-backend
npm install
npx prisma generate
npx prisma db push
npm run dev
```

### 4. Start Ingestion Service

```bash
cd ingestion-service
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 5. Verify Everything Works

```bash
# Health check
curl http://localhost:8000/health

# Ingestion service
curl http://localhost:8001/docs
```

## Express Backend Architecture

```
express-backend/src/
├── index.ts                     ← Server entry, route mounting, Socket.IO
├── config/env.ts                ← Joi env validation
├── routes/
│   ├── auth.ts                  ← Login, signup, Clerk sync
│   ├── agents.ts                ← Agent CRUD
│   ├── documents.ts             ← Document upload/list/delete
│   ├── ingestion.ts             ← Trigger & poll ingestion jobs
│   ├── onboarding.ts            ← 7-step wizard API
│   ├── rag.ts                   ← Direct RAG query
│   ├── runner.ts                ← Chat + audio endpoints
│   ├── twilio.ts                ← List provisioned numbers
│   ├── twilioVoice.ts           ← Twilio webhooks (incoming/respond/status)
│   ├── settings.ts              ← Twilio credentials CRUD
│   ├── tts.ts                   ← TTS proxy routes
│   ├── analytics.ts             ← Usage metrics (mocked)
│   ├── users.ts                 ← User management
│   └── admin.ts                 ← Admin endpoints
├── services/
│   ├── ragService.ts            ← Core RAG: retrieval + Groq LLM
│   ├── credentialsService.ts    ← AES-256-GCM encrypt/decrypt
│   ├── twilioClientService.ts   ← Per-tenant Twilio client cache
│   ├── twilioProvisioningService.ts ← Number search/purchase/release
│   ├── ttsService.ts            ← TTS call helper (2s timeout)
│   ├── callAnalysisService.ts   ← Post-call analysis
│   ├── promptAssemblyService.ts ← Template + config → system prompt
│   ├── minioService.ts          ← S3 file operations
│   └── voiceService.ts          ← Legacy ASR/TTS
├── middleware/
│   ├── clerkAuth.ts             ← JWT verify + user/tenant sync
│   ├── rateLimit.ts             ← Redis-based per-tenant limits
│   └── errorHandler.ts          ← Structured error responses
└── prisma/schema.prisma         ← Database schema (10 models)
```

## Key Features

### Per-Tenant Twilio Credentials
- Each tenant enters their own Twilio Account SID + Auth Token in Settings → Integrations
- Credentials encrypted with AES-256-GCM before storage (`credentialsService.ts`)
- Twilio clients cached per-tenant with 5-min TTL (`twilioClientService.ts`)
- Env vars (`TWILIO_ACCOUNT_SID/AUTH_TOKEN`) used only as dev/admin fallback
- Numbers provisioned on the tenant's own Twilio account

### TwiML Gather Voice Loop
- Incoming calls handled via pure HTTP webhooks, no WebSocket
- `/twilio/voice/incoming` → greeting + `<Gather input="speech">`
- `/twilio/voice/respond` → RAG query + TTS + another `<Gather>` (loop)
- `/twilio/voice/status` → call logging + session cleanup
- Redis stores call session (`twilio:session:{CallSid}`, TTL 1h)
- TTS via Chatterbox with 2-second timeout fallback to `<Say>`

### Real Phone Number Provisioning
- `provisionAgentNumber()` → search → purchase → configure webhooks → store in Agent
- `deprovisionAgentNumber()` → release number → clear DB fields
- `syncAgentWebhookUrl()` → update stale webhooks on server restart
- Deploy is gated: backend returns 400 if tenant has no Twilio credentials

## Docker Compose Services

```bash
docker-compose up -d          # Start all infrastructure
docker-compose ps             # Check status
docker-compose logs redis     # View logs for a service
docker-compose down           # Stop all
docker-compose down -v        # Stop + delete volumes (full reset)
```

## Database

```bash
cd express-backend
npx prisma generate           # Generate client from schema
npx prisma db push            # Push schema to database
npx prisma studio             # Visual DB browser (localhost:5555)
npx prisma migrate dev        # Create migration (for version control)
```

## Troubleshooting

| Problem | Fix |
|---|---|
| Port 5433 in use | `docker-compose down` then restart, or change port in docker-compose.yml |
| Prisma client out of date | `npx prisma generate` after schema changes |
| Redis connection refused | `docker-compose up -d redis` |
| Ingestion 404 on ChromaDB | Ensure `CHROMA_HOST=localhost` and `CHROMA_PORT=8002` |
| Twilio deploy fails 400 | Tenant needs to save Twilio credentials in Settings → Integrations |
| Encryption key error | Set `CREDENTIALS_ENCRYPTION_KEY` (64-char hex string) in `.env` |

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