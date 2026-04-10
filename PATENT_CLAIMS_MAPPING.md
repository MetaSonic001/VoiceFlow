# VoiceFlow AI Platform — Patent Claims Technical Mapping

> **Internal document** — Maps each patent claim to specific code artifacts.
> Prepared for patent counsel review before formal prosecution.
>
> Last updated: April 2026

---

## Claim 1 — Independent Claim (Full Pipeline)

**Claim text (summary):** A multi-tenant AI voice agent platform that receives a customer interaction, resolves the tenant, assembles a context-aware prompt using a hierarchical context injection system, retrieves relevant knowledge from an isolated vector store, scores results against configurable policy rules, assembles a dynamic system prompt, generates a response via a large language model, synthesises speech, and delivers the response.

### End-to-end data flow

```
Inbound call (Twilio) / WebSocket → Tenant resolution → assemble_context() (5-layer)
  → ChromaDB query (tenant-isolated) → Policy scoring pass → Dynamic prompt assembly
    → Groq LLM generation → Edge TTS synthesis → Twilio TwiML / WebSocket response
```

### Code trace

| Step | File | Function / Route | Notes |
|------|------|-----------------|-------|
| 1. Inbound call received | `python/backend/app/routes/voice.py` | `POST /inbound/{agent_id}` | Twilio webhook; validates signature |
| 2. Tenant resolution | `voice.py:37-55` | Agent looked up by `agent_id` → `agent.tenantId` | One query resolves tenant |
| 3. Session creation | `voice.py:55-65` | Redis key `twilio:session:{callSid}` stores `{ agentId, tenantId, startedAt, callerPhone }` | Per-call state |
| 4. Speech received | `voice.py` | `POST /gather/{agent_id}` | `request.form()["SpeechResult"]` from Twilio Gather |
| 5. Context injection | `python/backend/app/services/rag_service.py` | `assemble_context(tenant_id, agent_id, session_id)` | 5-layer hierarchy: Global → Tenant → Brand → Agent → Session |
| 6. Vector store query | `rag_service.py` | `query_documents(tenant_id, agent_id, query, top_k, max_tokens, policy_rules)` | Collection: `tenant_{tenant_id}`, where: `{ agentId }` |
| 7. Policy scoring | `rag_service.py` | `apply_policy_scoring(docs, rules)` | restrict=×0.05, require=×2.0, allow=×1.0 |
| 8. Prompt assembly | `rag_service.py` | `build_system_prompt(ctx)` | 7-section prompt: safety → tenant → brand → agent → few-shot → escalation → policy |
| 9. LLM generation | `rag_service.py` | `generate_response(system_prompt, context, query, conversation_history, token_limit, model)` | Groq API (`llama-3.3-70b-versatile` default; per-tenant model via agent config) |
| 10. TTS synthesis | `voice.py` + Edge TTS | Edge TTS `edge-tts` library with 13 en-US voices | Generates audio, serves via MinIO or inline TwiML `<Say>` |
| 11. Response delivery | `voice.py` | TwiML `<Say>` + `<Gather>` loop | Continues conversation |
| 12. Call ended | `voice.py` | `POST /status/{agent_id}` | Persists CallLog + async `analyze_call()` background task |

**Per-tenant LLM model selection:** `rag_service.py` — `generate_response()` reads `agent.llmPreferences.model` and validates against Groq production models (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, etc.). Falls back to `llama-3.3-70b-versatile` if not set or invalid.

**Per-tenant Groq API key (BYOK):** `rag_service.py` — `_resolve_groq_key(tenant)` decrypts and returns the tenant's own Groq API key from `tenant.settings.groqApiKey` (AES-256-GCM encrypted via `credentials.py`). All code paths call this helper first: `runner.py` `/chat`, `voice.py` `/gather`, `voice_ws.py` WebSocket, and widget `process_query()`. If no tenant key exists, the platform-level `GROQ_API_KEY` env var is used as fallback. Key management endpoints in `python/backend/app/routes/settings.py`: validate key against live Groq `/models` API before saving, return masked status, allow removal.

**WebSocket alternative path (Claim 1 variant):**

| Step | File | Notes |
|------|------|-------|
| 1. Browser connects | `python/backend/app/routes/voice_ws.py` | WebSocket at `/api/voice/ws/{agent_id}` |
| 2-9. Same pipeline | Same services | `assemble_context()` → RAG → Policy → Prompt → LLM (conversation history included) |
| 10. Server-side STT | `voice_ws.py` | Groq Whisper `whisper-large-v3-turbo` transcribes client audio (`_transcribe_groq()`) |
| 11. Server-side TTS | Edge TTS | `edge-tts` library generates speech; audio returned as binary WebSocket frame |
| 12. CallLog persisted | `voice_ws.py` on disconnect | Same schema as Twilio calls |

