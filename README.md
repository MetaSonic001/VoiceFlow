# VoiceFlow AI Platform

A multi-tenant SaaS platform for building, deploying, and managing AI-powered voice and chat agents. Businesses onboard through a guided wizard, upload their knowledge base, and receive a domain-specific AI agent that answers customer queries over phone (Twilio), browser-based WebSocket voice calls, or a web chat interface — using Retrieval-Augmented Generation (RAG) over their own documents with hierarchical context injection and policy-based retrieval scoring.

> **Status (April 2026):** The full pipeline is functional end-to-end: 7-step onboarding → document ingestion → per-tenant vector isolation → 5-layer context injection → policy-scored retrieval → dynamic 7-section prompt assembly → Groq LLM generation (per-tenant model selection, conversation history in all code paths) → TTS → multi-channel delivery (Twilio voice, **real WebSocket audio** with local `faster-whisper` or Groq Whisper STT + Edge/Kokoro/Piper TTS, web chat, embeddable widget, WhatsApp, **per-agent REST API for third-party integration**). Outbound campaigns with CSV upload, AMD detection, DND compliance, and real-time progress tracking. HMAC-SHA256 signed webhook dispatch with retry. A/B testing with traffic splitting. Analytics use real DB queries. A retraining pipeline captures bad calls and injects learned corrections as few-shot examples. Visual flow builder for conversation design. 29 route files (~142 endpoints), 13 services, 17 models. **Modern UI: glassmorphism, micro-interactions, 15+ CSS animations, dark mode on all 25 pages. Stack: Django 6 (HTMX + Alpine.js) frontend + FastAPI backend + Docker services (Postgres, Redis, ChromaDB, MinIO).** See [Implementation Status](#implementation-status) for the full breakdown.

---

## Table of Contents

1. [What This Project Does](#what-this-project-does)
2. [System Architecture](#system-architecture)
3. [Repository Structure](#repository-structure)
4. [Tech Stack](#tech-stack)
5. [How It Works — End to End](#how-it-works--end-to-end)
6. [Voice Pipeline Architecture](#voice-pipeline-architecture)
7. [RAG Engine Deep Dive](#rag-engine-deep-dive)
8. [LLM & AI Architecture](#llm--ai-architecture)
9. [Running the Project](#running-the-project)
10. [Environment Variables](#environment-variables)
11. [Services & Ports](#services--ports)
12. [Service Inventory](#service-inventory)
13. [API Reference](#api-reference)
14. [Security Architecture](#security-architecture)
15. [Implementation Status](#implementation-status)
16. [Data Models](#data-models)
17. [Testing](#testing)
18. [Known Limitations & Technical Debt](#known-limitations--technical-debt)
19. [Patent — Multi-Tenant RAG Voice Agent System](#patent--multi-tenant-rag-voice-agent-system)
20. [What Remains — Startup Readiness Checklist](#what-remains--startup-readiness-checklist)

---

## What This Project Does

VoiceFlow lets any business create an AI agent tailored to their domain without writing code:

1. **Sign up** → Django authentication (email/password)
2. **Onboarding wizard** (7 steps) → configure company profile, agent persona, knowledge base, voice settings, deployment channels
3. **Documents are ingested** → scraped from URLs or uploaded as files → chunked, embedded, stored in a per-tenant vector store in ChromaDB
4. **Agent is live** → receives questions via web chat, phone call (Twilio), or browser call (WebSocket) → hierarchical context injection (5 layers) → policy-scored retrieval from tenant-isolated store → dynamic 7-section prompt assembly → Groq LLM generation → TTS synthesis → voice or text response
5. **Continuous improvement** → bad calls are flagged → nightly pipeline extracts Q&A pairs → admins review and edit ideal responses → approved examples are injected as few-shot learning in the system prompt

The primary market is Indian SMBs. Every tenant and agent is logically isolated — one tenant cannot query another's documents.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACES                             │
│                                                                      │
│   ┌──────────────────────┐  ┌───────────────────┐  ┌─────────────┐  │
│   │  Django Frontend     │  │  Twilio Phone /    │  │  WebSocket  │  │
│   │  (Port 8050)         │  │  Voice Channel     │  │  Browser    │  │
│   │                      │  │                    │  │  Calls      │  │
│   │  • HTMX + Alpine.js  │  │  • Inbound calls   │  │             │  │
│   │  • Tailwind CSS      │  │  • TwiML webhooks  │  │  • /api/voice/ws/ │  │
│   │  • Onboarding wizard │  │  • Speech recog.   │  │    {agentId}│  │
│   │  • Agent dashboard   │  └─────────┬─────────┘  └──────┬──────┘  │
│   │  • Analytics         │            │                    │         │
│   │  • Retraining        │            │          ┌─────────┘         │
│   │  • Data Explorer     │            │          │ Embeddable Widget │
│   │  • Admin panel       │            │          │ <script> tag      │
│   └──────────┬───────────┘            │          │                   │
│              │ HTTP/REST              │          │                   │
│              │ via Django proxy       │          │                   │
└──────────────┼────────────────────────┼──────────┼───────────────────┘
               │                        │          │
               ▼                        ▼          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND  (Port 8040)                     │
│                                                                      │
│   ┌──────────────┐  ┌───────────────┐  ┌────────────────────────┐   │
│   │  Header Auth │  │  Rate Limiter │  │    29 Route Files      │   │
│   │  (Demo mode) │  │  (SlowAPI +   │  │                        │   │
│   │              │  │   Redis)      │  │  /auth    /agents       │   │
│   │  x-tenant-id │  │              │  │  /onboarding /rag       │   │
│   │  x-user-id   │  │  Per-tenant  │  │  /runner  /voice        │   │
│   └──────────────┘  └───────────────┘  │  /voice_ws /analytics  │   │
│                                        │  /brands  /retraining   │   │
│                                        │  /widget  /templates    │   │
│                                        │  /settings /admin       │   │
│                                        │  /platform /data_explorer│  │
│                                        │  /logs    /tts    ...   │   │
│                                        └───────────┬─────────────┘   │
│                                                    │                 │
│   ┌────────────────────────────────────────────────▼──────────────┐  │
│   │                    CORE SERVICES (4 files)                    │  │
│   │                                                               │  │
│   │   ┌─────────────────────────────────────────────────────┐     │  │
│   │   │  rag_service.py (consolidated RAG engine)           │     │  │
│   │   │                                                     │     │  │
│   │   │  • assemble_context()   — 5-layer hierarchy         │     │  │
│   │   │  • query_documents()    — hybrid semantic + BM25    │     │  │
│   │   │  • apply_policy_scoring()— restrict/require/allow   │     │  │
│   │   │  • build_system_prompt()— 7-section dynamic prompt  │     │  │
│   │   │  • generate_response()  — Groq LLM + conv history   │     │  │
│   │   │  • process_query()      — full pipeline orchestrator │     │  │
│   │   └─────────────────────────────────────────────────────┘     │  │
│   │                                                               │  │
│   │   ┌────────────────────────┐  ┌──────────────────────────┐   │  │
│   │   │  ingestion_service.py  │  │   credentials.py         │   │  │
│   │   │                        │  │                          │   │  │
│   │   │  • Docling (PDF/DOCX)  │  │  • AES-256-GCM           │   │  │
│   │   │  • PaddleOCR (scanned) │  │  • Per-tenant keys       │   │  │
│   │   │  • Trafilatura (URLs)  │  │  • encrypt/decrypt       │   │  │
│   │   │  • BeautifulSoup (fb)  │  │  • Twilio + Groq creds   │   │  │
│   │   │  • SentenceTransformer │  └──────────────────────────┘   │  │
│   │   └────────────────────────┘                                  │  │
│   │                                                               │  │
│   │   ┌────────────────────────┐                                  │  │
│   │   │  scheduler.py          │                                  │  │
│   │   │                        │                                  │  │
│   │   │  • APScheduler cron    │                                  │  │
│   │   │  • Extract flagged     │                                  │  │
│   │   │  • Embed approved      │                                  │  │
│   │   │  • Nightly pipeline    │                                  │  │
│   │   └────────────────────────┘                                  │  │
│   └───────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
               │                            │
               ▼                            ▼
┌────────────────────────────────────────────────────────────────────┐
│                         DATA STORES (Docker)                       │
│                                                                    │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│   │  PostgreSQL   │  │   ChromaDB   │  │    Redis     │            │
│   │  (Port 8010)  │  │  (Port 8030) │  │  (Port 8020) │            │
│   │               │  │              │  │              │            │
│   │  17 models    │  │  Per-tenant  │  │  Conv hist   │            │
│   │               │  │  collections │  │  BM25 index  │            │
│   │  Tenants      │  │              │  │  Rate limit  │            │
│   │  Agents       │  │  tenant_{id} │  │  Call sesh   │            │
│   │  Brands       │  │  + agentId   │  │  Job status  │            │
│   │  CallLogs     │  │  metadata    │  │              │            │
│   │  Retraining   │  │              │  │              │            │
│   └──────────────┘  └──────────────┘  └──────────────┘            │
│                                                                    │
│   ┌──────────────┐                                                 │
│   │    MinIO      │                                                │
│   │  API: 9020    │                                                │
│   │  Console:8070 │                                                │
│   │               │                                                │
│   │  Per-tenant   │  ┌──────────────────────────────────────────┐  │
│   │  file store   │  │  External APIs                           │  │
│   │  TTS cache    │  │  • Groq LLM (llama-3.3-70b-versatile)   │  │
│   │  (S3-compat)  │  │  • Groq Whisper (STT)                   │  │
│   └──────────────┘  │  • Edge TTS + Kokoro fallback         │  │
│                      │  • Twilio (per-tenant telephony)         │  │
│                      └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
VoiceFlow/
│
├── python/                        ← ACTIVE: Full-stack Python codebase
│   ├── Makefile                   ← developer commands (start, reset, test, demo)
│   ├── docker-compose.yml         ← Postgres, Redis, ChromaDB, MinIO
│   │
│   ├── backend/                   ← ACTIVE: FastAPI backend (Port 8040)
│   │   ├── main.py                ← Server entry, router registration, seeding
│   │   ├── app/
│   │   │   ├── auth.py            ← Auth context from headers (demo-mode)
│   │   │   ├── config.py          ← Settings (env vars)
│   │   │   ├── database.py        ← SQLAlchemy async engine + session
│   │   │   ├── models.py          ← 12 SQLAlchemy ORM models
│   │   │   ├── routes/            ← 29 route files
│   │   │   │   ├── agents.py      ← Agent CRUD + activate/pause
│   │   │   │   ├── analytics.py   ← Real DB-based analytics
│   │   │   │   ├── auth.py        ← Login/signup/user-sync
│   │   │   │   ├── brands.py      ← Brand CRUD (voice, topics, policies)
│   │   │   │   ├── campaigns.py   ← Campaign CRUD + contacts + AMD
│   │   │   │   ├── dnd.py         ← DND registry management
│   │   │   │   ├── documents.py   ← Document CRUD + upload
│   │   │   │   ├── ingestion.py   ← Ingestion job start/status
│   │   │   │   ├── logs.py        ← Call log CRUD + flagging
│   │   │   │   ├── onboarding.py  ← 16 wizard endpoints
│   │   │   │   ├── rag.py         ← RAG query + conversation history
│   │   │   │   ├── retraining.py  ← Retraining queue + process flagged
│   │   │   │   ├── runner.py      ← Chat + audio endpoints
│   │   │   │   ├── settings.py    ← Twilio/Groq creds (AES-256-GCM)
│   │   │   │   ├── templates.py   ← Agent template CRUD
│   │   │   │   ├── tts.py         ← TTS preset voices, preview, clone
│   │   │   │   ├── voice_inbound_router.py ← Inbound call dispatcher
│   │   │   │   ├── voice_twilio_gather.py  ← Twilio TwiML Gather loop
│   │   │   │   ├── voice_twilio_stream.py  ← Twilio Media Streams (WebSocket)
│   │   │   │   ├── voice_ws.py    ← WebSocket voice (browser calls)
│   │   │   │   ├── webhooks.py    ← Webhook CRUD + HMAC-signed dispatch
│   │   │   │   ├── whatsapp.py    ← WhatsApp inbound handler
│   │   │   │   ├── widget.py      ← Embeddable JS widget (public)
│   │   │   │   ├── ab_testing.py  ← A/B test variant management
│   │   │   │   ├── admin.py       ← Pipeline CRUD + trigger
│   │   │   │   ├── platform.py    ← Audit, notifications, health
│   │   │   │   ├── data_explorer.py ← Postgres/ChromaDB/Redis viewer
│   │   │   │   └── users.py       ← User management
│   │   │   └── services/          ← 13 service modules
│   │   │       ├── rag_service.py         ← 5-layer context injection +
│   │   │       │                            policy scoring + 7-section
│   │   │       │                            prompt assembly + multi-LLM
│   │   │       ├── ingestion_service.py   ← Docling + PaddleOCR + scraping
│   │   │       ├── streaming_orchestrator.py ← Real-time voice pipeline
│   │   │       ├── tts_router.py          ← Multi-engine TTS (Kokoro/Piper/Edge)
│   │   │       ├── stt_service.py         ← STT (Vosk/faster-whisper/Groq)
│   │   │       ├── campaign_worker.py     ← Outbound campaign execution
│   │   │       ├── compliance_service.py  ← DND/hours/retry compliance
│   │   │       ├── webhook_service.py     ← HMAC-SHA256 event dispatch
│   │   │       ├── flow_engine.py         ← Conversation flow execution
│   │   │       ├── credentials.py         ← AES-256-GCM encryption
│   │   │       └── scheduler.py           ← APScheduler nightly cron
│   │
│   └── frontend/                  ← ACTIVE: Django 6.0.4 frontend (Port 8050)
│       ├── manage.py
│       ├── core/
│       │   ├── urls.py            ← All URL routes
│       │   ├── api_client.py      ← Unified backend API client
│       │   └── views/
│       │       ├── dashboard.py   ← Agent list + detail views
│       │       ├── pages.py       ← All dashboard page views
│       │       ├── api_proxy.py   ← 55 proxy endpoints for JS/HTMX
│       │       ├── onboarding.py  ← 7-step wizard view
│       │       ├── auth.py        ← Login/register/logout
│       │       └── chat.py        ← Chat + voice agent views
│       └── templates/
│           ├── base_dashboard.html
│           ├── partials/sidebar.html
│           ├── onboarding/flow.html   ← 7-step wizard (Alpine.js)
│           ├── agents/detail.html     ← Agent detail + chat
│           └── dashboard/             ← 25 dashboard pages
│               ├── analytics.html     ← Charts + metrics
│               ├── ab_testing.html    ← A/B test management
│               ├── audit.html         ← Filterable audit log
│               ├── brands.html        ← Brand voice config
│               ├── billing.html       ← Usage & plans
│               ├── calls.html         ← Call log viewer
│               ├── campaigns.html     ← Outbound campaigns
│               ├── data_explorer.html ← DB visualiser
│               ├── dnd.html           ← DND registry
│               ├── integrations.html  ← Integration status
│               ├── knowledge.html     ← Knowledge base management
│               ├── notifications.html ← Notification center
│               ├── pipelines.html     ← Admin pipelines
│               ├── reports.html       ← Generated reports
│               ├── retraining.html    ← Retraining queue admin
│               ├── settings.html      ← Twilio/Groq/voice config
│               ├── system.html        ← System health monitor
│               ├── voice_agent.html   ← Real-time voice testing
│               ├── webhooks.html      ← Webhook endpoint management
│               ├── whatsapp.html      ← WhatsApp config
│               ├── widget.html        ← Embed code manager
│               └── ...
│
├── PATENT_CLAIMS_MAPPING.md       ← Patent claim → code trace mapping
│
├── test_all_endpoints.py          ← API regression test script
├── test_rag_pipeline.py           ← RAG E2E test script
└── pyproject.toml                 ← Single dependency source (uv sync)
```

> **Note:** The active runtime codebase is `python/` — `python/backend/` (FastAPI) and `python/frontend/` (Django).

---

## Tech Stack

### Frontend
| Layer | Technology |
|---|---|
| Framework | Django 6.0.4 |
| Language | Python 3.12 |
| Templating | Django Templates + HTMX + Alpine.js |
| Styling | Tailwind CSS (via CDN) |
| Charts | Chart.js |
| Auth | Django built-in authentication |
| Interactivity | Alpine.js (reactive state, forms, modals) |
| Server Communication | HTMX + fetch API (via Django proxy endpoints) |

### Backend (FastAPI)
| Layer | Technology |
|---|---|
| Runtime | Python 3.12 |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Auth | Header-based tenant context (demo-mode) |
| Validation | Pydantic (via FastAPI) |
| Real-time | Native WebSocket (voice channel) |
| File uploads | FastAPI UploadFile + MinIO |
| Scheduling | APScheduler (retraining cron) |
| Rate Limiting | SlowAPI (Redis-backed, per-tenant) |

### Ingestion Pipeline (in FastAPI backend)
| Layer | Technology |
|---|---|
| Document Parsing | Docling (`DocumentConverter`) |
| OCR | PaddleOCR (scanned PDFs/images) |
| Scraping | Trafilatura + BeautifulSoup fallback |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) |
| Chunking | LangChain `RecursiveCharacterTextSplitter` |

### Infrastructure
| Component | Technology |
|---|---|
| Primary DB | PostgreSQL 15 (Docker, port 8010) |
| Vector Store | ChromaDB (Docker, port 8030) |
| Cache / Queue | Redis 7 (Docker, port 8020) |
| File Storage | MinIO S3-compatible (Docker, port 9020/8070) |
| LLM | Groq API (`Llama` / `GPT-OSS` family) |
| TTS | Edge TTS (primary) + Kokoro local fallback/cloning |
| Telephony | Twilio (TwiML Gather loop, per-tenant credentials) |
| Credential Encryption | AES-256-GCM via `cryptography` library |
| Build / Dev Tooling | PowerShell Makefile with startup, reset, and test targets |

---

## How It Works — End to End

### Onboarding Flow (New Tenant)

```
User signs up via Django auth (email/password)
        │
        ▼
POST /auth/signup (FastAPI)
        │ Creates User + Tenant in PostgreSQL
        │ Returns { access_token, user }
        │
        ▼
Django frontend redirects to /onboarding or /dashboard
        │
        ▼
7-Step Onboarding Wizard (Alpine.js)
  Step 1: Company Profile    → POST /onboarding/company     → auto-scrapes website
  Step 2: Agent Creation     → POST /onboarding/agent       → creates Agent row
  Step 3: Knowledge Upload   → POST /onboarding/knowledge   → triggers ingestion
  Step 4: Voice & Personality→ POST /onboarding/voice       → Edge + Kokoro voice preview
  Step 5: Channel Setup      → POST /onboarding/channels    → Twilio BYOK / WebSocket
  Step 6: Testing Sandbox    → UI tests chat/voice in real-time
  Step 7: Go Live / Deploy   → POST /onboarding/deploy      → activates agent (demo mode returns mock number)
```

### Document Ingestion Flow

```
Tenant uploads URL or file via onboarding or knowledge page
        │
        ▼
FastAPI POST /api/ingestion/start
        │ Creates Document rows in PostgreSQL (status: "pending")
        │ Launches background task via ingestion_service.py
        │
        ▼
ingestion_service.py (FastAPI BackgroundTask)
        │
        ├── For URLs:
        │   ├── httpx fetches page HTML
        │   ├── trafilatura extracts article content
        │   └── BeautifulSoup fallback (if trafilatura returns nothing)
        │
        └── For Files (MinIO → local temp):
            ├── PDF / DOCX / PPTX / XLSX → Docling DocumentConverter
            ├── Scanned PDFs / Images     → PaddleOCR fallback
            └── Plain text files          → direct read
        │
        ▼
LangChain RecursiveCharacterTextSplitter
  (chunk_size=1000, chunk_overlap=200)
        │
        ▼
SentenceTransformer.encode() → float32 embeddings (384-dim)
        │
        ▼
ChromaDB collection: "tenant_{tenantId}"
  Metadata per chunk: { agentId, source, chunk_index, content_type }
        │
        ▼
Redis: job:{jobId} = "completed"  (progress tracking)
```

### Query / Chat Flow

```
User sends message in chat interface
        │
        ▼
Django proxy: fetch('/api/runner/chat', { message, agentId, sessionId })
        │ Adds x-tenant-id, x-user-id headers from session
        │
        ▼
FastAPI POST /api/runner/chat
  │ Header auth provides tenant context
  │ Loads agent from PostgreSQL (SQLAlchemy)
        │
        ▼
rag_service.assemble_context(tenant_id, agent_id, session_id)
  │
  ├─ Layer 1: GLOBAL_SAFETY_RULES (hardcoded constant)
  ├─ Layer 2: Tenant settings + policyRules (PostgreSQL)
  ├─ Layer 3: Brand voice + allowed/restricted topics (PostgreSQL)
  ├─ Layer 4: Agent config + template + persona (PostgreSQL)
  ├─ Layer 5: Session history from Redis (last 20 turns)
  └─ Few-shot: Approved RetrainingExamples from DB
        │
        ▼
rag_service.process_query(tenant_id, agent_id, query, assembled_context)
        │
        ├─ 1. Hybrid document retrieval
        │      ├── _semantic_search() → ChromaDB query
        │      │   (vector similarity, agentId filter, top ~7 chunks)
        │      └── _bm25_search() → Redis-backed BM25 scoring
        │          (keyword matching, top ~3 chunks)
        │
        ├─ 2. Combine, deduplicate, re-rank by relevance score
        │
        ├─ 3. apply_policy_scoring(docs, rules)
        │      (restrict=×0.05, require=×2.0, allow=×1.0)
        │      Rules from Tenant + Brand + Agent merged hierarchy
        │
        ├─ 4. Condense context — fit chunks into token budget
        │
        ├─ 5. build_system_prompt(assembled_context) → 7-section prompt:
        │      [1: Safety] [2: Tenant] [3: Brand] [4: Agent]
        │      [5: Few-shot] [6: Escalation] [7: Policy summary]
        │
        └─ 6. generate_response() → POST Groq API /chat/completions
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
Twilio → POST /api/voice/inbound/{agent_id} (FastAPI webhook)
        │
  ├─ 1. Look up agent by `agent_id`
  │     → SQLAlchemy query on Agent table
  │
  └─ 2. Return TwiML with <Gather> + <Say> greeting
        → speech input loops through `/api/voice/gather/{agent_id}`
        │
        ▼  (caller speaks)
        │
Twilio → POST /api/voice/gather/{agent_id}
        │
  ├─ 1. Extract speech from Twilio form payload (`SpeechResult`)
  ├─ 2. Run `rag_service.process_query()` using session key `call-{CallSid}`
  ├─ 3. Persist CallLog entry and trigger async post-call analysis task
  └─ 4. Return TwiML with assistant answer in <Say> and another <Gather>
        → continues as a conversational loop
        │
        ▼  (on hangup)
        │
Twilio → POST /api/voice/status/{agent_id}
        │
  └─ Log status transition for the call lifecycle
```

### WebSocket Browser Call Flow

```
User clicks "Call" button on embedded widget / dashboard
        │
        ▼
Widget opens WebSocket → connects to /api/voice/ws/{agent_id}
        │
        ▼
Server: voice_ws.py handles WebSocket connection
  │ Validates agent exists in DB (SQLAlchemy)
  │ Resolves tenant Groq key (tenant key first, platform fallback)
  └ Accepts JSON messages: config, audio chunks, end-of-utterance
        │
        ▼  (user speaks — browser records audio via MediaRecorder)
        │
Client sends binary audio frame via WebSocket
        │
        ▼
Server: voice_ws.py —
  `_transcribe_local()` (faster-whisper) OR `_transcribe_groq()`
  → `process_query()` (full RAG pipeline)
  → returns transcript + text response
  → synthesises response audio via Edge (primary) with Kokoro/Piper fallback
  → sends transcript, response, and audio data URI over WebSocket
        │
        ▼  (loop continues until disconnect)
        │
Client closes WebSocket or disconnects
  → Server saves CallLog entries for each exchange
```

**Embeddable widget:** Any website can embed:
```html
<script src="https://your-domain.com/api/widget/AGENT_ID/embed.js"></script>
```
This creates a floating call button that connects via WebSocket.

### Retraining / Continuous Improvement Flow

```
Bad call happens → user/admin flags it
  POST /api/logs/{id}/flag  → CallLog.flaggedForRetraining = True
        │
        ▼
Nightly scheduler (02:00, APScheduler cron)
  scheduler.nightly_retraining_pipeline()
        │
        ├─ 1. extract_flagged_call_logs():
        │      Query: CallLog where flaggedForRetraining=True, retrained=False
        │      Parse transcript → extract user query + bad response pairs
        │      Create RetrainingExample records (status: "pending")
        │      Mark CallLog.retrained = True
        │
        └─ 2. retrain_approved_examples():
               Embed approved examples into ChromaDB for retrieval
        │
        ▼
Admin reviews in /dashboard/retraining page
  │ Filters by status, agent
  │ Edits ideal response text
  │ Clicks Approve or Reject
  │   PATCH /api/retraining/{id}
        │
        ▼
On next query, assemble_context() loads approved examples:
  → SQLAlchemy: RetrainingExample where status IN ['approved', 'in_prompt']
  → Up to 10 most recent, by approvedAt desc
  → Injected as Section 5 "LEARNED EXAMPLES" in build_system_prompt()
  → Agent immediately improves for similar queries (no fine-tuning)
```

---

## Voice Pipeline Architecture

VoiceFlow supports **four distinct voice paths**, each optimized for different use cases. All paths share the same RAG engine (`rag_service.py`) for response generation.

### Voice Path Overview

| Path | Protocol | Duplex | Latency | Use Case |
|---|---|---|---|---|
| **Twilio Gather** | HTTP (TwiML) | Half | ~3-5s | Simple IVR replacement, no WebSocket needed |
| **Twilio Media Streams** | WebSocket (μ-law) | Full | ~1-2s | Production calls with barge-in |
| **Browser Live** | WebSocket (PCM) | Full | ~1-2s | Gemini-live-style browser voice |
| **Browser Simple** | WebSocket (binary) | Half | ~3-5s | Legacy fallback, batch processing |

### Routing Diagram

```
                    ┌───────────────────────────────────┐
                    │    voice_inbound_router.py         │
                    │   POST /inbound/{agent_id}         │
                    └──────┬──────────────┬──────────────┘
                           │              │
              telephony_provider     telephony_provider
              == "twilio-gather"     == "twilio-stream"
                           │              │
            ┌──────────────▼──┐    ┌──────▼───────────────┐
            │ voice_twilio_   │    │ voice_twilio_stream.py│
            │ gather.py       │    │  WS /media-stream/    │
            │ <Gather> TwiML  │    │  <Connect><Stream>    │
            └────────┬────────┘    └───────┬──────────────┘
                     │                     │
                     ▼                     ▼
             process_query()      streaming orchestration
             (non-streaming)      STT → RAG → TTS (streaming)
                                           │
          ┌────────────────────────────────┼────────────────────┐
          ▼                                ▼                    ▼
   ┌─────────────┐              ┌──────────────┐     ┌─────────────────┐
   │ stt_service  │              │ rag_service   │     │  tts_router     │
   │ faster-      │              │ process_query │     │  kokoro/piper/  │
   │ whisper/vosk │              │ _streaming    │     │  edge/orpheus   │
   │ /groq        │              └──────────────┘     └─────────────────┘
   └─────────────┘

   Browser paths (no Twilio):
   ┌─────────────────┐    ┌──────────────────┐
   │ voice_ws.py      │    │ voice_live.py     │
   │ WS /ws/{id}      │    │ WS /live/{id}     │
   │ half-duplex      │    │ full-duplex       │
   │ batch processing │    │ Gemini-live-style │
   │ (legacy)         │    │ VAD + barge-in    │
   └─────────────────┘    └──────────────────┘
```

### Path 1 — Twilio TwiML Gather Loop (Half-Duplex)

```mermaid
sequenceDiagram
  participant C as Caller
  participant T as Twilio
  participant V as VoiceFlow API
  participant R as RAG Engine
  C->>T: Dials phone number
  T->>V: POST /api/voice/inbound/{agent_id}
  V-->>T: TwiML <Gather input="dtmf speech"><Say>Greeting</Say></Gather>
  T-->>C: Plays greeting, listens for speech
  C->>T: Speaks
  T->>V: POST /api/voice/gather/{agent_id} (SpeechResult)
  V->>R: process_query(transcript, session)
  R-->>V: AI response text
  V-->>T: TwiML <Say>Response</Say><Gather>...
  T-->>C: Reads response, waits for next input
  Note over T,V: Loop continues until hangup
  T->>V: POST /api/voice/status/{agent_id} (completed)
  V->>V: Save CallLog + async post-call analysis
```

**How it works:** Twilio handles STT. Each turn is a full HTTP request/response cycle. LLM output is sanitized for TwiML injection before being placed in `<Say>` tags.

### Path 2 — Twilio Media Streams (Full-Duplex, Production)

```mermaid
sequenceDiagram
  participant C as Caller
  participant T as Twilio
  participant WS as WebSocket Handler
  participant STT as STT Service
  participant RAG as RAG Engine
  participant TTS as TTS Router
  C->>T: Dials phone number
  T->>WS: POST /inbound → TwiML <Connect><Stream>
  T->>WS: WebSocket opened (μ-law 8kHz)
  loop Real-time audio
    T->>WS: media event (base64 μ-law)
    WS->>WS: Decode → PCM 16kHz → VAD (RMS energy)
    Note over WS: Silence detected (24 frames / ~480ms)
    WS->>STT: transcribe_bytes(pcm_buffer)
    STT-->>WS: transcript
    WS->>RAG: process_query_streaming()
    loop Token streaming
      RAG-->>WS: token
      WS->>TTS: synthesize_streaming(tokens)
      TTS-->>WS: WAV chunk
      WS->>WS: WAV → μ-law 8kHz → 160-byte frames
      WS->>T: media event (20ms pacing)
    end
    Note over WS: During playback: monitor for barge-in (RMS > 300)
    WS->>T: clear event (if barge-in detected)
  end
```

**Key features:** Server-side VAD (Voice Activity Detection) using RMS energy thresholds, barge-in/interruption detection, streaming TTS with sentence-boundary chunking, 20ms frame pacing for smooth audio playback.

### Path 3 — Browser Live Voice (Gemini-Live Style)

```mermaid
sequenceDiagram
  participant B as Browser (MediaRecorder)
  participant WS as /api/voice/live/{agent_id}
  participant STT as faster-whisper
  participant RAG as RAG Streaming
  participant TTS as TTS Router
  B->>WS: WebSocket connect + JWT auth
  WS-->>B: {"type":"state","state":"listening"}
  loop Full-duplex voice
    B->>WS: {"type":"audio","data":"base64 PCM"}
    WS->>WS: Decode → RMS check → buffer
    Note over WS: Silence detected (20 frames / ~400ms)
    WS-->>B: {"type":"state","state":"thinking"}
    WS->>STT: transcribe_bytes(buffer)
    STT-->>WS: transcript
    WS-->>B: {"type":"transcript","text":"..."}
    WS->>RAG: process_query_streaming()
    WS-->>B: {"type":"state","state":"speaking"}
    loop Token → TTS → Audio
      RAG-->>WS: token
      WS-->>B: {"type":"response","text":"token"}
      WS->>TTS: synthesize(sentence)
      TTS-->>WS: WAV bytes
      WS-->>B: {"type":"audio","data":"base64 WAV"}
    end
    WS-->>B: {"type":"audio_end"}
    Note over B,WS: Barge-in: if user speaks during<br/>playback with RMS > 200 → interrupt
  end
```

**Protocol messages:**
| Direction | Type | Payload |
|---|---|---|
| Client → Server | `audio` | base64 PCM 16kHz mono |
| Client → Server | `config` | Voice ID selection |
| Client → Server | `interrupt` | Explicit barge-in |
| Server → Client | `state` | `listening` / `thinking` / `speaking` |
| Server → Client | `transcript` | STT result |
| Server → Client | `response` | LLM token |
| Server → Client | `audio` | base64 WAV chunk |
| Server → Client | `audio_end` | TTS complete |

### Outbound Campaign Call Flow

```mermaid
sequenceDiagram
  participant A as Admin UI
  participant API as Campaign API
  participant Q as Redis Queue
  participant W as Campaign Worker
  participant CS as Compliance Service
  participant TW as Twilio REST API
  participant AG as Voice Agent
  A->>API: POST /api/campaigns (create draft)
  A->>API: POST /api/campaigns/{id}/contacts/upload (CSV)
  A->>API: POST /api/campaigns/{id}/start
  API->>Q: Push contact IDs to Redis list
  API->>W: Launch campaign worker (async)
  loop For each contact
    W->>Q: Pop next contact ID
    W->>CS: validate_before_dial(phone)
    CS-->>W: (allowed, reason)
    alt DND / outside hours / max retries
      W->>W: Skip contact, update status
    else Allowed
      W->>TW: Create call with AMD enabled
      TW-->>W: Call SID
      TW->>AG: POST /api/voice/outbound/{agent_id}
      AG->>AG: Check AnsweredBy (human/machine/fax)
      alt Human answered
        AG-->>TW: TwiML <Connect><Stream> with contact variables
        Note over AG: Full voice pipeline runs<br/>(same as inbound)
      else Machine / Fax
        AG-->>TW: Hangup (or voicemail message)
      end
      TW->>API: POST /api/campaigns/{id}/amd-callback
      API->>API: Update contact status + campaign stats
    end
    W->>W: sleep(1s) rate throttle
  end
  W->>API: Mark campaign completed
  W->>W: Dispatch webhook: campaign.finished
```

---

## RAG Engine Deep Dive

The RAG engine lives in `rag_service.py` (~1200 lines) and is the central intelligence of the platform. Every query — chat, voice, widget, API — goes through this pipeline.

### 5-Layer Hierarchical Context Assembly

```
┌─────────────────────────────────────────────────────────────────┐
│                    assemble_context()                            │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Layer 1: GLOBAL SAFETY RULES (hardcoded constant)       │    │
│  │   • No impersonation, no hallucination                  │    │
│  │   • No prompt leakage, privacy protection               │    │
│  │   • Language matching, off-topic handling                │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Layer 2: TENANT (from PostgreSQL → Tenant table)        │    │
│  │   • Organization name, industry, domain                 │    │
│  │   • Tenant-wide policyRules                             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Layer 3: BRAND (from PostgreSQL → Brand table)          │    │
│  │   • Brand voice and tone                                │    │
│  │   • Allowed topics, restricted topics                   │    │
│  │   • Brand-level policyRules                             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Layer 4: AGENT (from PostgreSQL → Agent + Config)       │    │
│  │   • Persona name, role, personality traits              │    │
│  │   • Custom instructions, behavior rules                 │    │
│  │   • Escalation triggers and rules                       │    │
│  │   • Knowledge boundaries, confidence threshold          │    │
│  │   • LLM model selection (from llmPreferences)           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Layer 5: SESSION (from Redis, 24h TTL)                  │    │
│  │   • Last 20 conversation turns (user + assistant)       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Layer 6: CONTACT VARIABLES (optional, outbound only)    │    │
│  │   • Caller name, order ID, custom CSV fields            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ FEW-SHOT EXAMPLES (from PostgreSQL → RetrainingExample) │    │
│  │   • Up to 10 approved examples, most recent first       │    │
│  │   • Format: "User: {query}\nIdeal Response: {response}" │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  All policies from Tenant + Brand + Agent are MERGED into a    │
│  single mergedPolicies list for retrieval scoring.             │
└─────────────────────────────────────────────────────────────────┘
```

### Hybrid Search — Semantic + BM25 with Reciprocal Rank Fusion

```mermaid
flowchart TD
    Q[User Query] --> S[Semantic Search]
    Q --> B[BM25 Keyword Search]

    S --> |ChromaDB vector similarity<br/>collection: tenant_{id}<br/>filter: agentId metadata<br/>top-K chunks| SR[Semantic Results<br/>score = 1.0 - distance]

    B --> |Redis-stored BM25 index<br/>BM25Okapi scoring<br/>tokenized corpus| BR[BM25 Results<br/>score = BM25 relevance]

    SR --> RRF[Reciprocal Rank Fusion<br/>k=60]
    BR --> RRF

    RRF --> |Score per doc:<br/>Σ 1/(k + rank + 1)<br/>across both lists| DEDUP[Deduplicate by<br/>content hash]

    DEDUP --> PS[Policy Scoring]

    PS --> |restrict = ×0.05<br/>require = ×2.0<br/>allow = ×1.0| RANKED[Final Ranked Chunks]

    RANKED --> PROMPT[Inject into Prompt]
```

### Policy Scoring Rules

After retrieval, each chunk's score is modified based on merged tenant/brand/agent policies:

| Rule Action | Score Multiplier | Effect |
|---|---|---|
| `restrict` | ×0.05 | Nearly suppressed — chunk almost never reaches the prompt |
| `require` | ×2.0 | Boosted — chunk ranked higher |
| `allow` | ×1.0 | Unchanged |

**Matching logic** — a policy rule matches a chunk when:
| Rule Type | Matches On |
|---|---|
| `topic` | Target string found in chunk content (case-insensitive) |
| `documentSource` | Target found in chunk metadata `source` field |
| `documentTag` | Target found in chunk metadata `tags` list |

### Dynamic 8-Section Prompt Assembly

`build_system_prompt()` constructs the final system prompt from the assembled context:

| Section | Tag | Content Source |
|---|---|---|
| 1 | `[SAFETY RULES]` | Hardcoded global safety constant |
| 2 | `[ORGANIZATION]` | Tenant name + industry |
| 3 | `[BRAND GUIDELINES]` | Brand voice, allowed topics, restricted topics ("NEVER discuss: ...") |
| 4 | `[AGENT]` | Agent name, role, template prompt (with `{{placeholder}}` replacement), persona, custom instructions, behavior rules, knowledge boundaries |
| 5 | `[LEARNED EXAMPLES]` | Few-shot examples from approved retraining ("User: ...\nIdeal Response: ...") |
| 6 | `[ESCALATION]` | Escalation triggers + rules (condition → action) |
| 7 | `[ACTIVE POLICIES]` | Human-readable summary of restrict/require policies |
| 8 | `[CONTACT CONTEXT]` | Outbound call personalization ("You are speaking with {name}. Their order ID is {value}.") |

Sections are joined with `\n\n---\n\n` delimiters.

### Full Query Pipeline

```mermaid
flowchart TD
    INPUT[User Query] --> AC[assemble_context<br/>5-layer hierarchy from DB + Redis]
    AC --> QD[query_documents<br/>Concurrent: ChromaDB + BM25]
    QD --> PS[apply_policy_scoring<br/>restrict/require/allow multipliers]
    PS --> BSP[build_system_prompt<br/>8-section dynamic prompt]
    BSP --> LLM{Streaming?}
    LLM -->|Non-streaming| GR[generate_response<br/>Groq API, retry ×4]
    LLM -->|Streaming| SC[LLMClient.stream_completion<br/>Multi-provider SSE]
    GR --> SAVE[save_conversation_history<br/>Redis, 24h TTL, 20 turns]
    SC --> FC{Function call<br/>detected?}
    FC -->|Yes| TOOL[VoiceToolExecutor.execute<br/>→ inject result → re-stream]
    FC -->|No| SAVE
    TOOL --> SAVE
    SAVE --> OUT[Response + Sources]
```

---

## LLM & AI Architecture

### Multi-Provider LLM Support

The platform supports four LLM providers, configurable per-agent via `agent.llmPreferences`:

| Provider | Streaming | Non-Streaming | SDK / Method | Notes |
|---|---|---|---|---|
| **Groq** | Yes (SSE) | Yes (retry ×4) | Custom httpx SSE parsing | Primary provider. Per-tenant BYOK or platform fallback key. |
| **OpenAI** | Yes (SDK) | No | `openai.AsyncOpenAI` | Standard OpenAI-compatible API. |
| **Gemini** | Yes (SDK bridge) | No | `google.generativeai` via `run_in_executor` + `asyncio.Queue` | Converts OpenAI message format → Gemini format. |
| **Ollama** | Yes (SDK) | No | `ollama.AsyncClient` | Local self-hosted models. No API key required. |

### Per-Tenant Key Resolution

```
1. Check agent.llmPreferences.llmProvider → determines provider
2. Look up encrypted API key from tenant.settings (groqApiKey / openaiApiKey / geminiApiKey)
3. Decrypt via credentials.decrypt_safe (AES-256-GCM)
4. If tenant key missing → fall back to platform-level key from env vars
5. Ollama → no key needed (local)
```

### Function Calling / Voice Tools

During streaming voice responses, the system supports **live function calling**:

1. If agent has `customFunctions` defined, a non-streaming pre-check runs first
2. LLM output is scanned for tool-call JSON: `{"tool": "<name>", "arguments": {...}}`
3. If detected → filler audio plays ("Let me check that for you...") → tool executes via HTTP → result injected as follow-up context → final response streams

**Built-in tool registry:**
| Tool | Action | Status |
|---|---|---|
| `book_appointment` | Schedule via calendar API | Scaffold |
| `lookup_crm` | Customer lookup by phone | Scaffold |
| `send_sms` | Send SMS via Twilio | Scaffold |
| `capture_dtmf` | Collect DTMF digits | Scaffold |
| `update_lead` | Update CRM lead status | Scaffold |
| `transfer_call` | Warm transfer to human | Scaffold |

### TTS Engine Routing

```
tts_router.synthesize(text, engine, voice_id, speed)
        │
        ├── engine == "kokoro"  → HTTP POST to Kokoro container (port 8880)
        │                         OpenAI-compatible /v1/audio/speech
        │
        ├── engine == "piper"   → HTTP POST to Piper container (port 8890)
        │                         /v1/audio/speech with fallback to /synthesize
        │
        ├── engine == "orpheus" → LLM rewrite (adds <laugh>, <sigh> emotion tags)
        │                         → then delegates to Kokoro for synthesis
        │
        └── engine == "edge"    → Microsoft Edge TTS cloud API
                                  300+ voices, no local container needed
```

**Streaming TTS:** `synthesize_streaming()` buffers incoming token stream and flushes on sentence boundaries (`.!?` followed by whitespace) or every ~64 tokens. Each flush produces a full WAV chunk — this is chunked batch synthesis, not true streaming TTS.

### STT Engine Hierarchy

```
transcribe_bytes(audio, engine, groq_key)
        │
        ├── engine == "groq" && key exists → Groq Whisper API (whisper-large-v3-turbo)
        │
        └── else → try faster-whisper (local, tiny model, int8)
                    → try Vosk (local, English small model)
                    → try Groq API (if key available)
                    → return "" (silent failure)
```

**Vosk streaming:** `create_vosk_recognizer()` + `transcribe_stream_chunk()` provide stateful streaming STT using Vosk's `KaldiRecognizer` — only Vosk supports per-chunk streaming; faster-whisper is batch-only.

---

## Running the Project

### Prerequisites

- Docker Desktop (for infrastructure services)
- Python 3.11+ (3.12 recommended)
- `make` (via Chocolatey: `choco install make`)
- **CUDA/CPU PyTorch runtime** — installed by `make install` (used by local Kokoro TTS path)
- **SoX (Sound eXchange)** — recommended for local audio tooling
  - Download from: [http://sox.sourceforge.net/](http://sox.sourceforge.net/)
  - Or via Chocolatey: `choco install sox`
- Groq API key ([console.groq.com](https://console.groq.com))
- (Optional) Twilio account for phone calls — each tenant brings their own

### Step 1 — One-Time Setup (Recommended)

```bash
cd python
make init
```

`make init` runs: venv creation, dependency install, `.env` bootstrap, Docker services, migrations, and template seeding.

Dependency management is pyproject-based: `uv sync` reads `pyproject.toml` (and `uv.lock` once created) as the single source of truth.

### Step 2 — Start the Full Stack

```bash
make all
```

This starts Docker services and launches FastAPI + Django in separate windows.

### Alternative Manual Startup (if you want granular control)

```bash
cd python
make venv
make install
make env
make docker
make migrate
make seed
make backend-bg
make frontend-bg
```

### Startup Sequence Diagram

```mermaid
flowchart TD
    A[cd python] --> B[make init]
    B --> C[make all]
    C --> D[FastAPI :8040]
    C --> E[Django :8050]
    C --> F[Postgres :8010]
    C --> G[Redis :8020]
    C --> H[ChromaDB :8030]
    C --> I[MinIO :9020/:8070]
```

### Step 3 — Access the Application

| Interface | URL |
|---|---|
| Django Frontend | http://localhost:8050 |
| FastAPI Backend | http://localhost:8040 |
| FastAPI Docs | http://localhost:8040/docs |
| OpenAPI JSON | http://localhost:8040/openapi.json |
| PostgreSQL | localhost:8010 |
| Redis | localhost:8020 |
| ChromaDB | http://localhost:8030 |
| MinIO Console | http://localhost:8070 (`minioadmin` / `minioadmin`) |
| MinIO API | localhost:9020 |

### Other Useful Commands

```bash
make help               # Show all commands
make lock               # Generate/update uv.lock from pyproject.toml
make status             # Show port/container status
make restart-backend    # Restart FastAPI
make restart-frontend   # Restart Django
make stop               # Stop app + docker services
make nuke               # Wipe all data + restart fresh
make logs               # Tail Docker logs
make logs-postgres      # Tail Postgres logs
```

### (Optional) Voice Calls via Twilio

1. **Expose your local backend publicly:**
```bash
ngrok http 8040
```

2. **Each tenant enters their own Twilio credentials** in the Settings → Integrations page or during onboarding Step 6.

3. **On deploy**, the current onboarding backend runs in demo mode and returns a mock number (`+1-555-DEMO`).

---

## Environment Variables

Primary runtime configuration is loaded from `python/.env` (created by `make env` from `python/.env.example`).

### Shared Runtime (`python/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | No | `postgresql+asyncpg://vf_admin:vf_secure_2025!@localhost:8010/voiceflow_prod` | PostgreSQL connection string |
| `DB_NAME` | No | `voiceflow_prod` | Django/Postgres database name |
| `DB_USER` | No | `vf_admin` | Django/Postgres user |
| `DB_PASSWORD` | No | `vf_secure_2025!` | Django/Postgres password |
| `DB_HOST` | No | `localhost` | Django/Postgres host |
| `DB_PORT` | No | `8010` | Django/Postgres port |
| `REDIS_HOST` | No | `localhost` | Redis host |
| `REDIS_PORT` | No | `8020` | Redis port |
| `CHROMA_HOST` | No | `localhost` | ChromaDB host |
| `CHROMA_PORT` | No | `8030` | ChromaDB port |
| `BACKEND_API_URL` | No | `http://localhost:8040` | FastAPI URL used by Django frontend |
| `GROQ_API_KEY` | No* | — | Platform fallback LLM key. Optional if tenants provide their own via Settings. |
| `MINIO_ENDPOINT` | No | `localhost:9020` | MinIO API endpoint |
| `MINIO_ACCESS_KEY` | No | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | No | `minioadmin` | MinIO secret key |
| `MINIO_BUCKET` | No | `voiceflow-tts` | Bucket used for generated audio/files |
| `DJANGO_SECRET_KEY` | No | dev default in code | Django secret key |
| `DJANGO_DEBUG` | No | `True` | Django debug mode |
| `DJANGO_ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Django allowed hosts |
| `JWT_SECRET` | No | `dev-secret` | JWT signing secret for backend auth token issuance |
| `PORT` | No | `8040` | FastAPI port |
| `TWILIO_ACCOUNT_SID` | No | — | Fallback Twilio SID |
| `TWILIO_AUTH_TOKEN` | No | — | Fallback Twilio token |
| `TWILIO_WEBHOOK_BASE_URL` | No | — | Public base URL for Twilio callbacks (for local dev usually ngrok URL) |
| `CREDENTIALS_ENCRYPTION_KEY` | No* | — | 64-char hex key for AES-256-GCM encrypted credential storage |

*No separate frontend/backend env files are required for local startup. Backend also reads optional local `.env` in `python/backend/`; frontend reads from `python/.env` first.*

---

## Services & Ports

| Service | Technology | Port | Role |
|---|---|---|---|
| Django Frontend | Django 6.0.4 + HTMX + Alpine.js | 8050 | UI, dashboard, onboarding |
| FastAPI Backend | Python FastAPI | 8040 | Auth, agents, RAG, voice, API |
| PostgreSQL | Docker | 8010 | Primary relational data |
| Redis | Docker | 8020 | Conversation cache, rate limits, BM25 |
| ChromaDB | Docker | 8030 | Vector embeddings (per-tenant collections) |
| MinIO API | Docker | 9020 | File storage (S3-compatible) |
| MinIO Console | Docker | 8070 | MinIO web admin |

---

## Service Inventory

The FastAPI backend contains **13 service modules** in `python/backend/app/services/`:

| Service | File | Lines | What It Does |
|---|---|---|---|
| **RAG Engine** | `rag_service.py` | ~1200 | 5-layer context injection, hybrid search (semantic + BM25 + RRF), policy scoring, 8-section prompt assembly, multi-LLM generation (streaming + non-streaming), conversation history management |
| **Document Ingestion** | `ingestion_service.py` | ~820 | Docling (PDF/DOCX/PPTX/XLSX), PaddleOCR (scanned docs), Trafilatura + BeautifulSoup (URLs), SentenceTransformer embedding, ChromaDB storage, BM25 index building in Redis |
| **TTS Router** | `tts_router.py` | ~135 | Multi-engine text-to-speech dispatch: Kokoro (local CPU), Piper (local ONNX), Edge TTS (cloud), Orpheus (emotion-tagged). Streaming TTS with sentence-boundary chunking. |
| **STT Service** | `stt_service.py` | ~270 | Multi-engine speech-to-text: faster-whisper (local, int8), Vosk (local, streaming), Groq Whisper API (cloud). Auto-downloads Vosk model on first run. |
| **Campaign Worker** | `campaign_worker.py` | ~430 | Outbound campaign execution: Redis queue processing, per-tenant Twilio credentials, AMD handling, voicemail detection, rate throttling, campaign lifecycle management |
| **Compliance Service** | `compliance_service.py` | ~128 | Pre-dial compliance checks: DND registry lookup, calling hours enforcement (timezone-aware), retry limit enforcement |
| **Webhook Service** | `webhook_service.py` | ~125 | HMAC-SHA256 signed event dispatch to external URLs. 3 retries with exponential backoff. Events: `call.completed`, `campaign.finished`, `escalation.triggered`, `retraining.flagged` |
| **Flow Engine** | `flow_engine.py` | ~250 | Visual conversation graph walker: executes node-based flows (greeting, knowledge, condition, api_call, human_transfer, end). Supports variable interpolation and conditional branching. |
| **Voice Tools** | `voice_tools.py` | ~175 | Live function calling during voice conversations: tool registry, HTTP-based tool execution with timeout, filler audio synthesis during tool execution |
| **Credentials** | `credentials.py` | ~87 | AES-256-GCM encryption/decryption for per-tenant API keys (Twilio, Groq, OpenAI). 96-bit random nonce. Graceful migration from plaintext via `decrypt_safe()`. |
| **Scheduler** | `scheduler.py` | ~161 | APScheduler nightly cron (02:00): extracts Q/A pairs from flagged calls, embeds approved retraining examples into ChromaDB, creates platform notifications |
| **Call State** | `call_state.py` | ~110 | Redis-backed call state machine (IDLE → LISTENING → THINKING → SPEAKING) with 2h TTL. Enforces valid transitions. Barge-in: any state → LISTENING always allowed. |
| **Streaming Orchestrator** | `streaming_orchestrator.py` | ~330 | Reusable real-time voice pipeline: STT → RAG → TTS with PCM energy-based barge-in detection, call state machine integration, μ-law frame pacing |

### Route Files (30 files, ~142 endpoints)

| Route File | Prefix | Endpoints | Description |
|---|---|---|---|
| `auth.py` | `/auth` | 3 | Login, signup, user sync |
| `onboarding.py` | `/onboarding` | 16 | 7-step wizard endpoints |
| `agents.py` | `/api/agents` | 9 | Agent CRUD + activate/pause + WhatsApp config |
| `documents.py` | `/api/documents` | 5 | Document CRUD + file upload |
| `rag.py` | `/api/rag` | 3 | Direct RAG query + conversation history |
| `runner.py` | `/api/runner` | 3 | Chat + audio endpoints |
| `ingestion.py` | `/api/ingestion` | 4 | Trigger ingestion + poll status |
| `templates.py` | `/api/templates` | 4 | Agent template CRUD |
| `analytics.py` | `/analytics` | 6 | Overview, realtime, charts, agent comparison |
| `logs.py` | `/api/logs` | 3 | Call log listing + rating + flagging |
| `brands.py` | `/api/brands` | 5 | Brand CRUD (voice, topics, policies) |
| `settings.py` | `/api/settings` | 8 | Twilio/Groq credential management |
| `users.py` | `/api/users` | 3 | User management |
| `retraining.py` | `/api/retraining` | 6 | Retraining queue + manual trigger |
| `tts.py` | `/api/tts` | 5 | Voice presets, preview, synthesis, cloning |
| `widget.py` | `/api/widget` | 6 | Embeddable widget config + session API |
| `campaigns.py` | `/api/campaigns` | 7 | Campaign CRUD + CSV upload + start/pause + AMD callback |
| `webhooks.py` | `/api/webhooks` | 5 | Webhook endpoint CRUD + test dispatch |
| `ab_testing.py` | `/api/ab` | 5 | Experiment CRUD + variant stats + record outcome |
| `dnd.py` | `/api/dnd` | 4 | DND registry CRUD + bulk import |
| `whatsapp.py` | `/api/whatsapp` | 1 | WhatsApp inbound webhook handler |
| `voice_inbound_router.py` | `/api/voice` | 1 | Inbound call dispatcher (gather vs stream) |
| `voice_twilio_gather.py` | `/api/voice` | 4 | TwiML Gather loop + post-call analysis |
| `voice_twilio_stream.py` | `/api/voice` | 5 | Twilio Media Streams WS + outbound + transfer |
| `voice_live.py` | `/api/voice` | 1 | Gemini-live-style browser voice WS |
| `voice_ws.py` | `/api/voice` | 1 | Legacy browser voice WS |
| `admin.py` | `/admin` | 7 | Pipeline CRUD + trigger |
| `platform.py` | `/api` | 5 | Audit, notifications, health |
| `data_explorer.py` | `/api/data-explorer` | 4 | Postgres/ChromaDB/Redis viewer |

---

## API Reference

All backend endpoints use header-based tenant context.

**Authentication headers:**
```
x-tenant-id: <tenant_uuid>
x-user-id: <user_uuid>
```

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/login` | Email-based API login |
| POST | `/auth/signup` | New account signup (email-based API flow) |
| POST | `/auth/clerk_sync` | Sync external user to local DB (legacy compat) |

### Agents
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/agents/` | List agents for authenticated tenant |
| POST | `/api/agents/` | Create new agent |
| GET | `/api/agents/{agent_id}` | Get agent with documents |
| PUT | `/api/agents/{agent_id}` | Update agent configuration |
| DELETE | `/api/agents/{agent_id}` | Delete agent and documents |
| POST | `/api/agents/{agent_id}/activate` | Activate agent |
| POST | `/api/agents/{agent_id}/pause` | Pause agent |

### Documents
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/documents/` | List documents (supports filtering by agent) |
| GET | `/api/documents/{doc_id}` | Get document details |
| POST | `/api/documents/upload` | Upload file to MinIO + trigger ingestion |
| POST | `/api/documents/` | Create document metadata entry |
| PUT | `/api/documents/{doc_id}` | Update document metadata/status |
| DELETE | `/api/documents/{doc_id}` | Remove document and vectors |

### RAG / Chat
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/rag/query` | Direct RAG query with agentId |
| GET | `/api/rag/conversation/{session_id}` | Get conversation history |
| DELETE | `/api/rag/conversation/{session_id}` | Delete conversation history |
| POST | `/api/runner/chat` | Chat endpoint (used by frontend) |
| POST | `/api/runner/audio` | Voice audio upload for transcription + RAG |
| GET | `/api/runner/agent/{agent_id}` | Fetch runner-oriented agent metadata |

### Ingestion
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/ingestion/start` | Trigger URL/S3 ingestion job |
| POST | `/api/ingestion/company` | Trigger company-knowledge ingestion workflow |
| GET | `/api/ingestion/status/{job_id}` | Poll job progress (0-100%) |
| GET | `/api/ingestion/jobs` | List recent ingestion jobs |

### Onboarding
| Method | Endpoint | Description |
|---|---|---|
| GET | `/onboarding/company-search` | Search/fetch company profile candidates |
| GET | `/onboarding/company` | Get current company profile |
| POST | `/onboarding/company` | Save company profile |
| GET | `/onboarding/scrape-status/{job_id}` | Get company scrape progress |
| GET | `/onboarding/company-knowledge` | Get scraped company knowledge chunks |
| DELETE | `/onboarding/company-knowledge/{chunk_id}` | Remove scraped company chunk |
| POST | `/onboarding/agent` | Create initial agent |
| POST | `/onboarding/knowledge` | Upload knowledge (proxied to FastAPI) |
| POST | `/onboarding/voice` | Save voice config |
| POST | `/onboarding/channels` | Save channel config |
| POST | `/onboarding/agent-config` | Save full agent configuration |
| POST | `/onboarding/deploy` | Deploy agent to phone number |
| GET | `/onboarding/status` | Get onboarding status |
| GET/POST/DELETE | `/onboarding/progress` | Resume / save / clear onboarding state |

### Twilio / Voice
| Method | Endpoint | Description |
|---|---|---|
| GET | `/twilio/numbers` | List provisioned phone numbers for tenant |
| POST | `/api/voice/inbound/{agent_id}` | Inbound call webhook (TwiML Gather) |
| POST | `/api/voice/gather/{agent_id}` | Twilio speech gather callback |
| POST | `/api/voice/status/{agent_id}` | Call status callback |
| GET | `/api/voice/calls/{agent_id}` | List recent voice call logs for agent |
| WS | `/api/voice/ws/{agent_id}` | Browser voice websocket endpoint |

### Settings
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/settings` | Get tenant settings |
| PUT | `/api/settings` | Update tenant settings |
| POST | `/api/settings/twilio` | Save & verify Twilio credentials (encrypted) |
| GET | `/api/settings/twilio` | Get credential status (never returns auth token) |
| DELETE | `/api/settings/twilio` | Remove Twilio credentials |

### TTS (Text-to-Speech — Edge + Kokoro)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/tts/preset-voices` | List Edge voices + local Kokoro/Piper options |
| POST | `/api/tts/preview` | Generate voice preview audio for a given voiceId |
| POST | `/api/tts/synthesise` | Generate speech audio for text + voiceId |
| POST | `/api/tts/clone-voice` | Upload reference audio and generate 3 clone confirmation samples |
| POST | `/api/tts/clone-preview` | Generate cloned voice audio for custom text |

### Analytics (real SQLAlchemy queries)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/analytics/overview` | Usage metrics overview (real CallLog aggregates) |
| GET | `/analytics/calls` | Call log history with filtering |
| GET | `/analytics/realtime` | Live metrics |
| GET | `/analytics/metrics-chart` | Time-series data |
| GET | `/analytics/agent-comparison` | Side-by-side agent stats |
| GET | `/analytics/usage` | Aggregate usage counters |

### Brands
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/brands/` | List brands for tenant |
| POST | `/api/brands/` | Create brand with voice/topic/policy config |
| GET | `/api/brands/{brand_id}` | Get brand details |
| PUT | `/api/brands/{brand_id}` | Update brand configuration |
| DELETE | `/api/brands/{brand_id}` | Delete brand |

### Groq Settings (BYOK)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/settings/groq/models` | List available Groq production models (id, name, speed, context window) |
| POST | `/api/settings/groq` | Save & verify tenant Groq API key (validates against live Groq API, encrypts with AES-256-GCM) |
| GET | `/api/settings/groq` | Get Groq key status (masked key, verified flag, usingPlatformKey boolean) |
| DELETE | `/api/settings/groq` | Remove tenant Groq API key (reverts to platform default) |

### Call Logs
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/logs/` | List call logs with pagination |
| PATCH | `/api/logs/{log_id}/rating` | Rate call (`1` or `-1`) with optional notes |
| POST | `/api/logs/{log_id}/flag` | Flag call for retraining |

### Retraining
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/retraining/` | List retraining queue (filter by status, agentId) |
| GET | `/api/retraining/stats` | Dashboard counts: pending, approved, rejected, flaggedNotProcessed |
| PATCH | `/api/retraining/{example_id}` | Edit ideal response and/or change status (pending/approved/rejected) |
| DELETE | `/api/retraining/{example_id}` | Remove a retraining example |
| POST | `/api/retraining/process` | Manually trigger flagged call processing (immediate, no wait for nightly cron) |
| POST | `/api/retraining/process-now` | Alias for `/process` |

### Widget (public — no auth)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/widget/{agent_id}` | Widget config JSON (name, greeting, colors) |
| GET | `/api/widget/{agent_id}/embed.js` | Embeddable JavaScript widget |
| POST | `/api/widget/{agent_id}/sessions` | Create a new conversation session (returns sessionId) |
| POST | `/api/widget/{agent_id}/sessions/{session_id}/message` | Send a message and get AI response (full RAG pipeline) |
| GET | `/api/widget/{agent_id}/sessions/{session_id}` | Get session transcript |
| DELETE | `/api/widget/{agent_id}/sessions/{session_id}` | End session and persist as CallLog |

### Admin — Pipeline Management
| Method | Endpoint | Description |
|---|---|---|
| POST | `/admin/pipelines` | Create a new pipeline |
| GET | `/admin/pipelines` | List all pipelines for tenant |
| PUT | `/admin/pipelines/{pipeline_id}` | Update pipeline name/stages |
| DELETE | `/admin/pipelines/{pipeline_id}` | Delete a pipeline |
| POST | `/admin/pipelines/trigger` | Trigger pipeline execution |
| GET | `/admin/pipeline_agents` | List tenant agents in pipeline format |
| POST | `/admin/pipeline_agents` | Validate agent belongs to tenant |

### Platform + Data Explorer
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/audit` | Get audit logs |
| GET | `/api/notifications` | Get notifications |
| POST | `/api/notifications/{notif_id}/read` | Mark one notification as read |
| POST | `/api/notifications/read-all` | Mark all notifications as read |
| GET | `/api/system/health` | Platform health summary |
| GET | `/api/data-explorer/overview` | Combined datastore overview |
| GET | `/api/data-explorer/postgres` | PostgreSQL data view |
| GET | `/api/data-explorer/chromadb` | ChromaDB data view |
| GET | `/api/data-explorer/redis` | Redis key/value view |

### API Documentation
```
GET /docs         → FastAPI Swagger UI
GET /openapi.json → Raw OpenAPI 3.0 specification
```

### Request/Response Flow Diagram

```mermaid
sequenceDiagram
  participant UI as Django UI / Widget
  participant API as FastAPI
  participant R as Redis
  participant C as ChromaDB
  participant L as Groq LLM
  UI->>API: POST /api/runner/chat
  API->>R: Load session history
  API->>C: Retrieve semantic chunks
  API->>API: Apply policy scoring + prompt assembly
  API->>L: /chat/completions
  L-->>API: Response text
  API->>R: Save updated conversation
  API-->>UI: JSON response (+ sources)
```

### Health
```
GET /health  →  { status: "ok", timestamp: "..." }
```

### Campaigns (Outbound Dialing)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/campaigns/` | List campaigns for tenant |
| POST | `/api/campaigns/` | Create campaign (draft status) |
| POST | `/api/campaigns/{id}/contacts/upload` | Upload contacts CSV (phone, name, custom fields) |
| POST | `/api/campaigns/{id}/start` | Enqueue contacts to Redis + launch campaign worker |
| POST | `/api/campaigns/{id}/pause` | Pause campaign execution |
| GET | `/api/campaigns/{id}/stats` | Live stats with Redis queue depth |
| POST | `/api/campaigns/{id}/amd-callback` | Twilio AMD webhook (answering machine detection) |

### Webhooks
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/webhooks/` | List webhook endpoints for tenant |
| POST | `/api/webhooks/` | Create webhook endpoint (URL, events, auto-generated secret) |
| PUT | `/api/webhooks/{id}` | Update webhook config |
| DELETE | `/api/webhooks/{id}` | Delete webhook endpoint |
| POST | `/api/webhooks/{id}/test` | Send test event to verify endpoint |

### A/B Testing
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/ab/` | List experiments |
| POST | `/api/ab/` | Create experiment with variants (prompt, voice, model, temperature) |
| GET | `/api/ab/{id}/stats` | Variant performance stats (calls, conversions, sentiment) |
| POST | `/api/ab/{id}/record` | Record call outcome for a variant |
| DELETE | `/api/ab/{id}` | Delete experiment |

### DND (Do Not Disturb) Registry
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/dnd/` | List DND entries for tenant |
| POST | `/api/dnd/` | Add number to DND registry |
| DELETE | `/api/dnd/{id}` | Remove DND entry |
| POST | `/api/dnd/bulk` | Bulk import DND numbers |

### WhatsApp
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/whatsapp/inbound/{agent_id}` | Twilio WhatsApp inbound webhook (text + voice notes, Redis conversation history with 24h TTL) |

### Voice — Browser Live (Gemini-Style)
| Method | Endpoint | Description |
|---|---|---|
| WS | `/api/voice/live/{agent_id}` | Full-duplex browser voice WebSocket with JWT auth, VAD, barge-in, streaming TTS |

### Voice — Twilio Media Streams
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/voice/outbound/{agent_id}` | Outbound call TwiML (AMD check + Media Stream connect) |
| WS | `/api/voice/media-stream/{agent_id}` | Full-duplex Twilio WebSocket (μ-law ↔ PCM) |
| POST | `/api/voice/transfer/{call_sid}` | Warm transfer to human agent via Twilio REST API |
| POST | `/api/voice/recording-status/{agent_id}` | Twilio recording callback |

---

## Security Architecture

### Credential Encryption

All tenant-supplied API keys (Twilio, Groq, OpenAI) are encrypted at rest using **AES-256-GCM**:

```
Encrypt: nonce (96-bit random) + AESGCM.encrypt(key, nonce, plaintext) → base64url(nonce + ciphertext)
Decrypt: base64url decode → split nonce (12 bytes) + ciphertext → AESGCM.decrypt
Key: 32-byte key from CREDENTIALS_ENCRYPTION_KEY env var (64-char hex)
```

- Keys are encrypted per-field before storage in `Tenant.settings` (PostgreSQL JSON)
- `decrypt_safe()` gracefully handles plaintext values (migration support)
- `mask()` shows only first 4 characters for display

### Webhook HMAC Signing

All webhook event deliveries are signed with **HMAC-SHA256**:
- Each `WebhookEndpoint` has an auto-generated `secret`
- Signature header: `X-VoiceFlow-Signature: sha256=<hex digest>`
- Payload: JSON body of the event
- 3 retries with exponential backoff (1s, 2s, 4s) on delivery failure

### TwiML Injection Prevention

LLM-generated text is sanitized before injection into TwiML `<Say>` tags:
- Strips all XML/SSML tags via regex
- Escapes `&`, `<`, `>` characters
- Prevents LLM output from breaking TwiML structure or injecting executable tags

### Tenant Isolation

- **Database:** All queries include `WHERE tenantId = ?` — enforced at ORM level
- **Vector Store:** Per-tenant ChromaDB collections (`tenant_{tenantId}`) with `agentId` metadata filter
- **Conversation State:** Redis keys scoped to tenant + agent + session
- **Credentials:** AES-256-GCM encrypted per-tenant, never cross-readable
- **Rate Limiting:** Per-tenant via SlowAPI + Redis (falls back to IP-based)

### Authentication Flow

```
Browser → Django Login (session-based) → Django stores user + tenant in session
    │
    ▼
Django Proxy → Adds x-tenant-id, x-user-id, x-user-email headers
    │
    ▼
FastAPI → Reads headers via get_auth() dependency → AuthContext(tenant_id, user_id)
    │
    ▼
WebSocket endpoints → JWT bearer token in query param → validated via get_current_user()
```

### Twilio Signature Validation

Inbound Twilio webhooks validate `X-Twilio-Signature` using Twilio's `RequestValidator` with the tenant's auth token. Falls back to allowing unsigned requests when credentials are not configured (development mode only).

---

## Implementation Status

A complete breakdown of what works versus what needs attention.

### Fully Working

| Component | Notes |
|---|---|
| Django authentication | Email/password login + signup, session-based auth |
| 7-step onboarding wizard | All 7 steps persist to backend, including deploy |
| URL scraping + ingestion | Trafilatura extraction with BeautifulSoup fallback |
| File ingestion (PDF/DOCX/PPTX/XLSX) | Docling DocumentConverter + PaddleOCR fallback for scanned pages |
| ChromaDB vector storage | Per-tenant collections (`tenant_{id}`) with agentId metadata filter |
| Semantic search | Embedding-based top-K retrieval via ChromaDB |
| Hybrid retrieval (BM25 + semantic) | Client-side BM25 scoring combined with semantic results |
| **5-Layer Context Injection** | Global → Tenant → Brand → Agent → Session hierarchy assembled per request |
| **Policy-based retrieval scoring** | restrict=×0.05, require=×2.0, allow=×1.0 from merged Tenant/Brand/Agent rules |
| **Dynamic 7-section prompt assembly** | Safety → Tenant → Brand → Agent → Few-shot → Escalation → Policy |
| **Brand-level configuration** | Brand voice, allowed/restricted topics, policy rules — CRUD API + DB model |
| Groq LLM generation | Via Groq API with token limit management and condensing |
| Conversation history (Redis) | 24h TTL, last 20 turns stored per session |
| Chat interface (frontend) | Sends to `/api/runner/chat` via Django proxy |
| Redis rate limiting | Per-tenant with in-memory fallback |
| MinIO file storage | Per-tenant object paths (`{tenantId}/{timestamp}-{filename}`) |
| Twilio voice (TwiML Gather loop) | Inbound calls → speech recognition → full context pipeline → TwiML `<Say>` response loop |
| Per-tenant Twilio credentials | AES-256-GCM encrypted, stored in tenant settings, client cache with 5-min TTL |
| Twilio onboarding deploy | Demo-mode deploy endpoint activates agent and returns mock number (`+1-555-DEMO`) |
| Twilio webhook endpoints | Inbound/gather/status webhooks implemented at `/api/voice/*` |
| Agent template system | 10 seeded templates (Customer Support, Cold Calling, Lead Qualification, Technical Support, Receptionist, Survey Agent, Debt Collection, Appointment Reminder, Order Status, Customer Onboarding) |
| Voice selector UI | Edge + Kokoro voices with real-time preview and cloned voice selection |
| TTS | Edge TTS (primary) + Kokoro local fallback, with voice cloning and custom clone preview |
| Call logging | CallLog records with duration, transcript, caller phone, rating, flagging |
| **Analytics dashboard** | Real SQLAlchemy queries — overview, realtime, metrics-chart, agent-comparison |
| Onboarding progress (server-side) | GET/POST/DELETE `/onboarding/progress` for resume |
| Deploy gating | Frontend checks Twilio credential status before allowing deploy |
| **Retraining pipeline** | Nightly cron extracts flagged calls → admin review queue → approved examples injected as few-shot learning |
| **WebSocket voice calls** | Real audio pipeline: MediaRecorder → local `faster-whisper` or Groq Whisper STT → RAG → Edge/Clone/Kokoro TTS → audio playback. Text fallback for no-mic browsers. |
| **Embeddable call widget** | Public `<script>` tag serves push-to-talk widget with real audio capture/playback |
| **Retraining admin UI** | `/dashboard/retraining` — filter, edit, approve/reject, manual trigger |
| **Widget management UI** | `/dashboard/widget` — per-agent embed code with copy-to-clipboard |
| **FastAPI API documentation** | Interactive API explorer at `/docs` with OpenAPI 3.0 spec |
| **Conversation history in LLM (all paths)** | Last 20 turns from Redis passed into Groq messages array in ALL code paths: /chat, WebSocket, widget, process_query |
| **Per-tenant LLM model selection** | `GROQ_MODELS_ALLOWLIST` validates `agent.llmPreferences.model`; default `llama-3.3-70b-versatile` |
| **Bring Your Own Groq Key (BYOK)** | Tenants supply their own Groq API key via Settings. Encrypted with AES-256-GCM. All code paths resolve tenant key first, falling back to platform key |
| **Admin pipeline management** | Real CRUD: create/read/update/delete pipelines, async trigger with stage execution |
| **Per-agent REST API** | Public session-based endpoints for third-party integration (create session → send messages → get transcript → end session) |
| **Data Explorer dashboard** | `/dashboard/data-explorer` — visualise Postgres, ChromaDB & Redis contents in real-time |
| **Nightly retraining pipeline** | APScheduler cron at 02:00 — auto-extracts Q/A pairs from flagged calls + embeds approved examples into ChromaDB |
| **Agent template CRUD** | Full create/read/update/delete for agent templates via `/api/templates` |
| **Integrations page** | Real-time Twilio/Groq credential status from backend API |
| **Audit log with filtering** | Client-side search + action filter + API refresh |
| **Outbound campaigns** | Full campaign management: create → upload CSV contacts → start/pause → real-time stats with progress bars → AMD (answering machine detection) callback |
| **Webhook event dispatch** | HMAC-SHA256 signed event delivery to external URLs with 3 retries + exponential backoff. Events: `call.completed`, `campaign.finished`, `escalation.triggered`, `retraining.flagged` |
| **A/B Testing** | Create test variants (prompt, voice, model, temperature), split traffic, track conversion rates with confidence calculation |
| **DND (Do Not Disturb) Registry** | Compliance-first — add/bulk-import blocked numbers, automatic pre-dial check via `ComplianceService.is_dnd()` |
| **WhatsApp channel** | Per-agent WhatsApp configuration with Twilio integration, webhook URL generation, text + voice note handling |
| **Visual Flow Builder** | Drag-and-drop conversation flow designer with Mermaid.js visualization — greeting/knowledge/condition/API call/transfer nodes |
| **Modern UI system** | Production-grade design system: glassmorphism cards, micro-interactions, 15+ CSS animations (fade-in-up, scale-in, shimmer skeletons, stagger), dark mode support on all 25 dashboard pages |
| **TwiML injection prevention** | LLM output sanitized before TwiML `<Say>` — strips XML/SSML tags, escapes special characters |
| **Webhook secret masking** | Secrets revealed only at creation time; masked (first 4 chars + dots) on subsequent reads |
| **Streaming voice orchestrator** | Real-time audio pipeline: STT → RAG → TTS with barge-in/interruption support via Twilio Media Streams WebSocket |
| **Multi-TTS router** | Kokoro (CPU, natural), Piper (CPU, fast ONNX), Edge TTS (cloud, 300+ voices), Orpheus — per-agent configurable |
| **Campaign compliance** | Pre-dial checks: DND registry, calling hours (local timezone), retry limits — all enforced by `ComplianceService` |

### Partially Implemented

| Component | What Exists | What's Missing |
|---|---|---|
| Multi-language support | Agent `language` field in onboarding | No automatic language detection or translation pipeline |
| Voice cloning | `POST /api/tts/clone-voice` endpoint | Quality depends on reference audio; no fine-tuning |

### Not Yet Implemented (Frontend Exists, No Backend)

| Component | Frontend | Notes |
|---|---|---|
| Billing / invoices | `/dashboard/billing` page | No Stripe/payment backend; needs subscription logic |
| Backup / restore | `/dashboard/backup` page | No backend backup functionality |

### Known Issues

| Issue | Severity | Impact |
|---|---|---|
| Demo-mode auth | Low | No production auth — uses header-based tenant context for demos |
| `@csrf_exempt` on proxy views | Medium | CSRF attacks possible on state-changing Django→FastAPI proxy routes |
| Open redirect in login `next` param | Medium | Phishing via crafted redirect URL |
| WebSocket JWT in query string | Medium | Token visible in server logs / browser history |
| Recording callback bug | Low | Ignores `RecordingStatus` field; assumes audio URL always present |
| No DB migrations | Medium | `create_all()` only — schema changes require manual intervention |
| BM25 index rebuilt per query | Low | Performance degrades linearly with corpus size |

---

## Data Models

### PostgreSQL — SQLAlchemy ORM (`python/backend/app/models.py`)

17 models (Tenant, User, Brand, Agent, AgentConfiguration, AgentTemplate, OnboardingProgress, Document, CallLog, RetrainingExample, Pipeline, AuditLog, Notification, Campaign, CampaignContact, DNDRegistry, WebhookEndpoint):

```
Tenant
  id (uuid), name, domain?, apiKey, settings (JSON — includes encrypted
  Twilio creds, twilioCredentialsVerified flag), policyRules (JSON),
  isActive
  → has many: Users, Agents, Documents, Brands, RetrainingExamples

User
  id (uuid), email, name?, role, tenantId, brandId?
  → belongs to: Tenant, Brand

Brand
  id (uuid), tenantId, name, brandVoice (Text), allowedTopics (JSON),
  restrictedTopics (JSON), policyRules (JSON), createdAt, updatedAt
  → belongs to: Tenant
  → has many: Users, Agents

Agent
  id (uuid), name, systemPrompt?, voiceType, llmPreferences (JSON),
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
  id (uuid), name (unique), description, category?,
  baseSystemPrompt, defaultCapabilities (JSON),
  suggestedKnowledgeCategories (JSON), defaultTools (JSON)

OnboardingProgress
  id (autoincrement), userEmail (unique), tenantId?, agentId?,
  currentStep, data (JSON)

Document
  id (uuid), url?, s3Path?, status, title?, content?, metadata (JSON),
  tenantId, agentId
  → status: pending | processing | completed | failed

CallLog
  id (uuid), tenantId, agentId, callerPhone?, startedAt,
  endedAt?, durationSeconds?, transcript (Text), analysis (JSON),
  rating? (Int), ratingNotes?, flaggedForRetraining (Boolean),
  retrained (Boolean, default: false), createdAt
  → has many: RetrainingExamples

RetrainingExample
  id (uuid), tenantId, agentId, callLogId, userQuery (Text),
  badResponse (Text), idealResponse (Text),
  status (String: pending | approved | rejected),
  approvedAt?, approvedBy?, createdAt, updatedAt
  → belongs to: Tenant, Agent, CallLog

Pipeline
  id (uuid), tenantId, name, stages (JSON — array of stage objects),
  status (String: idle | running | completed | failed),
  lastRunAt?, createdAt, updatedAt
  → belongs to: Tenant

AuditLog
  id (uuid), tenantId, userId?, action, resource, resourceId?,
  details (JSON), ipAddress?, createdAt

Notification
  id (uuid), tenantId, userId?, type, title, message,
  isRead (Boolean), link?, createdAt

Campaign
  id (uuid), tenantId, agentId, name, status (draft|running|paused|completed),
  totalContacts, completedContacts, successfulContacts,
  scheduledAt?, startedAt?, completedAt?, createdAt, updatedAt
  → has many: CampaignContacts

CampaignContact
  id (uuid), campaignId, phoneNumber, name?, status (pending|calling|completed|failed|dnd),
  callSid?, callDuration?, callResult?, retryCount, calledAt?, createdAt

DNDRegistry
  id (uuid), tenantId, phoneNumber (unique per tenant), reason?,
  addedBy?, createdAt

WebhookEndpoint
  id (uuid), tenantId, url, events (JSON array), secret (auto-generated),
  description?, isActive (Boolean), createdAt, updatedAt
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
bm25:{tenantId}:{agentId}                      → JSON { documents, vocabulary } (BM25 index)
job:{jobId}                                    → ingestion job status string
job:{jobId}:progress                           → "0"–"100" percent
```

---

## Testing

### Test Files

| File | Test Count | Focus |
|---|---|---|
| `python/tests/conftest.py` | — | Shared fixtures: `async_client`, `test_tenant`, `test_agent`, DB cleanup |
| `python/tests/test_agents.py` | 5 | Agent CRUD, list, update, delete |
| `python/tests/test_auth.py` | 4 | Signup, login, token refresh, protected routes |
| `python/tests/test_tenants.py` | 3 | Tenant creation, settings update, get |
| `python/tests/test_documents.py` | 3 | Document upload, list, delete |
| `python/tests/test_knowledge_base.py` | 3 | KB creation, document association, search |
| `python/tests/test_conversations.py` | 4 | Start conversation, send message, list, history |
| `python/tests/test_webhooks.py` | 5 | Webhook CRUD + test delivery |
| `python/tests/test_campaigns.py` | 4 | Campaign CRUD + contact upload |
| `python/tests/test_rag_query.py` | 4 | RAG query with context, policy scoring, empty KB |

### Running Tests

```bash
cd python
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_agents.py

# Run a specific test
pytest tests/test_agents.py::test_create_agent
```

### Test Fixtures (`conftest.py`)

- `async_client` — `httpx.AsyncClient` pointing at FastAPI's `TestClient`
- `test_tenant` — auto-created tenant, cleaned up after test
- `test_agent` — agent linked to `test_tenant`, auto-cleaned
- Database is reset between test runs via truncation

---

## Known Limitations & Technical Debt

### Security Gaps

| Issue | Impact | Location |
|---|---|---|
| Django `@csrf_exempt` on proxy views | CSRF attacks on state-changing proxy routes | `django_frontend/views.py` |
| Open redirect in `/accounts/login/?next=` | Phishing via crafted redirect URL | `django_frontend/urls.py` |
| WebSocket JWT in query param | Token in server logs / browser history | `voice_live.py` |
| `CREDENTIALS_ENCRYPTION_KEY` hardcoded in dev `.env` | Key compromised if `.env` committed | `.env` |

### Performance Concerns

| Issue | Impact | Mitigation |
|---|---|---|
| Per-frame `pydub.AudioSegment` in Twilio stream | ~2ms per frame, adds latency at scale | Batch or use raw PCM slicing |
| BM25 built on every query (no index persistence) | O(n) per query on full corpus | Pre-build index on document ingest |
| No DB connection pooling configured | Connection exhaustion under load | Add SQLAlchemy pool settings |
| Unbounded `audio_buffer` in `voice_live.py` | Memory growth on long calls | Add max buffer size + flush |
| Fire-and-forget `asyncio.create_task` | Silent failures, no retry | Add task error handlers or use Celery |

### Known Bugs

| Bug | Trigger | Location |
|---|---|---|
| Recording callback ignores `RecordingStatus` | Twilio posts status updates; code assumes audio URL always present | `voice_twilio.py` |
| `streaming_orchestrator.py` orphaned | Imported nowhere; dead code | `python/services/` |
| `voice.py` partially dead | Old half-duplex code; some paths unreachable | `python/routes/voice.py` |

### Architecture Debt

- **No message queue**: Campaign worker runs in-process; should use Celery/Redis queue with worker processes
- **No circuit breaker**: External API failures (Twilio, LLM providers) propagate directly to callers
- **No structured logging**: Uses `print()` and basic `logging`; needs JSON structured logs for production observability
- **No database migrations**: Relies on `create_all()` — production needs Alembic migration chain
- **No health checks for dependencies**: `/health` returns OK without checking Postgres/Redis/ChromaDB connectivity

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
The same hierarchical RAG execution layer serves real-time voice calls via Twilio TwiML Gather loop and browser WebSocket calls. In the current implementation, Twilio routes by `agent_id` path parameter and resolves tenant via the agent record; phone-number-based tenant routing is a roadmap extension. The complete STT → context injection → retrieval → dynamic prompt → LLM pipeline is shared under per-tenant context constraints.

### System Architecture Under the Patent

```
Incoming Request (Voice or Text)
          │
          ▼
┌──────────────────────────────────────────────────────────┐
│              TENANT RESOLUTION                           │
│  • Auth JWT token   → extract tenantId                   │
│  • API key          → lookup tenant                      │
│  • Twilio inbound path param (`agent_id`) → tenantId      │
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
          │  STT (Groq Whisper)  │
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
          │  TTS (`<Say>` for Twilio, Edge/Kokoro for web) │
          │  → audio response   │
          └──────────┬─────────┘
                     │
                     ▼
          Response delivered to caller / chat
```

### What Needs to Be Built to Make All Claims True

The core patent pipeline is largely implemented. A few telephony-specific capabilities remain partial.

**Completed:**
- ~~Module 1 — Hierarchical Context Injection Service~~ → `rag_service.py:assemble_context()` — 5-layer hierarchy (Global → Tenant → Brand → Agent → Session)
- ~~Module 2 — Dynamic Prompt Assembly~~ → `rag_service.py:build_system_prompt()` — 7-section system prompt
- ~~Module 3 — Policy-Aware Retrieval Scoring~~ → `rag_service.py:apply_policy_scoring()` with restrict/require/allow multipliers
- ~~Module 4 — Schema Unification~~ → All 12 SQLAlchemy models exist with Brand, policy, escalation fields
- Module 5 — Phone Number to Tenant Mapping → **Partially implemented** (current Twilio path uses `agent_id`; phone-number routing map is a roadmap item)
- ~~Module 6 — Retraining Pipeline~~ → Flagged calls → nightly extraction → admin review → few-shot injection
- ~~Module 7 — WebSocket Voice Channel~~ → WebSocket at `/api/voice/ws/{agent_id}` + embeddable widget

Most patent-claimed modules are implemented; remaining telephony routing/provisioning gaps are documented below.

See `PATENT_CLAIMS_MAPPING.md` for the full claim-to-code trace document.

### Implementation Status of Patent Claims

| Claim | Description | Status |
|---|---|---|
| 1 | Receive input → resolve tenant → inject metadata → query isolated store → dynamic prompt → LLM → deliver | **Done** — Full pipeline: `assemble_context()` → policy-scored retrieval → 7-section prompt → Groq → voice/text response |
| 2 | Auto-create tenant vector store on first ingestion | **Done** — `get_or_create_collection()` in `ingestion_service.py` |
| 3 | Tenant metadata includes policies, compliance, persona | **Done** — Tenant.policyRules, Brand.policyRules, AgentConfiguration.policyRules + escalationRules loaded per request |
| 4 | Per-agent sub-stores within a tenant | **Done** via `agentId` metadata filter in ChromaDB |
| 5 | Policy-based filtering of retrieved chunks | **Done** — `apply_policy_scoring()` in `rag_service.py` with restrict/require/allow multipliers |
| 6 | Conversation state loaded and incorporated into prompt | **Done** — Last 20 turns from Redis passed into Groq messages array in all code paths (Twilio, WebSocket, chat, widget) |
| 7 | Dynamic LLM model selection per tenant config | **Done** — `GROQ_MODELS_ALLOWLIST` validates `agent.llmPreferences.model` against Groq production models; default `llama-3.3-70b-versatile` |
| 8 | Policy-weighted similarity scores modifying retrieval | **Done** — same as Claim 5, via `does_policy_match()` + multiplicative weights |
| 9 | Dynamic prompt assembly (not static template) | **Done** — `build_system_prompt()` in `rag_service.py`, 7 sections with `{{placeholder}}` replacement |
| 10 | Real-time ingestion without downtime | **Done** — FastAPI background task ingestion |
| 11 | Tenant isolation at storage AND inference layers | **Done** — Storage: per-tenant ChromaDB collections. Inference: `assemble_context()` scopes all DB queries to tenantId |
| 12 | Telephony with tenant-from-phone-number resolution | **Partial** — Current implementation resolves tenant via `/api/voice/inbound/{agent_id}`; phone-number mapping is pending |
| 13 | TTS audio response back via telephony | **Partial** — Twilio loop currently uses TwiML `<Say>` (Edge/Kokoro used in web voice paths) |
| 14 | Non-voice channels use same RAG pipeline | **Done** — `/api/runner/chat`, WebSocket `/api/voice/ws/{agent_id}`, embeddable widget all share same pipeline |
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
| **Run DB migrations** | 5 min | `make migrate` — ensure all SQLAlchemy models are reflected in Postgres |
| **Production SECRET_KEY** | 5 min | Current default is `"dev-secret"` — must be a real random secret in production |
| **HTTPS termination** | 1 hr | Add reverse proxy (nginx/Caddy) with TLS certificates for production |

### Should Build for Production

| Item | Effort | Description |
|---|---|---|
| **Billing / Stripe integration** | 2 wk | Frontend page exists at `/dashboard/billing`; needs Stripe subscriptions, usage metering, invoice generation |
| **Email notifications** | 1 wk | Frontend page exists at `/dashboard/notifications`; needs backend email service (SendGrid/SES) + in-app notification store |
| **Backup / restore** | 1 wk | Frontend page exists at `/dashboard/backup`; needs PostgreSQL dump + ChromaDB export logic |
| **True RTCPeerConnection audio** | 1 wk | Current WebSocket sends audio as binary frames; upgrade to RTCPeerConnection with STUN/TURN for lower latency |
| **Rate limit configuration UI** | 2 days | SlowAPI rate limiting works but limits are hardcoded; needs admin API to configure per-tenant limits |
| **Multi-language detection** | 3 days | Agent `language` field exists; add client language detection + prompt translation |
| **Automated testing** | 2 wk | No test suite for backend routes or frontend pages; need unit + integration tests |
| **CI/CD pipeline** | 3 days | No GitHub Actions / deployment pipeline; need build → test → deploy automation |
| **Monitoring / alerting** | 3 days | Need structured logging, health checks, uptime monitoring |

### Infrastructure for Scale

| Item | Description |
|---|---|
| Kubernetes / ECS deployment | Currently runs as Docker Compose + Make targets; needs container orchestration for HA |
| PostgreSQL read replicas | Single instance; needs read replicas for analytics queries at scale |
| ChromaDB clustering | Single instance; needs sharding strategy for 100+ tenants |
| Redis Sentinel / Cluster | Single instance; needs HA for conversation state |
| CDN for TTS audio | MinIO-cached TTS audio should be fronted by CloudFront/CDN |
| Secrets management | Credentials in `.env` files; need AWS Secrets Manager / Vault |
| SSL/TLS termination | Needs reverse proxy (nginx/Caddy) with TLS certificates |

### What Works End-to-End Today

If you start all services (`make init && make all`):

1. Sign up / log in via Django auth → tenant + user created automatically
2. Complete 7-step onboarding → configure company, create agent, upload documents, set voice, deploy
3. Documents are scraped/processed (Docling + PaddleOCR + trafilatura) → embedded → stored in `tenant_{id}` ChromaDB collection
4. Ask questions via web chat → full 5-layer context injection → policy-scored retrieval → 7-section prompt → Groq LLM → text response
5. Call via Twilio → same pipeline → TwiML `<Say>` voice response → conversational Gather loop
6. Call via WebSocket widget → embeddable `<script>` tag → MediaRecorder captures audio → server-side `faster-whisper` or Groq Whisper STT → RAG pipeline → Edge/Kokoro TTS audio playback
7. **Integrate via REST API** → any third-party website can create sessions, send messages, and get AI responses via 4 public endpoints per agent — no embed script needed
8. Agent remembers conversation context → last 20 turns from Redis included in every LLM call
9. Per-tenant model selection → each agent can use a different Groq model from the allowlist
10. Flag bad calls → nightly extraction → admin reviews/edits ideal responses → approved examples injected as few-shot learning
11. View real analytics → call counts, durations, success rates, agent comparisons from actual CallLog data
12. Configure brands → brand voice, topic restrictions, policy rules applied at inference time
13. Explore data → interactive Data Explorer with knowledge base, call log, and agent data visualisation
14. Browse interactive API docs → FastAPI Swagger UI at `/docs` (raw spec at `/openapi.json`)
15. Filter audit logs → searchable, filterable audit trail with action-type badges and real-time refresh

---

## License

License file is not yet committed in this repository. Add a `LICENSE` file before distribution.
---

## CPU-Only Mode — Included Services

All voice services run on CPU with no GPU requirement:

| Service | Technology | Port | Notes |
|---|---|---|---|
| Kokoro TTS | `ghcr.io/remsky/kokoro-fastapi-cpu` | 8880 | Primary TTS, natural voice |
| Piper TTS | `rhasspy/wyoming-piper` | 8890 | Fast ONNX CPU, low latency |
| Edge TTS | Cloud API (Microsoft) | — | Fallback; 300+ voices |
| Vosk STT | Offline model (auto-download) | — | Primary STT |
| faster-whisper | Local model (int8 CPU) | — | Fallback STT |

**TTS fallback chain:** Kokoro → Piper → Edge TTS  
**STT fallback chain:** faster-whisper (local) → Groq Whisper (API)

---

## What Is Not Included (GPU / Experimental Features)

The following features require GPU or are experimental and have been intentionally omitted from this release to keep the stack production-ready on CPU-only hardware:

| Feature | Status | Notes |
|---|---|---|
| **Orpheus TTS** (emotion/expressive) | Not included | Requires 3B GGUF model (~1.8 GB) + llama.cpp server; see commented block in `docker-compose.yml` |
| **Voice Cloning** | GPU only | Returns `410 Gone` with message "Voice cloning requires GPU". Endpoint scaffold exists at `POST /api/tts/clone-voice`. |
| **Hinglish (Hindi-English)** | Planned v2 | `agent.language = "hinglish"` column exists; transliteration pipeline not yet implemented |
| **CUDA/GPU torch** | Not needed | All inference is CPU-only; no `torch.cuda` in codebase |

---

## Telephony Architecture

```
Inbound / Outbound call
        │
        ▼
voice_inbound_router.py  (/api/voice/inbound/{agent_id})
        │
        ├─[telephony_provider = twilio-stream]──► voice_twilio_stream.py
        │                                         ├─ Twilio Media Streams WebSocket
        │                                         ├─ streaming_orchestrator.py
        │                                         │   ├─ Vosk / faster-whisper STT
        │                                         │   ├─ rag_service.process_query()
        │                                         │   └─ tts_router → μ-law → Twilio
        │                                         └─ Barge-in / interruption detection
        │
        └─[telephony_provider = twilio-gather]──► voice_twilio_gather.py
                                                  ├─ <Gather> TwiML loop
                                                  ├─ rag_service.process_query()
                                                  └─ <Say> TwiML response

Outbound campaigns:
  campaign_worker.py → Twilio REST API dial
        │
        └─► /api/voice/outbound/{agent_id}?contact_id=...
              ├─ AMD check (machine → hangup)
              └─ <Connect><Stream> + contact variables as <Parameter> tags
```

## Running Alembic Migrations

Alembic manages the FastAPI backend database schema. Run migrations:

```bash
cd python
# Linux/macOS/CI
make alembic-migrate

# Windows PowerShell
cd backend
uv run alembic upgrade head
```

Django migrations (frontend auth/sessions) are separate:

```bash
cd python/frontend
python manage.py migrate
```

To run both at once (Linux/macOS):

```bash
cd python
make migrate-all
```
