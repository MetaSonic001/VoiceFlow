# VoiceFlow AI Platform

A multi-tenant SaaS platform for building, deploying, and managing AI-powered voice and chat agents. Businesses onboard through a guided wizard, upload their knowledge base, and receive a domain-specific AI agent that answers customer queries over phone (Twilio) or a web chat interface — using Retrieval-Augmented Generation (RAG) over their own documents.

> **Status:** The core platform is functional end-to-end. RAG pipeline, onboarding, per-tenant Twilio provisioning, TwiML voice loop, and self-hosted TTS all work. Several enterprise dashboard sections (analytics, billing) still return mock data. See the [Implementation Status](#implementation-status) section for the full picture.


---

## Table of Contents

1. [What This Project Does](#what-this-project-does)
2. [System Architecture](#system-architecture)
3. [Repository Structure](#repository-structure)
4. [Tech Stack](#tech-stack)
5. [How It Works — End to End](#how-it-works--end-to-end)
6. [Running the Project](#running-the-project)
7. [Environment Variables](#environment-variables)
8. [Services & Ports](#services--ports)
9. [API Reference](#api-reference)
10. [Implementation Status](#implementation-status)
11. [Data Models](#data-models)
12. [Patent — Multi-Tenant RAG Voice Agent System](#patent--multi-tenant-rag-voice-agent-system)

---

## What This Project Does

VoiceFlow lets any business create an AI agent tailored to their domain without writing code:

1. **Sign up** → authenticated via Clerk
2. **Onboarding wizard** (7 steps) → configure company profile, agent persona, knowledge base, voice settings, deployment channels
3. **Documents are ingested** → scraped from URLs or uploaded as files → chunked, embedded, stored in a per-tenant vector store in ChromaDB
4. **Agent is live** → receives questions via web chat or phone call → retrieves relevant chunks from the tenant's knowledge store → generates a contextual answer via Groq LLM → responds in voice or text

The primary market is Indian SMBs. Every tenant and agent is logically isolated — one tenant cannot query another's documents.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACES                             │
│                                                                     │
│   ┌─────────────────────┐         ┌──────────────────────────────┐  │
│   │   Next.js Frontend  │         │    Twilio Phone / WebSocket  │  │
│   │   (Port 3000)       │         │    Voice Channel             │  │
│   │                     │         │                              │  │
│   │   • Landing page    │         │   • Inbound calls            │  │
│   │   • Onboarding      │         │   • Media stream (WebSocket) │  │
│   │   • Agent dashboard │         │   • TwiML webhooks           │  │
│   │   • Analytics       │         └──────────────┬───────────────┘  │
│   │   • Admin panel     │                        │                  │
│   └──────────┬──────────┘                        │                  │
│              │ HTTP/REST via Next.js API proxy    │                  │
└──────────────┼────────────────────────────────────┼─────────────────┘
               │                                    │
               ▼                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    EXPRESS.JS BACKEND  (Port 8000)                  │
│                                                                     │
│   ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│   │  Clerk Auth  │  │ Rate Limiter │  │    Route Handlers      │   │
│   │  Middleware  │  │  (Redis)     │  │                        │   │
│   │              │  │              │  │  /auth       /agents   │   │
│   │  JWT verify  │  │  Per-tenant  │  │  /onboarding /rag      │   │
│   │  User sync   │  │  limits      │  │  /runner     /twilio   │   │
│   └──────────────┘  └──────────────┘  │  /analytics  /admin    │   │
│                                       └───────────┬────────────┘   │
│                                                   │                 │
│   ┌───────────────────────────────────────────────▼──────────────┐  │
│   │                   CORE SERVICES                              │  │
│   │                                                              │  │
│   │   ┌─────────────────────┐   ┌──────────────────────────┐    │  │
│   │   │   RAG Service       │   │   Twilio Voice Svc       │    │  │
│   │   │                     │   │                          │    │  │
│   │   │  • Hybrid retrieval │   │  • TwiML Gather loop     │    │  │
│   │   │  • BM25 scoring     │   │  • Per-tenant creds      │    │  │
│   │   │  • Context condense │   │  • Webhook validation    │    │  │
│   │   │  • Groq LLM call    │   │  • Redis call sessions   │    │  │
│   │   │  • Conv. history    │   └──────────────────────────┘    │  │
│   │   └─────────────────────┘                                   │  │
│   │                                                              │  │
│   │   ┌─────────────────────┐   ┌──────────────────────────┐    │  │
│   │   │   Credentials Svc   │   │   MinIO Service          │    │  │
│   │   │                     │   │                          │    │  │
│   │   │  • AES-256-GCM      │   │  • Per-tenant buckets    │    │  │
│   │   │  • Per-tenant keys  │   │  • File upload/download  │    │  │
│   │   │  • Client cache     │   │  • S3-compatible API     │    │  │
│   │   └─────────────────────┘   └──────────────────────────┘    │  │
│   └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
               │                           │
               ▼                           ▼
┌──────────────────────────┐  ┌────────────────────────────────────┐
│  FASTAPI INGESTION SVC   │  │       DATA STORES                  │
│  (Port 8001)             │  │                                    │
│                          │  │  ┌────────────┐  ┌─────────────┐  │
│  • URL scraping          │  │  │ PostgreSQL │  │   ChromaDB  │  │
│    - Crawl4AI (primary)  │  │  │ (Port 5433)│  │  (Port 8002)│  │
│    - Trafilatura         │  │  │            │  │             │  │
│    - Playwright          │  │  │ Tenants    │  │ Per-tenant  │  │
│    - Scrapy (fallback)   │  │  │ Users      │  │ collections │  │
│  • File processing       │  │  │ Agents     │  │             │  │
│    - PDF + OCR           │  │  │ Documents  │  │ tenant_{id} │  │
│    - DOCX / DOC          │  │  │ AgentConf  │  │ + agentId   │  │
│    - PPTX / XLSX         │  │  │ OnboardPrg │  │ metadata    │  │
│    - Images (DocTR OCR)  │  │  └────────────┘  └─────────────┘  │
│  • Embedding generation  │  │                                    │
│    (all-MiniLM-L6-v2)   │  │  ┌────────────┐  ┌─────────────┐  │
│  • ChromaDB storage      │  │  │   Redis    │  │    MinIO    │  │
│  • Progress tracking     │  │  │ (Port 6379)│  │ (Port 9000) │  │
│    via Redis             │  │  │            │  │             │  │
│                          │  │  │ Conv hist  │  │ Per-tenant  │  │
└──────────────────────────┘  │  │ Rate limit │  │ file store  │  │
                              │  │ Call sesh  │  │ TTS cache   │  │
                              │  │ Job status │  │ (S3-compat) │  │
                              │  └────────────┘  └─────────────┘  │
                              └────────────────────────────────────┘
                                         ▲
┌──────────────────────────┐             │
│  CHATTERBOX TTS SERVICE  │─────────────┘
│  (Port 8003)             │
│                          │
│  • Chatterbox Turbo 350M │
│  • 5 preset voices       │
│  • Voice cloning         │
│  • MinIO TTS cache       │
│  • SHA-256 dedup         │
└──────────────────────────┘
```

---

## Repository Structure

```
VoiceFlow/
│
├── voiceflow-ai-platform (1)/     ← ACTIVE: Next.js 15 frontend
│   ├── app/
│   │   ├── page.tsx               ← Landing page
│   │   ├── layout.tsx             ← Root layout with ClerkProvider
│   │   ├── onboarding/            ← 7-step onboarding wizard
│   │   ├── dashboard/             ← Agent management dashboard
│   │   │   ├── analytics/
│   │   │   ├── billing/
│   │   │   ├── audit/
│   │   │   ├── knowledge/
│   │   │   ├── settings/
│   │   │   └── ...
│   │   ├── admin/pipelines/       ← Admin panel
│   │   ├── voice-agent/           ← Standalone voice interface
│   │   └── api/                   ← Next.js API routes (proxy layer)
│   │       ├── auth/clerk_sync/   ← Clerk → backend user sync
│   │       ├── agents/            ← Proxy to Express /api/agents
│   │       ├── onboarding/        ← Proxy to Express /onboarding
│   │       └── runner/[...path]/  ← Proxy to Express /api/runner
│   ├── components/
│   │   ├── agent-dashboard.tsx
│   │   ├── chat-interface.tsx
│   │   ├── voice-agent-interface.tsx
│   │   ├── onboarding-flow.tsx
│   │   ├── ClerkSync.tsx
│   │   ├── onboarding/            ← Per-step wizard components
│   │   └── dashboard/             ← Dashboard sub-components
│   ├── lib/
│   │   ├── api-client.ts          ← Unified API client class
│   │   ├── prisma.ts              ← Prisma client (frontend)
│   │   ├── tenant-utils.ts        ← Tenant context helpers
│   │   └── constants.ts
│   └── prisma/schema.prisma       ← Frontend DB schema
│
├── new_backend/                   ← ACTIVE: Backend services
│   ├── docker-compose.yml         ← PostgreSQL, Redis, MinIO, ChromaDB
│   ├── express-backend/           ← ACTIVE: Main Express API
│   │   ├── src/
│   │   │   ├── index.ts           ← Server entry + Socket.IO setup
│   │   │   ├── routes/
│   │   │   │   ├── agents.ts
│   │   │   │   ├── analytics.ts   ← (currently mocked)
│   │   │   │   ├── auth.ts
│   │   │   │   ├── documents.ts
│   │   │   │   ├── ingestion.ts
│   │   │   │   ├── onboarding.ts
│   │   │   │   ├── rag.ts
│   │   │   │   ├── runner.ts      ← Chat + audio endpoints
│   │   │   │   ├── twilio.ts
│   │   │   │   ├── users.ts
│   │   │   │   └── admin.ts
│   │   │   ├── services/
│   │   │   │   ├── ragService.ts  ← Core RAG pipeline
│   │   │   │   ├── voiceService.ts← ASR + TTS
│   │   │   │   ├── twilioMediaService.ts
│   │   │   │   └── minioService.ts
│   │   │   └── middleware/
│   │   │       ├── clerkAuth.ts   ← JWT verify + user sync
│   │   │       ├── rateLimit.ts   ← Redis-based per-tenant limits
│   │   │       └── errorHandler.ts
│   │   └── prisma/schema.prisma   ← Backend DB schema
│   └── ingestion-service/         ← ACTIVE: FastAPI ingestion
│       └── main.py                ← Scraping + embedding + ChromaDB
│
├── tts-service/                   ← ACTIVE: Chatterbox TTS microservice
│   ├── main.py                    ← FastAPI TTS server (port 8003)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
│
├── not-required/                  ← LEGACY: archived prior iterations
│   ├── agent-workflow/            ← Old Flask+Groq RAG app
│   ├── backend/                   ← Old FastAPI+CrewAI backend
│   ├── FastAPI/                   ← Old SQLite-based FastAPI
│   ├── document-ingestion/        ← Old modular ingestion service
│   ├── rag/                       ← Old flask RAG prototype
│   ├── nestjs-backend/            ← NestJS experiment
│   ├── n8n/                       ← n8n workflow experiments
│   └── agent_runner_service/      ← Old agent runner
│
└── tools/db_visualizer/           ← Development utility
```

> Everything inside `not-required/` is archived. It represents the evolution of the system across multiple iterations and should not be run. The active codebase is `voiceflow-ai-platform (1)/` and `new_backend/`.

---

## Tech Stack

### Frontend
| Layer | Technology |
|---|---|
| Framework | Next.js 15 (App Router), React 19 |
| Language | TypeScript |
| Styling | Tailwind CSS v4, shadcn/ui (Radix UI primitives) |
| Animation | Framer Motion |
| Charts | Recharts |
| Auth | Clerk (`@clerk/nextjs`) |
| Forms | react-hook-form + Zod |
| Database (frontend) | Prisma + PostgreSQL |

### Backend (Express)
| Layer | Technology |
|---|---|
| Runtime | Node.js 18+ |
| Framework | Express.js |
| Language | TypeScript |
| ORM | Prisma |
| Auth | Clerk SDK (`@clerk/clerk-sdk-node`) |
| Validation | Joi |
| Real-time | Socket.IO |
| File uploads | Multer |

### Backend (Ingestion)
| Layer | Technology |
|---|---|
| Framework | FastAPI (Python) |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) |
| Scraping | Crawl4AI, Trafilatura, Playwright, Scrapy |
| OCR | DocTR, Tesseract, pdfminer |
| Chunking | LangChain `RecursiveCharacterTextSplitter` |
| Documents | `python-docx`, `python-pptx`, `openpyxl`, Pillow |

### Infrastructure
| Component | Technology |
|---|---|
| Primary DB | PostgreSQL 15 |
| Vector Store | ChromaDB |
| Cache / Queue | Redis 7 |
| File Storage | MinIO (S3-compatible) |
| LLM | Groq API (`llama` / `mixtral` family) |
| TTS | Chatterbox Turbo 350M (self-hosted, MIT license) |
| Telephony | Twilio (TwiML Gather loop, per-tenant credentials) |
| Credential Encryption | AES-256-GCM via Node.js crypto |
| Auth Provider | Clerk |

---

## How It Works — End to End

### Onboarding Flow (New Tenant)

```
User signs up via Clerk
        │
        ▼
ClerkSync component fires (client-side)
        │
        ├─► POST /api/auth/clerk_sync  (Next.js API route)
        │       │ Verifies Clerk session server-side
        │       ├─► POST /auth/clerk-sync (Express)
        │       │       │ Creates/finds User + Tenant in PostgreSQL
        │       │       └─► Returns { access_token, user, needs_onboarding }
        │       └─► Redirects to /onboarding or /dashboard
        │
        ▼
7-Step Onboarding Wizard
  Step 1: Company Profile    → POST /onboarding/company
  Step 2: Agent Creation     → POST /onboarding/agent     → creates Agent row
  Step 3: Knowledge Upload   → POST /onboarding/knowledge → triggers ingestion
  Step 4: Voice & Personality→ POST /onboarding/voice     → stores voice config
  Step 5: Channel Setup      → POST /onboarding/channels  → Twilio setup
  Step 6: Testing Sandbox    → UI tests chat/voice in real-time
  Step 7: Go Live / Deploy   → POST /onboarding/deploy    → assigns phone number
```

### Document Ingestion Flow

```
Tenant uploads URL or file
        │
        ▼
Express /api/ingestion/start
        │ Creates Document rows in PostgreSQL (status: "pending")
        │ Calls FastAPI /ingest
        │
        ▼
FastAPI Ingestion Service (background task)
        │
        ├── For URLs:
        │   ├── Try Crawl4AI (primary, AI-driven)
        │   ├── Try Trafilatura (article extraction)
        │   ├── Try Playwright (dynamic/SPA pages)
        │   └── Try Scrapy (fallback)
        │
        └── For S3 files:
            ├── PDF  → pdfminer text extraction → DocTR OCR (if scanned)
            ├── DOCX → python-docx paragraph/table extraction
            ├── PPTX → python-pptx slide text extraction
            ├── XLSX → openpyxl/pandas table extraction
            └── Images → Tesseract/DocTR OCR
        │
        ▼
LangChain RecursiveCharacterTextSplitter
  (chunk_size=1000, chunk_overlap=200)
        │
        ▼
SentenceTransformer.encode() → float32 embeddings
        │
        ▼
ChromaDB collection: "tenant_{tenantId}"
  Metadata per chunk: { agentId, source, chunk_index, content_type }
        │
        ▼
Redis: job:{job_id} = "completed"  (progress tracking)
```

### Query / Chat Flow

```
User sends message in ChatInterface
        │
        ▼
fetch('/api/runner/chat', { message, agentId, sessionId })
        │
        ▼
Next.js proxy route → adds x-tenant-id, x-user-id headers
        │
        ▼
Express /api/runner/chat
  │ Clerk auth middleware verifies JWT
  │ Loads agent from PostgreSQL
        │
        ▼
ragService.processQuery(tenantId, agentId, query, agent, sessionId)
        │
        ├─ 1. Load conversation history from Redis
        │      key: "conversation:{tenantId}:{agentId}:{sessionId}"
        │
        ├─ 2. Hybrid document retrieval
        │      ├── semanticSearch → ChromaDB /query
        │      │   (vector similarity, agentId filter, top ~7 chunks)
        │      └── keywordSearch → ChromaDB /get + BM25 scoring
        │          (client-side BM25 over fetched docs, top ~3 chunks)
        │
        ├─ 3. Combine, deduplicate, re-rank by relevance score
        │      (exact phrase match + word match + proximity bonus)
        │
        ├─ 4. condenseContext() — fit chunks into token budget
        │      (50% of tokenLimit reserved for context)
        │
        ├─ 5. generateResponse() → POST Groq API /chat/completions
        │      model: grok-beta, max_tokens: ~20% of tokenLimit
        │      System: agent.systemPrompt || "You are a helpful assistant."
        │      User:   "Context:\n{chunks}\n\n{query}"
        │
        └─ 6. Store updated conversation in Redis (TTL: 24h, max 20 turns)
        │
        ▼
{ response, agentId, sessionId }
```

### Voice Call Flow (Twilio — TwiML Gather Loop)

```
Caller dials Twilio number provisioned on tenant's account
        │
        ▼
Twilio → POST /twilio/voice/incoming (Express webhook)
        │
        ├─ 1. Look up agent by phoneNumber (req.body.To)
        │     → prisma.agent.findFirst({ phoneNumber: toNumber })
        │     → load tenant + agentConfiguration
        │
        ├─ 2. Validate Twilio webhook signature
        │     → getTwilioAuthTokenForValidation(tenantId)
        │     → uses per-tenant decrypted auth token
        │
        ├─ 3. Create Redis session
        │     → key: twilio:session:{CallSid}
        │     → stores: { agentId, tenantId, callSid }
        │     → TTL: 1 hour
        │
        ├─ 4. Generate greeting via TTS (if voiceId configured)
        │     → ttsService.synthesiseForCall(greeting, voiceId)
        │     → 2s timeout → falls back to <Say> on failure
        │
        └─ 5. Return TwiML:
              <Response>
                <Play>{presigned wav url}</Play>  ← or <Say> fallback
                <Gather input="speech" action="/twilio/voice/respond">
                  <Say>...</Say>
                </Gather>
              </Response>
        │
        ▼  (caller speaks)
        │
Twilio → POST /twilio/voice/respond
        │
        ├─ 1. Load session from Redis (CallSid)
        ├─ 2. Extract speech: req.body.SpeechResult
        ├─ 3. ragService.processQuery(tenantId, agentId, speech)
        ├─ 4. TTS: synthesiseForCall(aiResponse, voiceId)
        └─ 5. Return TwiML with <Play> + another <Gather>
              → loop continues until caller hangs up
        │
        ▼  (on hangup)
        │
Twilio → POST /twilio/voice/status
        │
        └─ Log call duration, create CallLog record, clean Redis session
```

---

## Running the Project

### Prerequisites

- Docker Desktop (for infrastructure services)
- Node.js 18+
- Python 3.10+
- `npm` or `pnpm`
- Clerk account → API keys ([dashboard.clerk.com](https://dashboard.clerk.com))
- Groq API key ([console.groq.com](https://console.groq.com))
- (Optional) Twilio account for phone calls — each tenant brings their own

### Step 1 — Start Infrastructure

```bash
cd new_backend
docker-compose up -d
```

This starts PostgreSQL (5433), Redis (6379), MinIO (9000/9001), ChromaDB (8002), and the TTS service (8003).

> **Note:** The TTS service requires an NVIDIA GPU for CUDA inference. If running CPU-only, set `DEVICE=cpu` in `tts-service/.env` (slower but works).

### Step 2 — Generate Encryption Key

```bash
# Run once — store the output in your .env as CREDENTIALS_ENCRYPTION_KEY
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

> **Warning:** Never change this key after tenants have saved Twilio credentials — changing it makes all stored credentials unreadable.

### Step 3 — Configure Environment Files

Each service has a `.env.example` template. Copy and fill in real values:

```bash
# Express Backend
cp new_backend/express-backend/.env.example new_backend/express-backend/.env

# Ingestion Service
cp new_backend/ingestion-service/.env.example new_backend/ingestion-service/.env

# TTS Service
cp tts-service/.env.example tts-service/.env

# Frontend
cp "voiceflow-ai-platform (1)/.env.example" "voiceflow-ai-platform (1)/.env.local"
```

Required values to fill in:
- `CLERK_SECRET_KEY` and `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` from Clerk dashboard
- `GROQ_API_KEY` from Groq console
- `CREDENTIALS_ENCRYPTION_KEY` from Step 2
- `DATABASE_URL` (default matches docker-compose: `postgresql://vf_admin:vf_secure_2025!@localhost:5433/voiceflow_prod`)

### Step 4 — Start Express Backend

```bash
cd new_backend/express-backend
npm install
npx prisma generate
npx prisma db push      # creates/updates tables
npm run dev              # starts on port 8000
```

### Step 5 — Start Ingestion Service

```bash
cd new_backend/ingestion-service
pip install -r requirements.txt
playwright install chromium   # required for scraping
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Step 6 — Start Frontend

```bash
cd "voiceflow-ai-platform (1)"
npm install
npx prisma generate
npm run dev              # starts on port 3000
```

### Step 7 — Access the Application

| Interface | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Express API | http://localhost:8000 |
| Express Health | http://localhost:8000/health |
| FastAPI Ingestion Docs | http://localhost:8001/docs |
| TTS Service Health | http://localhost:8003/health |
| MinIO Console | http://localhost:9001 (minioadmin / minioadmin) |
| ChromaDB | http://localhost:8002 |

### (Optional) Voice Calls via Twilio

1. **Expose your local backend publicly:**
```bash
ngrok http 8000
```

2. **Set the webhook URL in your backend `.env`:**
```env
TWILIO_WEBHOOK_BASE_URL=https://your-subdomain.ngrok-free.app
```

3. **Each tenant enters their own Twilio credentials** in the Settings → Integrations page after signing up. The platform uses their credentials to provision numbers on their Twilio account.

4. **On deploy**, the onboarding wizard calls the Twilio API to search for an available local number, purchase it, and configure the voice webhooks automatically. No manual Twilio console setup needed.

---

## Environment Variables

### Express Backend (`new_backend/express-backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | **Yes** | — | PostgreSQL connection string |
| `REDIS_HOST` | **Yes** | `localhost` | Redis host |
| `REDIS_PORT` | No | `6379` | Redis port |
| `CLERK_SECRET_KEY` | **Yes** | — | Clerk secret for JWT verification |
| `GROQ_API_KEY` | **Yes** | — | LLM inference via Groq |
| `CREDENTIALS_ENCRYPTION_KEY` | No* | — | 64-char hex string for AES-256-GCM encryption of tenant Twilio creds. Required if tenants save Twilio credentials. |
| `CHROMA_HOST` | No | `localhost` | ChromaDB host |
| `CHROMA_PORT` | No | `8002` | ChromaDB port |
| `CHROMA_URL` | No | `http://localhost:8002` | ChromaDB full URL (used by ragService) |
| `MINIO_ENDPOINT` | No | `localhost` | MinIO host |
| `MINIO_PORT` | No | `9000` | MinIO port |
| `MINIO_ACCESS_KEY` | No | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | No | `minioadmin` | MinIO secret key |
| `TWILIO_ACCOUNT_SID` | No | — | Fallback Twilio SID (dev/admin only) |
| `TWILIO_AUTH_TOKEN` | No | — | Fallback Twilio token (dev/admin only) |
| `TWILIO_WEBHOOK_BASE_URL` | No | — | Public URL for Twilio webhooks (e.g. ngrok URL) |
| `TTS_SERVICE_URL` | No | `http://localhost:8003` | Chatterbox TTS service URL |
| `FASTAPI_URL` | No | `http://localhost:8001` | Ingestion service URL |
| `PORT` | No | `8000` | Express server port |
| `NODE_ENV` | No | `development` | Environment mode |
| `JWT_SECRET` | No | `dev-secret` | JWT signing secret (change in production) |

### Ingestion Service (`new_backend/ingestion-service/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `REDIS_HOST` | No | `localhost` | Redis host for job tracking |
| `REDIS_PORT` | No | `6379` | Redis port |
| `CHROMA_HOST` | No | `localhost` | ChromaDB host |
| `CHROMA_PORT` | No | `8002` | ChromaDB port |
| `MINIO_ENDPOINT` | No | `http://localhost:9000` | MinIO endpoint |
| `MINIO_ACCESS_KEY` | No | — | MinIO access key |
| `MINIO_SECRET_KEY` | No | — | MinIO secret key |
| `EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | Sentence transformer model |
| `CHUNK_SIZE` | No | `1000` | Text chunk size |
| `CHUNK_OVERLAP` | No | `200` | Chunk overlap |

### TTS Service (`tts-service/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `MINIO_ENDPOINT` | No | `localhost:9000` | MinIO endpoint for TTS cache |
| `MINIO_ACCESS_KEY` | No | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | No | `minioadmin` | MinIO secret key |
| `MINIO_BUCKET` | No | `voiceflow-tts` | MinIO bucket for TTS audio |
| `DEVICE` | No | `cuda` | PyTorch device (`cuda` or `cpu`) |

### Frontend (`voiceflow-ai-platform (1)/.env.local`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | **Yes** | — | Clerk publishable key |
| `CLERK_SECRET_KEY` | **Yes** | — | Clerk secret key |
| `DATABASE_URL` | **Yes** | — | PostgreSQL connection string |
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | Public backend URL for client-side calls |
| `BACKEND_URL` | No | `http://localhost:8000` | Server-side backend URL for API proxies |
| `NEW_BACKEND_URL` | No | `http://localhost:8000` | Alias for backend URL |
| `BACKEND_API_KEY` | No | — | Server-to-server auth key |
| `NEXT_PUBLIC_WS_URL` | No | `ws://localhost:8000` | WebSocket URL |

---

## Services & Ports

| Service | Technology | Port | Role |
|---|---|---|---|
| Frontend | Next.js 15 | 3000 | UI, dashboard, onboarding |
| Express Backend | Node.js | 8000 | Auth, agents, RAG, voice, API |
| Ingestion Service | FastAPI | 8001 | Scraping, embedding, ChromaDB writes |
| TTS Service | FastAPI + Chatterbox | 8003 | Self-hosted text-to-speech, voice cloning |
| PostgreSQL | Docker | 5433 | Primary relational data |
| Redis | Docker | 6379 | Conversation cache, rate limits, call sessions |
| MinIO | Docker | 9000/9001 | File storage, TTS cache (S3-compatible) |
| ChromaDB | Docker | 8002 | Vector embeddings (per-tenant collections) |

---

## API Reference

All backend endpoints require a Clerk JWT token unless noted.

**Authentication header:**
```
Authorization: Bearer <clerk_jwt_token>
x-tenant-id: <tenant_uuid>
```

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/login` | Email/password login |
| POST | `/auth/signup` | New account signup |
| POST | `/auth/clerk-sync` | Sync Clerk user to local DB |
| POST | `/auth/logout` | Logout |

### Agents
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/agents` | List agents for authenticated tenant |
| POST | `/api/agents` | Create new agent |
| GET | `/api/agents/:id` | Get agent with documents |
| PUT | `/api/agents/:id` | Update agent configuration |
| DELETE | `/api/agents/:id` | Delete agent and documents |

### Documents
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/documents` | List documents for agent |
| POST | `/api/documents/upload` | Upload file to MinIO + trigger ingestion |
| DELETE | `/api/documents/:id` | Remove document and vectors |

### RAG / Chat
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/rag/query` | Direct RAG query with agentId |
| GET | `/api/rag/conversation/:sessionId` | Get conversation history |
| POST | `/api/runner/chat` | Chat endpoint (used by frontend) |
| POST | `/api/runner/audio` | Voice audio upload for transcription + RAG |

### Ingestion
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/ingestion/start` | Trigger URL/S3 ingestion job |
| GET | `/api/ingestion/status/:jobId` | Poll job progress (0-100%) |

### Onboarding
| Method | Endpoint | Description |
|---|---|---|
| POST | `/onboarding/company` | Save company profile |
| POST | `/onboarding/agent` | Create initial agent |
| POST | `/onboarding/knowledge` | Upload knowledge (proxied to FastAPI) |
| POST | `/onboarding/voice` | Save voice config |
| POST | `/onboarding/channels` | Save channel config |
| POST | `/onboarding/agent-config` | Save full agent configuration |
| POST | `/onboarding/deploy` | Deploy agent to phone number |
| GET/POST/DELETE | `/onboarding/progress` | Resume / save / clear onboarding state |

### Twilio / Voice
| Method | Endpoint | Description |
|---|---|---|
| GET | `/twilio/numbers` | List provisioned phone numbers for tenant |
| POST | `/twilio/voice/incoming` | Inbound call webhook (TwiML Gather) — no auth |
| POST | `/twilio/voice/respond` | Conversation loop webhook (TwiML) — no auth |
| POST | `/twilio/voice/status` | Call status callback — no auth |

### Settings
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/settings/twilio` | Save & verify Twilio credentials (encrypted) |
| GET | `/api/settings/twilio` | Get credential status (never returns auth token) |
| DELETE | `/api/settings/twilio` | Remove Twilio credentials |

### TTS (Text-to-Speech)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/tts/preset-voices` | List 5 preset voices with sample audio |
| POST | `/api/tts/synthesise` | Generate speech audio for text + voiceId |
| POST | `/api/tts/clone-voice` | Upload audio to create a cloned voice profile |

### Analytics (currently mocked)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/analytics/overview` | Usage metrics overview |
| GET | `/analytics/calls` | Call log history |
| GET | `/analytics/performance` | Response time, success rate charts |
| GET | `/analytics/agents/comparison` | Side-by-side agent stats |

### Health
```
GET /health  →  { status: "ok", timestamp: "..." }
```

---

## Implementation Status

A complete breakdown of what works versus what is a stub or mock.

### Working

| Component | Notes |
|---|---|
| Clerk authentication | JWT verify, user sync via ClerkSync component |
| 7-step onboarding wizard | All 7 steps persist to backend, including deploy |
| URL scraping + ingestion | 4-strategy cascade: Crawl4AI → Trafilatura → Playwright → Scrapy |
| File ingestion (PDF/DOCX/PPTX/XLSX) | With OCR fallback for scanned PDFs via DocTR |
| ChromaDB vector storage | Per-tenant collections with agentId metadata filter |
| Semantic search | Embedding-based top-K retrieval via ChromaDB |
| Hybrid retrieval (BM25 + semantic) | Client-side BM25 scoring combined with semantic results |
| Groq LLM generation | Via Groq API with token limit management and condensing |
| Conversation history (Redis) | 24h TTL, last 20 turns stored per session |
| Chat interface (frontend) | Sends to `/api/runner/chat` via Next.js proxy |
| Redis rate limiting | Per-tenant with in-memory fallback |
| MinIO file storage | Per-tenant object paths (`{tenantId}/{timestamp}-{filename}`) |
| Twilio voice (TwiML Gather loop) | Inbound calls → speech recognition → RAG → TTS response, auto-loops |
| Per-tenant Twilio credentials | AES-256-GCM encrypted, stored in tenant settings, client cache with 5-min TTL |
| Real Twilio number provisioning | Search → purchase → webhook config → store in Agent record |
| Twilio webhook validation | Per-tenant auth token decryption for signature verification |
| Agent template system | 6 seeded templates (General, Sales, Healthcare, Legal, Restaurant, Real Estate) |
| Prompt assembly service | Dynamic system prompt from template + agent configuration |
| Voice selector UI | 5 preset voices + voice cloning via Chatterbox Turbo |
| TTS microservice | Self-hosted Chatterbox Turbo 350M, MinIO caching, SHA-256 dedup |
| Call logging | CallLog records with duration, transcript, caller phone |
| Onboarding progress (server-side) | GET/POST/DELETE `/onboarding/progress` for resume |
| Deploy gating | Frontend checks Twilio credential status before allowing deploy |

### Partially Implemented / Mocked

| Component | Issue |
|---|---|
| Analytics dashboard | All routes return hardcoded data — no real DB aggregation |
| Admin pipelines page | UI page exists, no backend |
| Billing / invoices | Frontend API methods exist, no backend routes |
| Notifications | Frontend API methods exist, no backend routes |
| Backup / restore | Frontend API methods exist, no backend routes |
| Onboarding progress persistence | Stored in process memory — lost on server restart |

### Known Issues

| Issue | Impact |
|---|---|
| Agent config never used in RAG | Persona, tone, behavior rules, escalation triggers collected in onboarding but **not injected into LLM prompt at inference time** |
| Conversation history not passed to LLM | Redis stores 20 turns but `generateResponse()` only sends `[system, user]` — no history in messages array |
| TypeScript build errors suppressed | `next.config.mjs` has `typescript: { ignoreBuildErrors: true }` |
| `localStorage` in ApiClient constructor | Throws during SSR; Clerk token getter in class method always returns `null` |
| Inconsistent backend URL env vars | Frontend uses `BACKEND_URL`, `NEW_BACKEND_URL`, and `NEXT_PUBLIC_API_URL` interchangeably |

---

## Data Models

### PostgreSQL — Unified Prisma Schema (`new_backend/express-backend/prisma/schema.prisma`)

```
Tenant
  id (cuid), name, domain?, apiKey, settings (JSON — includes encrypted
  Twilio creds, twilioCredentialsVerified flag), isActive
  → has many: Users, Agents, Documents, Brands

User
  id (cuid), email, name?, role, tenantId, brandId?
  → belongs to: Tenant, Brand

Brand
  id (cuid), tenantId, name
  → belongs to: Tenant

Agent
  id (cuid), name, systemPrompt?, voiceType, llmPreferences (JSON),
  tokenLimit, contextWindowStrategy, tenantId, userId, brandId?,
  templateId?, phoneNumber?, twilioNumberSid?, chromaCollection?,
  channels (JSON), status
  → belongs to: Tenant, User, Brand, AgentTemplate
  → has one: AgentConfiguration
  → has many: Documents, CallLogs

AgentConfiguration
  agentId (unique FK), templateId?, agentName, agentRole,
  agentDescription, personalityTraits (JSON), communicationChannels (JSON),
  preferredResponseStyle, responseTone, voiceId?, voiceCloneSourceUrl?,
  companyName, industry, primaryUseCase, behaviorRules (JSON),
  escalationTriggers (JSON), knowledgeBoundaries (JSON),
  maxResponseLength, confidenceThreshold
  → belongs to: Agent, AgentTemplate

AgentTemplate
  id (cuid), name (unique), description, category?,
  baseSystemPrompt, defaultCapabilities (JSON),
  suggestedKnowledgeCategories (JSON), defaultTools (JSON)

OnboardingProgress
  id (autoincrement), userEmail (unique), tenantId?, agentId?,
  currentStep, data (JSON)

Document
  id (cuid), url?, s3Path?, status, title?, content?, metadata (JSON),
  tenantId, agentId
  → status: pending | processing | completed | failed

CallLog
  id (cuid), tenantId, agentId, callerPhone?, startedAt,
  endedAt?, durationSeconds?, transcript, analysis (JSON),
  rating?, flaggedForRetraining
```

### ChromaDB

```
Collection name: "tenant_{tenantId}"
  Document chunks with float32 embeddings (384-dim, all-MiniLM-L6-v2)
  Metadata per chunk: {
    agentId: string,
    source: string,        ← URL or filename
    chunk: number,         ← chunk index within document
    content_type: string,  ← "webpage" | "pdf" | "docx" | ...
    filename?: string,
    file_type?: string
  }
```

### Redis Keys

```
conversation:{tenantId}:{agentId}:{sessionId}  → JSON array of messages (TTL: 24h)
twilio:session:{CallSid}                       → JSON { agentId, tenantId, callSid } (TTL: 1h)
job:{jobId}                                    → ingestion job status string
job:{jobId}:progress                           → "0"–"100" percent
rate_limit:{tenantId}:{endpoint}               → request count (TTL: 15m)
```

---

## Patent — Multi-Tenant RAG Voice Agent System

### Title

**System and Method for Multi-Tenant Retrieval-Augmented Voice Agents with Isolated Knowledge Stores and Hierarchical Dynamic Context Injection**

### Core Problem Being Solved

Existing AI voice systems and RAG assistants either:
- Use a **single shared vector database** with tenant tags — weak isolation, cross-tenant data risk, no per-tenant retrieval customization
- **Duplicate entire pipelines** per customer — expensive, operationally unscalable

Neither approach provides automated per-tenant knowledge isolation combined with dynamic, hierarchical context injection into the retrieval and generation pipeline for real-time voice interaction.

### What Makes This Novel

The system combines four distinctly novel technical elements that do not appear together in any known prior art:

**1. Per-Tenant and Per-Agent Vector Store Isolation**
Document embeddings are stored in dedicated ChromaDB collections named `tenant_{tenantId}`, further segmented by `agentId` via metadata filtering. Retrieval is scoped at storage level — not merely filtered in a shared pool. Per-agent sub-collections can be provisioned independently within a tenant, enabling multiple domain-specific agents per organization.

**2. Hierarchical Context Injection (Global → Tenant → Brand → Agent → Session)**
Before any document retrieval occurs, the system assembles a structured context object across five explicit layers. This is the primary technical differentiator:

```
Layer 1 — GLOBAL
  Platform safety instructions, output format constraints,
  off-topic handling rules, base behavior guardrails

Layer 2 — TENANT
  Organization name, industry, domain, high-level compliance
  requirements, tenant-wide policies
  Source: Tenant.settings (PostgreSQL)

Layer 3 — BRAND  (optional)
  Brand-specific voice and tone, restricted terminology,
  escalation contacts, topic boundaries
  Source: Brand model (PostgreSQL)

Layer 4 — AGENT
  Persona name and role, personality traits, response tone,
  allowed topics, escalation triggers, knowledge boundaries,
  max response length, confidence threshold
  Source: AgentConfiguration (PostgreSQL)

Layer 5 — SESSION
  Active conversation history for the current session,
  user context, in-flight state
  Source: Redis conversation cache
```

This hierarchy is evaluated on every request. Lower layers take precedence over higher layers where they conflict. The context object is passed to the retrieval engine before any vector search occurs, modifying both what is retrieved and how the final prompt is assembled.

**3. Policy-Based Retrieval Scoring**
Standard vector similarity scores from ChromaDB are modified by a policy scoring pass before chunks are admitted to the prompt:
- Chunks violating tenant compliance rules are excluded
- Content tagged with restricted categories is demoted or removed
- Recency, source authority, and document classification are applied as multiplicative weights
- `AgentConfiguration.knowledgeBoundaries` provides agent-level exclusion rules enforced before prompt assembly

**4. Tight Voice + Telephony Integration Under Same RAG Layer**
The same hierarchical RAG execution layer serves real-time voice calls via Twilio Media Streams. Tenant resolution for voice uses telephony routing metadata (called phone number → tenant lookup), not just auth tokens. The complete STT → context injection → retrieval → dynamic prompt → LLM → TTS → audio response pipeline operates under per-tenant context constraints.

### System Architecture Under the Patent

```
Incoming Request (Voice or Text)
          │
          ▼
┌──────────────────────────────────────────────────────────┐
│              TENANT RESOLUTION                           │
│  • Auth JWT token   → extract tenantId                   │
│  • API key          → lookup tenant                      │
│  • Twilio "To:"     → phone_number_map → tenantId        │
│  • Subdomain        → tenant routing                     │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│    HIERARCHICAL CONTEXT INJECTION MODULE                 │
│                                                          │
│  Load from PostgreSQL:                                   │
│    layer_1 ← global system config (static)              │
│    layer_2 ← Tenant { name, industry, policies }         │
│    layer_3 ← Brand  { voice, terminology, escalation }   │
│    layer_4 ← AgentConfiguration {                        │
│                persona, traits, tone, behavior_rules,    │
│                escalation_triggers, knowledge_boundaries, │
│                confidence_threshold, max_response_length  │
│              }                                           │
│  Load from Redis:                                        │
│    layer_5 ← conversation history for current session    │
│                                                          │
│  Output: ContextObject { all 5 layers, merged }          │
└────────────────────┬─────────────────────────────────────┘
                     │
          ┌──────────▼─────────┐
          │  If voice input:   │
          │  STT (Vosk/Whisper) │
          │  → text transcript  │
          └──────────┬─────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│              RETRIEVAL ENGINE                            │
│                                                          │
│  Query embedding → ChromaDB["tenant_{tenantId}"]         │
│    + agentId filter (from ContextObject layer 4)         │
│    + KnowledgeBoundary pre-filter (layer 4 rules)        │
│                                                          │
│  Results → Policy Scoring:                               │
│    base_score × policy_weight[category]                  │
│    × recency_factor × source_authority                   │
│    − compliance_exclusion_filter                         │
│                                                          │
│  Output: top-K ranked, policy-compliant chunks           │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│           DYNAMIC PROMPT ASSEMBLY                        │
│                                                          │
│  [layer_1: base safety instructions]                     │
│  [layer_2: "You work for {company}. Industry: {domain}"] │
│  [layer_3: "Brand voice: {tone}. Avoid: {restrictions}"] │
│  [layer_4: "Your name is {name}. Role: {role}.           │
│             Escalate when: {triggers}.                   │
│             Never discuss: {boundaries}."]               │
│  [Retrieved document excerpts — policy-filtered]         │
│  [layer_5: Recent conversation history]                  │
│  [Current user query]                                    │
│                                                          │
│  Assembled dynamically per request. Never static.        │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
             LLM Inference (Groq)
             Optional: dynamic model selection
             per tenant config / latency / cost
                     │
                     ▼
          ┌──────────▼─────────┐
          │  If voice output:  │
          │  TTS (Coqui/Mozilla)│
          │  → audio response   │
          └──────────┬─────────┘
                     │
                     ▼
          Response delivered to caller / chat
```

### What Needs to Be Built to Make All Claims True

The scaffolding is in place. Three focused modules need to be implemented:

**Module 1 — Hierarchical Context Injection Service** *(highest priority)*
A new `contextInjector.ts` service that, given `(tenantId, agentId, sessionId)`, loads all five layers and returns a structured `ContextObject`. Called at the start of every `processQuery()` invocation before any retrieval. This is the core differentiator.

**Module 2 — Dynamic Prompt Assembly**
Rewrite `generateResponse()` to accept a `ContextObject` and compose the full multi-layer prompt instead of the current static `"You are a helpful assistant."` + context template.

**Module 3 — Policy-Aware Retrieval Scoring**
Add a scoring pass after ChromaDB retrieval that reads `AgentConfiguration.knowledgeBoundaries` and tenant compliance rules, applies multiplicative weights and exclusion filters before chunks enter the prompt.

**Previously completed:**
- ~~Module 4 — Schema Unification~~ → `AgentConfiguration`, `Brand`, `OnboardingProgress`, `CallLog` all exist in the backend Prisma schema.
- ~~Module 5 — Phone Number to Tenant Mapping~~ → `Agent.phoneNumber` and `Agent.twilioNumberSid` fields, looked up by `/twilio/voice/incoming` handler via `req.body.To`.

### Implementation Status of Patent Claims

| Claim | Description | Status |
|---|---|---|
| 1 | Receive input → resolve tenant → inject metadata → query isolated store → dynamic prompt → LLM → deliver | Partial — isolation and retrieval work; context injection and dynamic prompt not yet wired |
| 2 | Auto-create tenant vector store on first ingestion | **Done** — `get_or_create_collection()` in ingestion service |
| 3 | Tenant metadata includes policies, compliance, persona | Data model exists in backend schema; not yet read at inference time |
| 4 | Per-agent sub-stores within a tenant | **Done** via `agentId` metadata filter in ChromaDB |
| 5 | Policy-based filtering of retrieved chunks | Not implemented — no policy scoring layer exists yet |
| 6 | Conversation state loaded and incorporated into prompt | Redis storage exists; not yet passed to LLM messages array |
| 7 | Dynamic LLM model selection per tenant config | Not implemented — hardcoded to `grok-beta` for all tenants |
| 8 | Policy-weighted similarity scores modifying retrieval | Not implemented |
| 9 | Dynamic prompt assembly (not static template) | Not implemented — current prompt is a static 2-line template |
| 10 | Real-time ingestion without downtime | **Done** — FastAPI background task ingestion |
| 11 | Tenant isolation at storage AND inference layers | Storage: done. Inference-layer isolation: not yet enforced |
| 12 | Telephony with tenant-from-phone-number resolution | **Done** — `/incoming` handler looks up Agent by `req.body.To` phone number |
| 13 | TTS audio response back via telephony | **Done** — Chatterbox Turbo TTS integrated into TwiML Gather loop |
| 14 | Non-voice channels use same RAG pipeline | **Done** — `/api/runner/chat` uses identical `ragService` |
| 15 | Shared infra, logically separated per-tenant | Architecture supports it; inference-layer separation not fully enforced |

### Distinguishing Features vs. Prior Art

| Prior Art | What It Does | Gap vs. VoiceFlow |
|---|---|---|
| US20250165480A1 — General RAG improvements | Hybrid retrieval, chunking strategies | No per-tenant isolated collections; no hierarchical context injection |
| AU2019202632B2 — Multi-tenant conversational AI | Multi-tenant agents | Does not disclose per-tenant RAG pipelines with systemic context injection |
| US20250300950A1 — Contextual memory fusion | Adjusts responses using user context/memory | No strict per-tenant vector store isolation; no policy scoring |
| General enterprise RAG platforms | RAG with custom models | No telephony integration; no hierarchical layer injection |

The combination of per-tenant isolated vector stores, five-layer hierarchical context injection, policy-based retrieval scoring, and tight telephony integration does not appear together in any described prior art.

---

## License

MIT License — see LICENSE file for details.