---

## Claim 2 — Hierarchical Context Injection (5-Layer)

**File:** `python/backend/app/services/rag_service.py`
**Function:** `assemble_context(tenant_id, agent_id, session_id, brand_id_override?)`

| Layer | Source | Data |
|-------|--------|------|
| 1. Global | `GLOBAL_SAFETY_RULES` constant (line ~59) | Safety rules, prompt injection prevention |
| 2. Tenant | `SQLAlchemy: Tenant.settings`, `Tenant.policyRules` | Org name, industry, use case, tenant policies |
| 3. Brand | `SQLAlchemy: Brand.brandVoice`, `Brand.allowedTopics`, `Brand.restrictedTopics`, `Brand.policyRules` | Brand voice guidelines, topic constraints |
| 4. Agent | `SQLAlchemy: AgentTemplate.baseSystemPrompt`, `AgentConfiguration.*`, `Agent.systemPrompt` | Persona, template, custom instructions, capabilities |
| 5. Session | `Redis: conversation:{tenantId}:{agentId}:{sessionId}` | Last 20 conversation turns (passed through to LLM as `conversation_history` in all code paths: Twilio, WebSocket, chat, widget) |

**Merge strategy:** Lower layers override higher for same key. Global rules are immutable.

**Return type:** `dict` with 30+ fields including all policy rules, context layers, and few-shot examples.

---

## Claim 3 — Per-Tenant Vector Store Isolation

**Ingestion service:** `python/backend/app/services/ingestion_service.py`
- Collection naming: `f"tenant_{tenant_id}"` — per-tenant ChromaDB collection
- Agent isolation via metadata: `{ agentId }` in every chunk
- Input validation: `tenant_id` required on all endpoints

**Query service:** `python/backend/app/services/rag_service.py`
- Guard: `tenant_id` required parameter on `query_documents()`
- Query scoped: `where: { agentId }` in both semantic (`_semantic_search()`) and keyword (`_bm25_search()`) search
- No cross-tenant data leakage possible — collection name is the isolation boundary

---

## Claim 4 — Policy-Based Retrieval Scoring

**File:** `python/backend/app/services/rag_service.py`
**Function:** `apply_policy_scoring(docs, rules)` (line ~466)

- **Input:** Retrieved documents with metadata + policy rules from context hierarchy
- **Scoring:** Each rule checks document content and metadata against policy targets:
  - `topic` → content text matching
  - `documentSource` → metadata.source matching
  - `documentTag` → metadata.tags matching
- **Multipliers:** `restrict` → ×0.05 (nearly suppressed), `require` → ×2.0 (boosted), `allow` → ×1.0 (unchanged)
- **Policy rules source:** Merged from Tenant + Brand + Agent via `assemble_context()`

---

## Claim 5 — Dynamic Multi-Section Prompt Assembly

**File:** `python/backend/app/services/rag_service.py`
**Function:** `build_system_prompt(ctx: dict) -> str` (line ~514)

7 sections joined by `\n\n---\n\n`:

1. **Global safety rules** — Immutable `GLOBAL_SAFETY_RULES`, never overridden
2. **Tenant context** — Organisation name, industry, policy summary
3. **Brand guidelines** — Brand voice, allowed/restricted topics
4. **Agent configuration** — Name, persona, template (with `{{placeholder}}` replacement), custom instructions
5. **Learned examples** — Few-shot pairs from retraining pipeline (in-context learning)
6. **Escalation rules** — Trigger → action pairs
7. **Active policy rules** — Human-readable summary of restrictions and requirements

---

## Claim 6 — Brand-Level Configuration

**Schema:** `python/backend/app/models.py` — `class Brand(Base)`

| Field | Type | Purpose |
|-------|------|---------|
| `brandVoice` | `Text` | Voice/tone guidelines for all agents under this brand |
| `allowedTopics` | `JSON` | Array of topics the brand permits |
| `restrictedTopics` | `JSON` | Array of topics the brand forbids |
| `policyRules` | `JSON` | `PolicyRule[]` — brand-level retrieval scoring rules |

**API:** `python/backend/app/routes/brands.py` — Full CRUD with tenant isolation.
**Agent assignment:** `Agent.brandId` field; set during onboarding or later via API.

---

## Claim 7 — Real-Time Knowledge Updates (Continuous Improvement Loop)

