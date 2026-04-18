# VoiceFlow AI Platform

A multi-tenant SaaS platform for building, deploying, and managing AI-powered voice and chat agents. Businesses onboard through a guided wizard, upload their knowledge base, and receive a domain-specific AI agent that answers customer queries over phone (Twilio), browser-based WebSocket voice calls, or a web chat interface — using Retrieval-Augmented Generation (RAG) over their own documents with hierarchical context injection and policy-based retrieval scoring.

> **Status (April 2026):** The full pipeline is functional end-to-end: 7-step onboarding → document ingestion → per-tenant vector isolation → 5-layer context injection → policy-scored retrieval → dynamic 7-section prompt assembly → Groq LLM generation (per-tenant model selection, conversation history in all code paths) → TTS → multi-channel delivery (Twilio voice, **real WebSocket audio** with local `faster-whisper` or Groq Whisper STT + Edge/Chatterbox TTS, web chat, embeddable widget, **per-agent REST API for third-party integration**). Analytics use real DB queries. A retraining pipeline captures bad calls and injects learned corrections as few-shot examples. Admin pipeline management with real CRUD. Data Explorer dashboard to visualise Postgres, ChromaDB & Redis contents. Interactive API docs via FastAPI at `/docs`. **Stack: Django 6 (HTMX + Alpine.js) frontend + FastAPI backend + Docker services (Postgres, Redis, ChromaDB, MinIO).** See [Implementation Status](#implementation-status) for the full breakdown.

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
│   │  Header Auth │  │  Rate Limiter │  │    22 Route Files      │   │
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
│   │  12 models    │  │  Per-tenant  │  │  Conv hist   │            │
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
│   └──────────────┘  │  • Edge TTS + Chatterbox fallback         │  │
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
│   │   │   ├── routes/            ← 22 route files
│   │   │   │   ├── agents.py      ← Agent CRUD + activate/pause
│   │   │   │   ├── analytics.py   ← Real DB-based analytics
│   │   │   │   ├── auth.py        ← Login/signup/user-sync
│   │   │   │   ├── brands.py      ← Brand CRUD (voice, topics, policies)
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
│   │   │   │   ├── voice.py       ← Twilio TwiML Gather loop
│   │   │   │   ├── voice_ws.py    ← WebSocket voice (Whisper STT)
│   │   │   │   ├── widget.py      ← Embeddable JS widget (public)
│   │   │   │   ├── admin.py       ← Pipeline CRUD + trigger
│   │   │   │   ├── platform.py    ← Audit, notifications, health
│   │   │   │   ├── data_explorer.py ← Postgres/ChromaDB/Redis viewer
│   │   │   │   └── users.py       ← User management
│   │   │   └── services/          ← Core service modules
│   │   │       ├── rag_service.py         ← 5-layer context injection +
│   │   │       │                            policy scoring + 7-section
│   │   │       │                            prompt assembly + Groq LLM
│   │   │       ├── ingestion_service.py   ← Docling + PaddleOCR + scraping
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
│       │       ├── api_proxy.py   ← 25+ proxy endpoints for JS/HTMX
│       │       ├── onboarding.py  ← 7-step wizard view
│       │       ├── auth.py        ← Login/register/logout
│       │       └── chat.py        ← Chat + voice agent views
│       └── templates/
│           ├── base_dashboard.html
│           ├── partials/sidebar.html
│           ├── onboarding/flow.html   ← 7-step wizard (Alpine.js)
│           ├── agents/detail.html     ← Agent detail + chat
│           └── dashboard/             ← 18 dashboard pages
│               ├── analytics.html     ← Charts + metrics
│               ├── audit.html         ← Filterable audit log
│               ├── calls.html         ← Call log viewer
│               ├── data_explorer.html ← DB visualiser (Postgres/Chroma/Redis)
│               ├── knowledge.html     ← Knowledge base management
│               ├── retraining.html    ← Retraining queue admin
│               ├── settings.html      ← Twilio/Groq/voice config
│               ├── system.html        ← System health monitor
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
| TTS | Edge TTS (primary) + Chatterbox local fallback/cloning |
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
  Step 4: Voice & Personality→ POST /onboarding/voice       → Edge + Chatterbox voice preview
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
  → synthesises response audio via Edge (primary) with Chatterbox/clone fallback
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

## Running the Project

### Prerequisites

- Docker Desktop (for infrastructure services)
- Python 3.11+ (3.12 recommended)
- `make` (via Chocolatey: `choco install make`)
- **CUDA/CPU PyTorch runtime** — installed by `make install` (used by local Chatterbox TTS path)
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

### TTS (Text-to-Speech — Edge + Chatterbox)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/tts/preset-voices` | List Edge voices + local Chatterbox options |
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
| Agent template system | 6 seeded templates (Customer Support, Cold Calling, Lead Qualification, Technical Support, Receptionist, Survey Agent) |
| Voice selector UI | Edge + Chatterbox voices with real-time preview and cloned voice selection |
| TTS | Edge TTS (primary) + Chatterbox local fallback, with voice cloning and custom clone preview |
| Call logging | CallLog records with duration, transcript, caller phone, rating, flagging |
| **Analytics dashboard** | Real SQLAlchemy queries — overview, realtime, metrics-chart, agent-comparison |
| Onboarding progress (server-side) | GET/POST/DELETE `/onboarding/progress` for resume |
| Deploy gating | Frontend checks Twilio credential status before allowing deploy |
| **Retraining pipeline** | Nightly cron extracts flagged calls → admin review queue → approved examples injected as few-shot learning |
| **WebSocket voice calls** | Real audio pipeline: MediaRecorder → local `faster-whisper` or Groq Whisper STT → RAG → Edge/Clone/Chatterbox TTS → audio playback. Text fallback for no-mic browsers. |
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

---

## Data Models

### PostgreSQL — SQLAlchemy ORM (`python/backend/app/models.py`)

12 models:

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
          │  TTS (`<Say>` for Twilio, Edge/Chatterbox for web) │
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
| 13 | TTS audio response back via telephony | **Partial** — Twilio loop currently uses TwiML `<Say>` (Edge/Chatterbox used in web voice paths) |
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
6. Call via WebSocket widget → embeddable `<script>` tag → MediaRecorder captures audio → server-side `faster-whisper` or Groq Whisper STT → RAG pipeline → Edge/Chatterbox TTS audio playback
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