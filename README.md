# VoiceFlow AI Platform

A multi-tenant SaaS platform for building, deploying, and managing AI-powered voice and chat agents. Businesses onboard through a guided wizard, upload their knowledge base, and receive a domain-specific AI agent that answers customer queries over phone (Twilio), browser-based WebRTC calls, or a web chat interface — using Retrieval-Augmented Generation (RAG) over their own documents with hierarchical context injection and policy-based retrieval scoring.

> **Status (July 2025):** The full pipeline is functional end-to-end: 7-step onboarding → document ingestion → per-tenant vector isolation → 5-layer context injection → policy-scored retrieval → dynamic 7-section prompt assembly → Groq LLM generation (per-tenant model selection, conversation history in context) → TTS → multi-channel delivery (Twilio voice, WebRTC, web chat, embeddable widget, **per-agent REST API for third-party integration**). Analytics use real DB queries. A retraining pipeline captures bad calls and injects learned corrections as few-shot examples. Admin pipeline management with real CRUD. Interactive API docs via Scalar at `/api-docs`. See [Implementation Status](#implementation-status) for the full breakdown.

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
13. [What Remains — Startup Readiness Checklist](#what-remains--startup-readiness-checklist)

---

## What This Project Does

VoiceFlow lets any business create an AI agent tailored to their domain without writing code:

1. **Sign up** → authenticated via Clerk
2. **Onboarding wizard** (7 steps) → configure company profile, agent persona, knowledge base, voice settings, deployment channels
3. **Documents are ingested** → scraped from URLs or uploaded as files → chunked, embedded, stored in a per-tenant vector store in ChromaDB
4. **Agent is live** → receives questions via web chat, phone call (Twilio), or browser call (WebRTC) → hierarchical context injection (5 layers) → policy-scored retrieval from tenant-isolated store → dynamic 7-section prompt assembly → Groq LLM generation → TTS synthesis → voice or text response
5. **Continuous improvement** → bad calls are flagged → nightly pipeline extracts Q&A pairs → admins review and edit ideal responses → approved examples are injected as few-shot learning in the system prompt

The primary market is Indian SMBs. Every tenant and agent is logically isolated — one tenant cannot query another's documents.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACES                             │
│                                                                     │
│   ┌─────────────────────┐  ┌────────────────────┐ ┌─────────────┐  │
│   │   Next.js Frontend  │  │  Twilio Phone /     │ │  WebRTC     │  │
│   │   (Port 3000)       │  │  Voice Channel      │ │  Browser    │  │
│   │                     │  │                     │ │  Calls      │  │
│   │   • Landing page    │  │  • Inbound calls    │ │             │  │
│   │   • Onboarding      │  │  • TwiML webhooks   │ │  • Socket.IO│  │
│   │   • Agent dashboard │  │  • Speech recog.    │ │  • /voice   │  │
│   │   • Analytics       │  └──────────┬──────────┘ │    namespace│  │
│   │   • Retraining      │             │            └──────┬──────┘  │
│   │   • Call Widget     │             │                   │         │
│   │   • Admin panel     │             │                   │         │
│   └──────────┬──────────┘             │         ┌─────────┘         │
│              │ HTTP/REST              │         │ Embeddable Widget  │
│              │ via Next.js proxy      │         │ <script> tag       │
└──────────────┼────────────────────────┼─────────┼───────────────────┘
               │                        │         │
               ▼                        ▼         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    EXPRESS.JS BACKEND  (Port 8000)                  │
│                                                                     │
│   ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│   │  Clerk Auth  │  │ Rate Limiter │  │    19 Route Files      │   │
│   │  Middleware  │  │  (Redis)     │  │                        │   │
│   │              │  │              │  │  /auth    /agents       │   │
│   │  JWT verify  │  │  Per-tenant  │  │  /onboarding /rag      │   │
│   │  User sync   │  │  limits      │  │  /runner  /twilio      │   │
│   └──────────────┘  └──────────────┘  │  /analytics /admin     │   │
│                                       │  /brands  /retraining  │   │
│                                       │  /widget  /templates   │   │
│                                       │  /logs    /tts    ...  │   │
│                                       └───────────┬────────────┘   │
│                                                   │                 │
│   ┌───────────────────────────────────────────────▼──────────────┐  │
│   │                   CORE SERVICES (15 files)                   │  │
│   │                                                              │  │
│   │   ┌─────────────────────┐   ┌──────────────────────────┐    │  │
│   │   │  Context Injector   │   │   Prompt Assembly        │    │  │
│   │   │                     │   │                          │    │  │
│   │   │  5-layer hierarchy  │   │  7-section dynamic       │    │  │
│   │   │  Global→Tenant→     │   │  system prompt builder   │    │  │
│   │   │  Brand→Agent→       │   │  + few-shot examples     │    │  │
│   │   │  Session            │   │  from retraining         │    │  │
│   │   └─────────────────────┘   └──────────────────────────┘    │  │
│   │                                                              │  │
│   │   ┌─────────────────────┐   ┌──────────────────────────┐    │  │
│   │   │   RAG Service       │   │   Twilio Voice Svc       │    │  │
│   │   │                     │   │                          │    │  │
│   │   │  • Hybrid retrieval │   │  • TwiML Gather loop     │    │  │
│   │   │  • BM25 scoring     │   │  • Per-tenant creds      │    │  │
│   │   │  • Policy scoring   │   │  • Webhook validation    │    │  │
│   │   │  • Groq LLM call    │   │  • Redis call sessions   │    │  │
│   │   │  • Conv. history    │   └──────────────────────────┘    │  │
│   │   └─────────────────────┘                                   │  │
│   │                                                              │  │
│   │   ┌─────────────────────┐   ┌──────────────────────────┐    │  │
│   │   │  WebRTC Service     │   │   Retraining Pipeline    │    │  │
│   │   │                     │   │                          │    │  │
│   │   │  • Socket.IO /voice │   │  • Nightly batch cron    │    │  │
│   │   │  • Browser calls    │   │  • Flagged call extract  │    │  │
│   │   │  • Greeting + RAG   │   │  • Admin review queue    │    │  │
│   │   └─────────────────────┘   │  • Few-shot injection    │    │  │
│   │                              └──────────────────────────┘    │  │
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
│    - Playwright          │  │  │ 10 models  │  │ Per-tenant  │  │
│    - Scrapy (fallback)   │  │  │            │  │ collections │  │
│  • File processing       │  │  │ Tenants    │  │             │  │
│    - PDF + OCR           │  │  │ Agents     │  │ tenant_{id} │  │
│    - DOCX / DOC          │  │  │ Brands     │  │ + agentId   │  │
│    - PPTX / XLSX         │  │  │ CallLogs   │  │ metadata    │  │
│    - Images (DocTR OCR)  │  │  │ Retraining │  │             │  │
│  • Embedding generation  │  │  └────────────┘  └─────────────┘  │
│    (all-MiniLM-L6-v2)   │  │                                    │
│  • ChromaDB storage      │  │  ┌────────────┐  ┌─────────────┐  │
│  • Progress tracking     │  │  │   Redis    │  │    MinIO    │  │
│    via Redis             │  │  │ (Port 6379)│  │ (Port 9000) │  │
│                          │  │  │            │  │             │  │
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
│   │   │   ├── analytics/         ← Real Prisma-based analytics
│   │   │   ├── billing/           ← Billing page (no backend yet)
│   │   │   ├── audit/             ← Audit log page
│   │   │   ├── knowledge/         ← Knowledge base management
│   │   │   ├── calls/             ← Call log viewer
│   │   │   ├── retraining/        ← Retraining queue admin UI ★ NEW
│   │   │   ├── widget/            ← Embeddable widget manager ★ NEW
│   │   │   ├── reports/           ← Reports page
│   │   │   ├── settings/          ← Twilio / integrations
│   │   │   └── ...
│   │   ├── admin/pipelines/       ← Admin pipeline management
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
│   │   └── dashboard/             ← Dashboard sub-components (sidebar, etc.)
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
│   │   │   ├── index.ts           ← Server entry + Socket.IO + scheduler boot
│   │   │   ├── routes/            ← 19 route files
│   │   │   │   ├── agents.ts
│   │   │   │   ├── analytics.ts   ← Real Prisma queries (not mocked)
│   │   │   │   ├── auth.ts
│   │   │   │   ├── brands.ts      ← Brand CRUD ★
│   │   │   │   ├── documents.ts
│   │   │   │   ├── ingestion.ts
│   │   │   │   ├── logs.ts        ← Call log CRUD + flagging
│   │   │   │   ├── onboarding.ts
│   │   │   │   ├── rag.ts
│   │   │   │   ├── retraining.ts  ← Retraining queue API ★ NEW
│   │   │   │   ├── runner.ts      ← Chat + audio endpoints
│   │   │   │   ├── settings.ts    ← Twilio creds encryption
│   │   │   │   ├── templates.ts
│   │   │   │   ├── tts.ts
│   │   │   │   ├── twilio.ts      ← Twilio provisioning
│   │   │   │   ├── twilioVoice.ts ← TwiML Gather loop
│   │   │   │   ├── users.ts
│   │   │   │   ├── widget.ts      ← Embeddable JS widget ★ NEW
│   │   │   │   └── admin.ts
│   │   │   ├── services/          ← 15 service files
│   │   │   │   ├── contextInjector.ts   ← 5-layer context hierarchy ★
│   │   │   │   ├── promptAssembly.ts    ← 7-section system prompt ★
│   │   │   │   ├── ragService.ts        ← RAG + policy scoring ★
│   │   │   │   ├── retrainingService.ts ← Flagged call processing ★ NEW
│   │   │   │   ├── retrainingScheduler.ts ← Nightly cron ★ NEW
│   │   │   │   ├── webrtcService.ts     ← Socket.IO signaling ★ NEW
│   │   │   │   ├── callAnalysis.ts
│   │   │   │   ├── credentialsService.ts
│   │   │   │   ├── ttsService.ts
│   │   │   │   ├── voiceService.ts
│   │   │   │   ├── minioService.ts
│   │   │   │   ├── twilioClientService.ts
│   │   │   │   ├── twilioMediaService.ts
│   │   │   │   └── twilioProvisioningService.ts
│   │   │   └── middleware/
│   │   │       ├── clerkAuth.ts   ← JWT verify + user sync
│   │   │       ├── rateLimit.ts   ← Redis-based per-tenant limits
│   │   │       └── errorHandler.ts
│   │   └── prisma/schema.prisma   ← Backend DB schema (10 models)
│   └── ingestion-service/         ← ACTIVE: FastAPI ingestion
│       └── main.py                ← Scraping + embedding + ChromaDB
│
├── tts-service/                   ← ACTIVE: Chatterbox TTS microservice
│   ├── main.py                    ← FastAPI TTS server (port 8003)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
│
├── PATENT_CLAIMS_MAPPING.md       ← Patent claim → code trace mapping
│
└── tools/db_visualizer/           ← Development utility
```

> **Note:** The `not-required/` folder (legacy prior iterations) has been deleted. The active codebase is `voiceflow-ai-platform (1)/` and `new_backend/`.

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
| Real-time | Socket.IO (WebRTC signaling on `/voice` namespace) |
| File uploads | Multer |
| Scheduling | Native `setInterval` (retraining cron) |

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
ContextInjector.assemble(tenantId, agentId, sessionId)
  │
  ├─ Layer 1: Global safety rules (hardcoded)
  ├─ Layer 2: Tenant settings + policyRules (PostgreSQL)
  ├─ Layer 3: Brand voice + allowed/restricted topics (PostgreSQL)
  ├─ Layer 4: Agent config + template + persona (PostgreSQL)
  ├─ Layer 5: Session history from Redis (last 20 turns)
  └─ Few-shot: Approved RetrainingExamples from DB
        │
        ▼
ragService.processQuery(tenantId, agentId, query, assembledContext)
        │
        ├─ 1. Hybrid document retrieval
        │      ├── semanticSearch → ChromaDB /query
        │      │   (vector similarity, agentId filter, top ~7 chunks)
        │      └── keywordSearch → ChromaDB /get + BM25 scoring
        │          (client-side BM25 over fetched docs, top ~3 chunks)
        │
        ├─ 2. Combine, deduplicate, re-rank by relevance score
        │
        ├─ 3. Policy scoring pass
        │      (restrict=×0.05, require=×2.0, allow=×1.0)
        │      Rules from Tenant + Brand + Agent merged hierarchy
        │
        ├─ 4. condenseContext() — fit chunks into token budget
        │
        ├─ 5. buildSystemPrompt(assembledContext) → 7-section prompt:
        │      [1: Safety] [2: Tenant] [3: Brand] [4: Agent]
        │      [5: Few-shot] [6: Escalation] [7: Policy summary]
        │
        └─ 6. generateResponse() → POST Groq API /chat/completions
              + Store updated conversation in Redis (TTL: 24h)
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

### WebRTC Browser Call Flow

```
User clicks "Call" button on embedded widget / dashboard
        │
        ▼
Widget loads Socket.IO client → connects to /voice namespace
  socket.emit('join-call', { agentId, tenantId? })
        │
        ▼
Server: webrtcService.ts handles 'join-call'
  │ Validates agent exists in DB
  │ Creates Redis session: webrtc:session:{socketId}
  │ Generates greeting via TTS (if voiceId configured)
  └ Emits 'call-connected' + 'agent-audio' (greeting)
        │
        ▼  (user speaks — browser does STT via Web Speech API)
        │
Client sends 'audio-chunk' event with transcribed text
        │
        ▼
Server: Same pipeline as Chat —
  ContextInjector.assemble() → queryDocuments() → policyScoring()
  → buildSystemPrompt() → generateResponse() → TTS
  → Emits 'agent-audio' + 'agent-text' back to client
        │
        ▼  (loop continues until disconnect)
        │
Client emits 'end-call' or disconnects
  → Server saves CallLog, cleans Redis session
```

**Embeddable widget:** Any website can embed:
```html
<script src="https://your-domain.com/api/widget/AGENT_ID/embed.js"></script>
```
This creates a floating call button that connects via Socket.IO.

### Retraining / Continuous Improvement Flow

```
Bad call happens → user/admin flags it
  POST /api/logs/:id/flag  → CallLog.flaggedForRetraining = true
        │
        ▼
Nightly scheduler (2:00 AM, 24h interval)
  retrainingService.processFlaggedCallLogs()
        │
        ├─ Query: CallLog where flaggedForRetraining=true, retrained=false
        ├─ Parse transcript → extract user query + bad response pairs
        ├─ Create RetrainingExample records (status: "pending")
        └─ Mark CallLog.retrained = true
        │
        ▼
Admin reviews in /dashboard/retraining page
  │ Filters by status, agent
  │ Edits ideal response text
  │ Clicks Approve or Reject
  │   POST /api/retraining/:id/approve
        │
        ▼
On next query, ContextInjector.assemble() loads approved examples:
  → Prisma: RetrainingExample where status IN ['approved', 'in_prompt']
  → Up to 10 most recent, by approvedAt desc
  → Injected as Section 5 "LEARNED EXAMPLES" in buildSystemPrompt()
  → Agent immediately improves for similar queries (no fine-tuning)
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

### Analytics (real Prisma queries)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/analytics/overview` | Usage metrics overview (real CallLog aggregates) |
| GET | `/analytics/calls` | Call log history with filtering |
| GET | `/analytics/performance` | Response time, success rate charts |
| GET | `/analytics/agents/comparison` | Side-by-side agent stats |
| GET | `/analytics/realtime` | Live metrics |
| GET | `/analytics/metrics-chart` | Time-series data |

### Brands
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/brands` | List brands for tenant |
| POST | `/api/brands` | Create brand with voice/topic/policy config |
| GET | `/api/brands/:id` | Get brand details |
| PUT | `/api/brands/:id` | Update brand configuration |
| DELETE | `/api/brands/:id` | Delete brand |

### Call Logs
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/logs` | List call logs with pagination |
| GET | `/api/logs/:id` | Get call log details |
| POST | `/api/logs/:id/flag` | Flag call for retraining |
| POST | `/api/logs/:id/rate` | Rate call (thumbs up/down) |

### Retraining
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/retraining` | List retraining queue (filter by status, agentId) |
| PUT | `/api/retraining/:id` | Edit ideal response |
| POST | `/api/retraining/:id/approve` | Approve example for prompt injection |
| POST | `/api/retraining/:id/reject` | Reject example |
| POST | `/api/retraining/process-now` | Manually trigger flagged call processing |

### Widget (public — no auth)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/widget/:agentId` | Widget config JSON (name, greeting, colors) |
| GET | `/api/widget/:agentId/embed.js` | Embeddable JavaScript widget |
| POST | `/api/widget/:agentId/sessions` | Create a new conversation session (returns sessionId) |
| POST | `/api/widget/:agentId/sessions/:sessionId/message` | Send a message and get AI response (full RAG pipeline) |
| GET | `/api/widget/:agentId/sessions/:sessionId` | Get session transcript |
| DELETE | `/api/widget/:agentId/sessions/:sessionId` | End session and persist as CallLog |

### Admin — Pipeline Management
| Method | Endpoint | Description |
|---|---|---|
| POST | `/admin/pipelines` | Create a new pipeline |
| GET | `/admin/pipelines` | List all pipelines for tenant |
| PUT | `/admin/pipelines/:id` | Update pipeline name/stages |
| DELETE | `/admin/pipelines/:id` | Delete a pipeline |
| POST | `/admin/pipelines/trigger` | Trigger pipeline execution |
| GET | `/admin/pipeline_agents` | List tenant agents in pipeline format |
| POST | `/admin/pipeline_agents` | Validate agent belongs to tenant |

### API Documentation
```
GET /api-docs              →  Scalar interactive API reference UI
GET /api-docs/openapi.json →  Raw OpenAPI 3.0 specification
```

### Health
```
GET /health  →  { status: "ok", timestamp: "..." }
```

---

## Implementation Status

A complete breakdown of what works versus what needs attention.

### Fully Working

| Component | Notes |
|---|---|
| Clerk authentication | JWT verify, user sync via ClerkSync component |
| 7-step onboarding wizard | All 7 steps persist to backend, including deploy |
| URL scraping + ingestion | 4-strategy cascade: Crawl4AI → Trafilatura → Playwright → Scrapy |
| File ingestion (PDF/DOCX/PPTX/XLSX) | With OCR fallback for scanned PDFs via DocTR |
| ChromaDB vector storage | Per-tenant collections (`tenant_{id}`) with agentId metadata filter |
| Semantic search | Embedding-based top-K retrieval via ChromaDB |
| Hybrid retrieval (BM25 + semantic) | Client-side BM25 scoring combined with semantic results |
| **5-Layer Context Injection** | Global → Tenant → Brand → Agent → Session hierarchy assembled per request |
| **Policy-based retrieval scoring** | restrict=×0.05, require=×2.0, allow=×1.0 from merged Tenant/Brand/Agent rules |
| **Dynamic 7-section prompt assembly** | Safety → Tenant → Brand → Agent → Few-shot → Escalation → Policy |
| **Brand-level configuration** | Brand voice, allowed/restricted topics, policy rules — CRUD API + DB model |
| Groq LLM generation | Via Groq API with token limit management and condensing |
| Conversation history (Redis) | 24h TTL, last 20 turns stored per session |
| Chat interface (frontend) | Sends to `/api/runner/chat` via Next.js proxy |
| Redis rate limiting | Per-tenant with in-memory fallback |
| MinIO file storage | Per-tenant object paths (`{tenantId}/{timestamp}-{filename}`) |
| Twilio voice (TwiML Gather loop) | Inbound calls → speech recognition → full context pipeline → TTS → response loop |
| Per-tenant Twilio credentials | AES-256-GCM encrypted, stored in tenant settings, client cache with 5-min TTL |
| Real Twilio number provisioning | Search → purchase → webhook config → store in Agent record |
| Twilio webhook validation | Per-tenant auth token decryption for signature verification |
| Agent template system | 6 seeded templates (General, Sales, Healthcare, Legal, Restaurant, Real Estate) |
| Voice selector UI | 5 preset voices + voice cloning via Chatterbox Turbo |
| TTS microservice | Self-hosted Chatterbox Turbo 350M, MinIO caching, SHA-256 dedup |
| Call logging | CallLog records with duration, transcript, caller phone, rating, flagging |
| **Analytics dashboard** | Real Prisma queries — overview, realtime, metrics-chart, agent-comparison |
| Onboarding progress (server-side) | GET/POST/DELETE `/onboarding/progress` for resume |
| Deploy gating | Frontend checks Twilio credential status before allowing deploy |
| **Retraining pipeline** | Nightly cron extracts flagged calls → admin review queue → approved examples injected as few-shot learning |
| **WebRTC browser calls** | Socket.IO `/voice` namespace, same RAG pipeline as Twilio, no Twilio dependency |
| **Embeddable call widget** | Public `<script>` tag serves floating call button with Socket.IO WebRTC connection |
| **Retraining admin UI** | `/dashboard/retraining` — filter, edit, approve/reject, manual trigger |
| **Widget management UI** | `/dashboard/widget` — per-agent embed code with copy-to-clipboard |
| **Scalar API documentation** | Interactive API explorer at `/api-docs` with OpenAPI 3.0 spec |
| **Conversation history in LLM** | Last 20 turns from Redis passed into Groq messages array — agent remembers session context |
| **Per-tenant LLM model selection** | `resolveModel()` reads `agent.llmPreferences.model` with allowlist of 8 Groq models; default `llama-3.3-70b-versatile` |
| **Admin pipeline management** | Real Prisma CRUD: create/read/update/delete pipelines, async trigger with stage execution |
| **Per-agent REST API** | Public session-based endpoints for third-party website integration (create session → send messages → get transcript → end session) |
| **SSR-safe ApiClient** | All `localStorage` access guarded with `typeof window !== 'undefined'` — no SSR crashes |
| **Consolidated env vars** | Server-side uses `BACKEND_URL`, client-side uses `NEXT_PUBLIC_API_URL` — no more fragmented vars |

### Partially Implemented

| Component | What Exists | What's Missing |
|---|---|---|
| WebRTC audio streaming | Socket.IO signaling + text-based exchange | Uses Web Speech API for STT/TTS in browser — not true WebRTC audio tracks |
| Multi-language support | Agent `language` field in onboarding | No automatic language detection or translation pipeline |
| Voice cloning | `POST /api/tts/clone-voice` endpoint + Chatterbox integration | Quality depends on reference audio; no fine-tuning of cloned voices |

### Not Yet Implemented (Frontend Exists, No Backend)

| Component | Frontend | Notes |
|---|---|---|
| Billing / invoices | `/dashboard/billing` page + API client methods | No Stripe/payment backend; needs subscription logic |
| Notifications system | `/dashboard/notifications` page + API client methods | No notification backend service or push |
| Backup / restore | `/dashboard/backup` page + API client methods | No backend backup functionality |

### Known Issues

| Issue | Severity | Impact |
|---|---|---|
| TypeScript build errors suppressed | Low | `next.config.mjs` has `typescript: { ignoreBuildErrors: true }` |
| Prisma migration not run for new models | Blocking | `RetrainingExample`, `Pipeline` models and `retrained` field on CallLog exist in schema but require `npx prisma migrate dev` before first use |

---

## Data Models

### PostgreSQL — Unified Prisma Schema (`new_backend/express-backend/prisma/schema.prisma`)

11 models:

```
Tenant
  id (cuid), name, domain?, apiKey, settings (JSON — includes encrypted
  Twilio creds, twilioCredentialsVerified flag), policyRules (JSON),
  isActive
  → has many: Users, Agents, Documents, Brands, RetrainingExamples

User
  id (cuid), email, name?, role, tenantId, brandId?
  → belongs to: Tenant, Brand

Brand
  id (cuid), tenantId, name, brandVoice (Text), allowedTopics (JSON),
  restrictedTopics (JSON), policyRules (JSON), createdAt, updatedAt
  → belongs to: Tenant
  → has many: Users, Agents

Agent
  id (cuid), name, systemPrompt?, voiceType, llmPreferences (JSON),
  tokenLimit, contextWindowStrategy, tenantId, userId, brandId?,
  templateId?, phoneNumber?, twilioNumberSid?, chromaCollection?,
  channels (JSON), status
  → belongs to: Tenant, User, Brand, AgentTemplate
  → has one: AgentConfiguration
  → has many: Documents, CallLogs, RetrainingExamples

AgentConfiguration
  agentId (unique FK), templateId?, agentName, agentRole,
  agentDescription, personalityTraits (JSON), communicationChannels (JSON),
  preferredResponseStyle, responseTone, voiceId?, voiceCloneSourceUrl?,
  companyName, industry, primaryUseCase, behaviorRules (JSON),
  escalationTriggers (JSON), knowledgeBoundaries (JSON),
  policyRules (JSON), escalationRules (JSON),
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
  endedAt?, durationSeconds?, transcript (Text), analysis (JSON),
  rating? (Int), ratingNotes?, flaggedForRetraining (Boolean),
  retrained (Boolean, default: false), createdAt
  → has many: RetrainingExamples

RetrainingExample
  id (cuid), tenantId, agentId, callLogId, userQuery (Text),
  badResponse (Text), idealResponse (Text),
  status (String: pending | approved | rejected),
  approvedAt?, approvedBy?, createdAt, updatedAt
  → belongs to: Tenant, Agent, CallLog

Pipeline
  id (cuid), tenantId, name, stages (JSON — array of stage objects),
  status (String: idle | running | completed | failed),
  lastRunAt?, createdAt, updatedAt
  → belongs to: Tenant
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
widget:session:{sessionId}                     → JSON { agentId, tenantId, createdAt } (TTL: 1h)
widget:conversation:{sessionId}                → JSON array of messages (TTL: 24h)
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

The core patent pipeline is now fully implemented. Remaining gaps are quality-of-life improvements, not architectural.

**Completed:**
- ~~Module 1 — Hierarchical Context Injection Service~~ → `contextInjector.ts` — 5-layer hierarchy (Global → Tenant → Brand → Agent → Session)
- ~~Module 2 — Dynamic Prompt Assembly~~ → `promptAssembly.ts` — 7-section system prompt with `{{placeholder}}` replacement
- ~~Module 3 — Policy-Aware Retrieval Scoring~~ → `ragService.ts` — `applyPolicyScoring()` with restrict/require/allow multipliers
- ~~Module 4 — Schema Unification~~ → All models exist with Brand, policy, escalation fields
- ~~Module 5 — Phone Number to Tenant Mapping~~ → `Agent.phoneNumber` lookup via `req.body.To`
- ~~Module 6 — Retraining Pipeline~~ → Flagged calls → nightly extraction → admin review → few-shot injection
- ~~Module 7 — WebRTC Channel~~ → Socket.IO `/voice` namespace + embeddable widget

**Remaining gap:**
- Conversation history from Redis session (Layer 5) is loaded by `ContextInjector` but not yet passed into the Groq API `messages` array — only `[system, user]` messages are sent. Fix is straightforward: include session turns in the messages array.

See `PATENT_CLAIMS_MAPPING.md` for the full claim-to-code trace document.

### Implementation Status of Patent Claims

| Claim | Description | Status |
|---|---|---|
| 1 | Receive input → resolve tenant → inject metadata → query isolated store → dynamic prompt → LLM → deliver | **Done** — Full pipeline: ContextInjector → policy-scored retrieval → 7-section prompt → Groq → TTS/text |
| 2 | Auto-create tenant vector store on first ingestion | **Done** — `get_or_create_collection()` in ingestion service |
| 3 | Tenant metadata includes policies, compliance, persona | **Done** — Tenant.policyRules, Brand.policyRules, AgentConfiguration.policyRules + escalationRules loaded per request |
| 4 | Per-agent sub-stores within a tenant | **Done** via `agentId` metadata filter in ChromaDB |
| 5 | Policy-based filtering of retrieved chunks | **Done** — `applyPolicyScoring()` in ragService.ts with restrict/require/allow multipliers |
| 6 | Conversation state loaded and incorporated into prompt | Partial — Redis history loaded by ContextInjector (Layer 5) but not yet passed to Groq messages array |
| 7 | Dynamic LLM model selection per tenant config | Not implemented — hardcoded to `grok-beta` for all tenants |
| 8 | Policy-weighted similarity scores modifying retrieval | **Done** — same as Claim 5, via `doesPolicyMatch()` + multiplicative weights |
| 9 | Dynamic prompt assembly (not static template) | **Done** — `buildSystemPrompt()` in promptAssembly.ts, 7 sections with `{{placeholder}}` replacement |
| 10 | Real-time ingestion without downtime | **Done** — FastAPI background task ingestion |
| 11 | Tenant isolation at storage AND inference layers | **Done** — Storage: per-tenant ChromaDB collections. Inference: ContextInjector scopes all DB queries to tenantId |
| 12 | Telephony with tenant-from-phone-number resolution | **Done** — `/incoming` handler looks up Agent by `req.body.To` phone number |
| 13 | TTS audio response back via telephony | **Done** — Chatterbox Turbo TTS integrated into TwiML Gather loop |
| 14 | Non-voice channels use same RAG pipeline | **Done** — `/api/runner/chat`, WebRTC `/voice` namespace, embeddable widget all share same pipeline |
| 15 | Shared infra, logically separated per-tenant | **Done** — All services scope to tenantId; no cross-tenant data access possible |

### Distinguishing Features vs. Prior Art

| Prior Art | What It Does | Gap vs. VoiceFlow |
|---|---|---|
| US20250165480A1 — General RAG improvements | Hybrid retrieval, chunking strategies | No per-tenant isolated collections; no hierarchical context injection |
| AU2019202632B2 — Multi-tenant conversational AI | Multi-tenant agents | Does not disclose per-tenant RAG pipelines with systemic context injection |
| US20250300950A1 — Contextual memory fusion | Adjusts responses using user context/memory | No strict per-tenant vector store isolation; no policy scoring |
| General enterprise RAG platforms | RAG with custom models | No telephony integration; no hierarchical layer injection |

The combination of per-tenant isolated vector stores, five-layer hierarchical context injection, policy-based retrieval scoring, and tight telephony integration does not appear together in any described prior art.

---

## What Remains — Startup Readiness Checklist

A forward-looking assessment of what needs to happen to take VoiceFlow from "working prototype" to "production startup."

### Must Fix Before Launch

| Item | Effort | Description |
|---|---|---|
| **Run Prisma migration** | 5 min | `npx prisma migrate dev` — RetrainingExample, Pipeline models + `retrained` field on CallLog need actual DB tables |
| **Remove `ignoreBuildErrors`** | 2-4 hr | Fix all TypeScript errors so `next build` passes without suppressing type checks |
| **Production JWT_SECRET** | 5 min | Current default is `"dev-secret"` — must be a real random secret in production |

### Should Build for Production

| Item | Effort | Description |
|---|---|---|
| **Billing / Stripe integration** | 2 wk | Frontend page exists at `/dashboard/billing`; needs Stripe subscriptions, usage metering, invoice generation |
| **Email notifications** | 1 wk | Frontend page exists at `/dashboard/notifications`; needs backend email service (SendGrid/SES) + in-app notification store |
| **Backup / restore** | 1 wk | Frontend page exists at `/dashboard/backup`; needs PostgreSQL dump + ChromaDB export logic |
| **Real ASR for WebRTC** | 3 days | Current WebRTC uses browser Web Speech API; add server-side Whisper/Vosk for production-quality transcription |
| **WebRTC audio tracks** | 1 wk | Current implementation is text-based over Socket.IO; upgrade to true WebRTC peer connections with audio MediaStreams |
| **Rate limit configuration UI** | 2 days | Rate limiting works but limits are hardcoded; needs admin API to configure per-tenant limits |
| **Multi-language detection** | 3 days | Agent `language` field exists; add client language detection + prompt translation |
| **Automated testing** | 2 wk | No test suite for backend routes or frontend pages; need unit + integration tests |
| **CI/CD pipeline** | 3 days | No GitHub Actions / deployment pipeline; need build → test → deploy automation |
| **Monitoring / alerting** | 3 days | One TODO for external logging service; need structured logging, health checks, uptime monitoring |

### Infrastructure for Scale

| Item | Description |
|---|---|
| Kubernetes / ECS deployment | Currently runs as 4 separate processes; needs container orchestration for HA |
| PostgreSQL read replicas | Single instance; needs read replicas for analytics queries at scale |
| ChromaDB clustering | Single instance; needs sharding strategy for 100+ tenants |
| Redis Sentinel / Cluster | Single instance; needs HA for conversation state |
| CDN for TTS audio | MinIO-cached TTS audio should be fronted by CloudFront/CDN |
| Secrets management | Credentials in `.env` files; need AWS Secrets Manager / Vault |
| SSL/TLS termination | Needs reverse proxy (nginx/ALB) with TLS certificates |

### What Works End-to-End Today

If you start all 4 services (`docker-compose up -d`, Express backend, FastAPI ingestion, frontend):

1. Sign up via Clerk → tenant + user created automatically
2. Complete 7-step onboarding → configure company, create agent, upload documents, set voice, deploy
3. Documents are scraped/processed → embedded → stored in `tenant_{id}` ChromaDB collection
4. Ask questions via web chat → full 5-layer context injection → policy-scored retrieval → 7-section prompt → Groq LLM → text response
5. Call via Twilio → same pipeline → Chatterbox TTS → voice response → conversation loops
6. Call via WebRTC widget → embeddable `<script>` tag → Socket.IO → same pipeline → text/audio response
7. **Integrate via REST API** → any third-party website can create sessions, send messages, and get AI responses via 4 public endpoints per agent — no embed script needed
8. Agent remembers conversation context → last 20 turns from Redis included in every LLM call
9. Per-tenant model selection → each agent can use a different Groq model from the allowlist
10. Flag bad calls → nightly extraction → admin reviews/edits ideal responses → approved examples injected as few-shot learning
11. View real analytics → call counts, durations, success rates, agent comparisons from actual CallLog data
12. Configure brands → brand voice, topic restrictions, policy rules applied at inference time
13. Manage pipelines → create, configure stages, trigger execution, monitor status via admin API
14. Browse interactive API docs → Scalar UI at `/api-docs` with full OpenAPI spec

---

## License

MIT License — see LICENSE file for details.