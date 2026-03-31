# VoiceFlow AI Platform

A multi-tenant SaaS platform for building, deploying, and managing AI-powered voice and chat agents. Businesses onboard through a guided wizard, upload their knowledge base, and receive a domain-specific AI agent that answers customer queries over phone (Twilio) or a web chat interface — using Retrieval-Augmented Generation (RAG) over their own documents.

> **Honest Status:** This is a functional early prototype. The core RAG pipeline and onboarding flow work. Several enterprise dashboard sections currently return mock data. See the [Implementation Status](#implementation-status) section for the full picture.


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
│   │   │   RAG Service       │   │   Voice Service          │    │  │
│   │   │                     │   │                          │    │  │
│   │   │  • Hybrid retrieval │   │  • Vosk ASR (local)      │    │  │
│   │   │  • BM25 scoring     │   │  • Whisper API (cloud)   │    │  │
│   │   │  • Context condense │   │  • Coqui TTS (local)     │    │  │
│   │   │  • Groq LLM call    │   │  • Audio processing      │    │  │
│   │   │  • Conv. history    │   └──────────────────────────┘    │  │
│   │   └─────────────────────┘                                   │  │
│   │                                                              │  │
│   │   ┌─────────────────────┐   ┌──────────────────────────┐    │  │
│   │   │   Twilio Media Svc  │   │   MinIO Service          │    │  │
│   │   │                     │   │                          │    │  │
│   │   │  • TwiML generation │   │  • Per-tenant buckets    │    │  │
│   │   │  • WebSocket stream │   │  • File upload/download  │    │  │
│   │   │  • Call management  │   │  • S3-compatible API     │    │  │
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
                              │  │ Job status │  │ (S3-compat) │  │
                              │  └────────────┘  └─────────────┘  │
                              └────────────────────────────────────┘
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
| ASR | Vosk (local) / OpenAI Whisper (cloud) |
| TTS | Coqui TTS (local) / Mozilla TTS |
| Telephony | Twilio (voice webhooks, Media Streams) |
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

### Voice Call Flow (Twilio)

```
Caller dials Twilio number
        │
        ▼
Twilio → POST /twilio/voice (Express webhook)
        │ Returns TwiML: <Connect><Stream url="wss://ngrok-url/socket.io"/>
        │
        ▼
Socket.IO connection established (client = Twilio)
        │
  [on "start"]  → store session metadata (tenantId, agentId)
        │
  [on "media"]  → accumulate base64 audio chunks
        │         when buffer >= 32000 bytes:
        │           voiceService.transcribeAudio(buffer)
        │             → Vosk ASR (local 16kHz PCM) OR
        │             → OpenAI Whisper API
        │           ragService.processQuery(transcript)
        │           voiceService.generateSpeech(response)
        │             → Coqui TTS (local) OR Mozilla TTS
        │           socket.emit("response", { text, audio })
        │
  [on "stop"]   → cleanup session, free Vosk recognizer
```

---

## Running the Project

### Prerequisites

- Docker Desktop (for infrastructure)
- Node.js 18+
- Python 3.10+
- `npm` or `pnpm`
- Clerk account → API keys
- Groq API key
- (Optional) OpenAI API key for Whisper, Twilio account for phone

### Step 1 — Start Infrastructure

```bash
cd new_backend
docker-compose up -d
```

This starts PostgreSQL (5433), Redis (6379), MinIO (9000/9001), and ChromaDB (8002).

### Step 2 — Configure Environment Files

**Express Backend** (`new_backend/express-backend/.env`):
```env
# Database
DATABASE_URL=postgresql://vf_admin:vf_secure_2025!@localhost:5433/voiceflow_prod

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# ChromaDB
CHROMA_URL=http://localhost:8002

# Clerk Authentication
CLERK_SECRET_KEY=sk_test_...
CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_API_KEY=...

# External APIs
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...       # Optional, for Whisper ASR

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Twilio (Optional, for voice calls)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
NGROK_URL=your-ngrok-url.ngrok.io

# Voice
ASR_ENGINE=vosk              # vosk | whisper
TTS_ENGINE=coqui             # coqui | mozilla
VOSK_MODEL_PATH=./models/vosk-model

# App
PORT=8000
NODE_ENV=development
FRONTEND_URL=http://localhost:3000
```

**Ingestion Service** (`new_backend/ingestion-service/.env`):
```env
REDIS_HOST=localhost
REDIS_PORT=6379
CHROMA_PATH=./chroma_db
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

**Frontend** (`voiceflow-ai-platform (1)/.env.local`):
```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
CLERK_API_KEY=...
DATABASE_URL=postgresql://vf_admin:vf_secure_2025!@localhost:5433/voiceflow_prod
NEXT_PUBLIC_API_URL=http://localhost:8000
NEW_BACKEND_URL=http://localhost:8000
```

### Step 3 — Start Express Backend

```bash
cd new_backend/express-backend
npm install
npx prisma generate
npx prisma db push
npm run dev
```

### Step 4 — Start Ingestion Service

```bash
cd new_backend/ingestion-service
pip install -r requirements.txt
# On Windows, also install Playwright browser:
playwright install chromium
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Step 5 — Start Frontend

```bash
cd "voiceflow-ai-platform (1)"
npm install
npx prisma generate
npm run dev
```

### Step 6 — Access the Application

| Interface | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Express API | http://localhost:8000 |
| FastAPI Ingestion Docs | http://localhost:8001/docs |
| MinIO Console | http://localhost:9001 (minioadmin / minioadmin) |
| ChromaDB | http://localhost:8002 |

### (Optional) Voice Calls via Twilio

```bash
# Expose local port publicly
ngrok http 8000
```

Set `NGROK_URL` in your `.env`, then configure your Twilio phone number's voice webhook to:
```
https://your-ngrok-url.ngrok.io/twilio/voice
```

Download a Vosk model for local ASR:
```bash
mkdir -p new_backend/express-backend/models
cd new_backend/express-backend/models
# Download from https://alphacephei.com/vosk/models
# Recommended: vosk-model-small-en-us-0.15 (~40MB)
```

---

## Environment Variables

### Required

| Variable | Service | Description |
|---|---|---|
| `DATABASE_URL` | Backend, Frontend | PostgreSQL connection string |
| `CLERK_SECRET_KEY` | Backend, Frontend | Clerk secret for JWT verification |
| `CLERK_PUBLISHABLE_KEY` | Frontend | Clerk public key |
| `GROQ_API_KEY` | Backend | LLM inference via Groq |
| `REDIS_HOST` / `REDIS_PORT` | Backend, Ingestion | Redis connection |
| `CHROMA_URL` / `CHROMA_PATH` | Backend, Ingestion | ChromaDB endpoint |

### Optional

| Variable | Service | Description |
|---|---|---|
| `OPENAI_API_KEY` | Backend | Whisper ASR (cloud fallback) |
| `TWILIO_ACCOUNT_SID` | Backend | Twilio voice integration |
| `TWILIO_AUTH_TOKEN` | Backend | Twilio voice integration |
| `TWILIO_PHONE_NUMBER` | Backend | Assigned phone number |
| `NGROK_URL` | Backend | Public URL for Twilio webhooks |
| `VOSK_MODEL_PATH` | Backend | Path to local Vosk model directory |
| `MINIO_ENDPOINT` | Backend, Ingestion | MinIO/S3 endpoint |
| `MINIO_ACCESS_KEY` | Backend, Ingestion | MinIO credentials |
| `MINIO_SECRET_KEY` | Backend, Ingestion | MinIO credentials |

---

## Services & Ports

| Service | Technology | Port | Role |
|---|---|---|---|
| Frontend | Next.js 15 | 3000 | UI, dashboard, onboarding |
| Express Backend | Node.js | 8000 | Auth, agents, RAG, voice, API |
| Ingestion Service | FastAPI | 8001 | Scraping, embedding, ChromaDB writes |
| PostgreSQL | Docker | 5433 | Primary relational data |
| Redis | Docker | 6379 | Conversation cache, rate limits, job queue |
| MinIO | Docker | 9000/9001 | File storage (S3-compatible) |
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
| GET | `/twilio/numbers` | Get available phone numbers |
| POST | `/twilio/voice` | Incoming call webhook (TwiML response) |
| POST | `/twilio/call` | Initiate outbound call |
| GET | `/twilio/call/:callSid` | Get call status |

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
| 7-step onboarding wizard | Steps 1-4 persist to backend; Step 7 returns mock phone |
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
| Twilio webhook (TwiML) | TwiML generation works; full E2E voice untested |
| Vosk ASR | Works when model is downloaded locally |
| Coqui TTS | Works when Coqui model is installed |

### Partially Implemented / Mocked

| Component | Issue |
|---|---|
| Analytics dashboard | All routes return hardcoded data — no real DB aggregation |
| Twilio phone numbers | Returns 2 hardcoded mock numbers |
| `/onboarding/voice` | Returns `{ success: true }`, no persistence |
| `/onboarding/channels` | Returns `{ success: true }`, no persistence |
| `/onboarding/deploy` | Returns hardcoded mock phone number |
| Onboarding progress | Stored in process memory — lost on server restart |
| Admin pipelines page | UI page exists, no backend |
| Billing / invoices | Frontend API methods exist, no backend routes |
| Notifications | Frontend API methods exist, no backend routes |
| Backup / restore | Frontend API methods exist, no backend routes |

### Known Issues

| Issue | Impact |
|---|---|
| `x-tenant-id: 'default-tenant'` hardcoded in Next.js proxy | Multi-tenancy broken — all users share a single tenant |
| Two incompatible Prisma schemas | `AgentConfiguration`, `Brand`, `OnboardingProgress` exist only in frontend schema, not backend |
| Agent config never used in RAG | Persona, tone, behavior rules, escalation triggers collected in onboarding but **never injected into LLM prompt** |
| Conversation history not passed to LLM | Redis stores 20 turns but `generateResponse()` only sends `[system, user]` — no history in messages array |
| TypeScript build errors suppressed | `next.config.mjs` has `typescript: { ignoreBuildErrors: true }` |
| `localStorage` in ApiClient constructor | Throws during SSR; Clerk token getter in class method always returns `null` |
| No environment variable validation | App fails silently when `GROQ_API_KEY`, `CLERK_SECRET_KEY` etc. are missing |

---

## Data Models

### PostgreSQL — Backend (Runtime, source of truth)

```
Tenant
  id (cuid), name, domain?, apiKey, settings (JSON), isActive
  → has many: Users, Agents, Documents

User
  id (cuid), email, name?, tenantId
  → belongs to: Tenant
  → has many: Agents

Agent
  id (cuid), name, systemPrompt?, voiceType, llmPreferences (JSON),
  tokenLimit, contextWindowStrategy, tenantId, userId
  → belongs to: Tenant, User
  → has many: Documents

Document
  id (cuid), url?, s3Path?, status, title?, content?, metadata (JSON),
  tenantId, agentId
  → status: pending | processing | completed | failed
```

### PostgreSQL — Frontend (Onboarding / user-facing state)

Additional models that exist only in the frontend schema and need to be migrated to the backend:

```
AgentConfiguration
  agentId, agentName, agentRole, agentDescription,
  personalityTraits (JSON), communicationChannels (JSON),
  preferredResponseStyle, responseTone,
  companyName, industry, primaryUseCase,
  behaviorRules (JSON), escalationTriggers (JSON),
  knowledgeBoundaries (JSON),
  maxResponseLength, confidenceThreshold

OnboardingProgress
  userEmail, tenantId, agentId, currentStep, data (JSON)

Brand
  id, tenantId, name
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

The scaffolding is in place. Five focused modules need to be implemented:

**Module 1 — Hierarchical Context Injection Service** *(highest priority)*
A new `contextInjector.ts` service that, given `(tenantId, agentId, sessionId)`, loads all five layers and returns a structured `ContextObject`. Called at the start of every `processQuery()` invocation before any retrieval. This is the core differentiator.

**Module 2 — Dynamic Prompt Assembly**
Rewrite `generateResponse()` to accept a `ContextObject` and compose the full multi-layer prompt instead of the current static `"You are a helpful assistant."` + context template.

**Module 3 — Policy-Aware Retrieval Scoring**
Add a scoring pass after ChromaDB retrieval that reads `AgentConfiguration.knowledgeBoundaries` and tenant compliance rules, applies multiplicative weights and exclusion filters before chunks enter the prompt.

**Module 4 — Schema Unification + AgentConfiguration in Backend**
Migrate `AgentConfiguration`, `Brand`, and `OnboardingProgress` from the frontend-only Prisma schema into the backend schema so the RAG service can load them at inference time.

**Module 5 — Phone Number to Tenant Mapping**
Add a `PhoneNumberMapping` table (`phone_number → tenantId → agentId`) and use it in the Twilio webhook for tenant resolution from called number, replacing auth-token-based resolution for voice calls.

### Implementation Status of Patent Claims

| Claim | Description | Status |
|---|---|---|
| 1 | Receive input → resolve tenant → inject metadata → query isolated store → dynamic prompt → LLM → deliver | Partial — isolation and retrieval work; context injection and dynamic prompt not yet wired |
| 2 | Auto-create tenant vector store on first ingestion | **Done** — `get_or_create_collection()` in ingestion service |
| 3 | Tenant metadata includes policies, compliance, persona | Data model exists in frontend schema; not yet read at inference time |
| 4 | Per-agent sub-stores within a tenant | Done via `agentId` metadata filter in ChromaDB |
| 5 | Policy-based filtering of retrieved chunks | Not implemented — no policy scoring layer exists yet |
| 6 | Conversation state loaded and incorporated into prompt | Redis storage exists; not yet passed to LLM messages array |
| 7 | Dynamic LLM model selection per tenant config | Not implemented — hardcoded to `grok-beta` for all tenants |
| 8 | Policy-weighted similarity scores modifying retrieval | Not implemented |
| 9 | Dynamic prompt assembly (not static template) | Not implemented — current prompt is a static 2-line template |
| 10 | Real-time ingestion without downtime | **Done** — FastAPI background task ingestion |
| 11 | Tenant isolation at storage AND inference layers | Storage: done. Inference-layer isolation: not yet enforced |
| 12 | Telephony with tenant-from-phone-number resolution | Webhook structure exists; phone-to-tenant mapping not implemented |
| 13 | TTS audio response back via telephony | Structure and code exists; untested end-to-end |
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