**Retraining pipeline:** `python/backend/app/services/scheduler.py`

1. Business flags bad calls → `CallLog.flaggedForRetraining = True` (via `POST /api/logs/:id/flag`)
2. Nightly cron (`scheduler.py`) runs `nightly_retraining_pipeline()`:
   - `extract_flagged_call_logs()` extracts user-query / bad-response pairs from transcript
   - Creates `RetrainingExample` records (status: "pending")
   - Marks CallLog as `retrained: True`
3. Admin reviews examples (`/dashboard/retraining` page), edits ideal response, approves
4. `retrain_approved_examples()` embeds approved examples into ChromaDB
5. `build_system_prompt()` includes approved examples as **LEARNED EXAMPLES** section (in-context learning)
6. Agent immediately responds better to similar queries — **no fine-tuning needed**

**Schema:** `python/backend/app/models.py` — `class RetrainingExample(Base)` with status tracking and audit fields.
**Admin UI:** `python/frontend/templates/dashboard/retraining.html`

---

## Claim 8 — Multi-Channel Delivery

| Channel | Implementation | File |
|---------|---------------|------|
| **Twilio voice** | TwiML webhooks, `<Gather>` + `<Say>` loop | `python/backend/app/routes/voice.py` |
| **WebSocket browser calls** | FastAPI WebSocket, Groq Whisper STT + Edge TTS (server-side) | `python/backend/app/routes/voice_ws.py` |
| **Web chat** | REST API `POST /api/runner/chat` | `python/backend/app/routes/runner.py` |
| **Embeddable widget** | Self-contained JS snippet | `python/backend/app/routes/widget.py` (`GET /api/widget/{agent_id}/embed.js`) |

All channels share the same RAG pipeline: `assemble_context()` → `query_documents()` → `apply_policy_scoring()` → `build_system_prompt()` → `generate_response()`.

---

## Claim 9 — Per-Tenant Twilio Credentials (Encrypted)

**File:** `python/backend/app/services/credentials.py`
**Encryption:** AES-256-GCM with per-deployment `ENCRYPTION_KEY` (derived via `_derive_key()`)
**Functions:** `encrypt_value(plaintext)` → base64 token, `decrypt_value(token)` → plaintext, `decrypt_safe(token)` → plaintext or original
**Storage:** `Tenant.settings.twilioCredentials` (encrypted JSON in Postgres)
**API:** `python/backend/app/routes/settings.py` — `POST /twilio` (save), `GET /twilio` (status), `DELETE /twilio` (remove)

---

## Claim 10 — Agent Template System

**Schema:** `python/backend/app/models.py` — `class AgentTemplate(Base)` with `baseSystemPrompt`, `defaultCapabilities`, `suggestedKnowledgeCategories`, `defaultTools`
**Seeded templates:** 6 industry-specific templates (Customer Support, Sales, Healthcare, Legal, etc.)
**API:** `python/backend/app/routes/templates.py` — Full CRUD (GET list, GET by ID, POST create, PUT update, DELETE soft-delete), template selection during onboarding
**Usage:** Template's `baseSystemPrompt` is used as the base for dynamic prompt assembly with `{{placeholder}}` replacement.

---

## Claim 11 — Automated Document Ingestion

**Service:** `python/backend/app/services/ingestion_service.py`

| Source | Processing |
|--------|-----------|
| URLs | Trafilatura + BeautifulSoup fallback |
| S3/MinIO files | Docling (PDF, DOCX, PPTX, XLSX) + PaddleOCR for images |
| Company website | Multi-page crawl with smart scraping |

**Chunking:** `RecursiveCharacterTextSplitter` (1000 chars, 200 overlap)
**Embeddings:** `all-MiniLM-L6-v2` via `SentenceTransformer`
**Storage:** ChromaDB collection `tenant_{tenant_id}` with `agentId` metadata
**Incremental:** Tracks document hashes, skips unchanged content on re-ingestion

---

## Claim 12 — Call Analytics and Post-Call Analysis

**CallLog persistence:** `python/backend/app/models.py` — `class CallLog(Base)` with transcript, duration, rating, analysis JSON
**Post-call analysis:** `voice.py:analyze_call()` — LLM-powered analysis stored in `CallLog.analysis` (runs as FastAPI `BackgroundTask`)
**Analytics API:** `python/backend/app/routes/analytics.py` — SQLAlchemy queries for:
- `/analytics/overview` — Total calls, avg duration, success rate
- `/analytics/realtime` — Live metrics
- `/analytics/metrics-chart` — Time-series data
- `/analytics/agent-comparison` — Per-agent performance
- `/analytics/usage` — Usage statistics

---

## Claim 13 — Tenant Rate Limiting

**Library:** SlowAPI (Python slowapi)
**Files:** `python/backend/app/routes/rag.py`, `python/backend/app/routes/runner.py`
**Method:** `Limiter(key_func=_tenant_key, storage_uri="redis://...")` — Per-tenant sliding window rate limiter using Redis
**Limits:** `@limiter.limit("30/minute")` applied on RAG and runner endpoints

---

## Claim 14 — Guided Agent Onboarding

**Backend:** `python/backend/app/routes/onboarding.py` — Multi-step wizard API
**Frontend:** `python/frontend/templates/onboarding/flow.html` — 7-step flow:
1. Company setup (with auto-scraping)
2. Agent template selection
3. Knowledge upload (files + URLs)
4. Voice personality configuration (Edge TTS preview with 13 voices)
5. Channel setup (Twilio BYOK / WebSocket)
6. Agent configuration (name, role, behaviour)
7. Deployment + go-live

**Progress persistence:** `python/backend/app/models.py` — `class OnboardingProgress(Base)` — Server-side resume support

---

## Claim 15 — WebSocket Voice Channel (Twilio-Free)

**WebSocket:** `python/backend/app/routes/voice_ws.py` — FastAPI WebSocket at `/api/voice/ws/{agent_id}`
**Widget:** `python/backend/app/routes/widget.py` — Embeddable `<script>` tag
**Server STT:** Groq Whisper (`whisper-large-v3-turbo`) — client sends audio via WebSocket binary frame, server transcribes (`_transcribe_groq()`)
**Server TTS:** Edge TTS via `edge-tts` library — server generates speech, returns audio as binary WebSocket frame
**Pipeline:** Same `assemble_context()` → RAG → Policy → Prompt → LLM as Twilio calls (conversation history included in all paths)

---

## Partially Implemented Claims

| Claim | Gap | What remains |
|-------|-----|-------------|
| Fine-tuning | Only in-context learning (few-shot) is implemented | Full model fine-tuning via LoRA/QLoRA not implemented (by design — too slow/expensive for MVP) |
| Multi-language | Agent `language` field exists in onboarding | No automatic language detection or translation pipeline |
| Custom TTS voices | Edge TTS provides 13 en-US voices | Voice cloning not yet implemented; current selection covers standard use cases |

---

## Architecture Diagram (for patent figures)

```
┌────────────────────────────────────────────────────────────┐
│                    INBOUND CHANNELS                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │  Twilio   │  │WebSocket │  │ Web Chat │  │  Widget   │ │
│  │  Voice    │  │  Voice   │  │  REST    │  │  Embed    │ │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬─────┘ │
└────────┼──────────────┼────────────┼──────────────┼────────┘
         │              │            │              │
         └──────────────┼────────────┼──────────────┘
                        ▼
              ┌──────────────────┐
              │ Tenant Resolution │
              │ (Auth / DB Lookup)│
              └────────┬─────────┘
                       ▼
              ┌──────────────────┐
              │ assemble_context()│ ◄── 5-Layer Hierarchy
              │ (SQLAlchemy+Redis)│     Global → Tenant → Brand
              └────────┬─────────┘     → Agent → Session
                       ▼
         ┌─────────────┴─────────────┐
         ▼                           ▼
┌──────────────────┐     ┌────────────────────┐
│ query_documents() │     │  Few-Shot Examples  │
│ (tenant-isolated) │     │  (Retraining DB)    │
└────────┬─────────┘     └──────────┬─────────┘
         │                          │
         ▼                          │
┌────────────────────┐              │
│apply_policy_scoring()│             │
│ (restrict/boost)    │              │
└────────┬───────────┘              │
         │                          │
         └──────────┬───────────────┘
                    ▼
         ┌──────────────────────┐
         │ build_system_prompt() │ ◄── 7-Section System Prompt
         └────────┬─────────────┘
                  ▼
         ┌──────────────────┐
         │ generate_response()│
         │    (Groq LLM)     │
         └────────┬─────────┘
                  ▼
         ┌──────────────────┐
         │   TTS Synthesis   │ ◄── Edge TTS (Twilio & WebSocket: server-side)
         └────────┬─────────┘
                  ▼
         ┌──────────────────┐
         │ Response Delivery │ ◄── TwiML / WebSocket / REST JSON
         └────────┬─────────┘
                  ▼
         ┌──────────────────┐
         │ CallLog + Analysis │ ◄── Persistent storage + LLM analysis
         └──────────────────┘
```
