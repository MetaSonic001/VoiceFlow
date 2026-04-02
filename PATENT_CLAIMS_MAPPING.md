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
Inbound call (Twilio) / WebRTC → Tenant resolution → ContextInjector (5-layer)
  → ChromaDB query (tenant-isolated) → Policy scoring pass → Dynamic prompt assembly
    → Groq LLM generation → TTS synthesis → Twilio TwiML / WebRTC response
```

### Code trace

| Step | File | Function / Route | Notes |
|------|------|-----------------|-------|
| 1. Inbound call received | `src/routes/twilioVoice.ts` | `POST /twilio/voice/incoming` | Twilio webhook; validates signature |
| 2. Tenant resolution | `src/routes/twilioVoice.ts:40-50` | Agent looked up by `req.body.To` (phone number) → `agent.tenantId` | One query resolves tenant |
| 3. Session creation | `src/routes/twilioVoice.ts:55-65` | Redis key `twilio:session:{callSid}` stores `{ agentId, tenantId, startedAt, callerPhone }` | Per-call state |
| 4. Speech received | `src/routes/twilioVoice.ts` | `POST /twilio/voice/respond` | `req.body.SpeechResult` from Twilio Gather |
| 5. Context injection | `src/services/contextInjector.ts` | `ContextInjector.assemble(tenantId, agentId, sessionId)` | 5-layer hierarchy: Global → Tenant → Brand → Agent → Session |
| 6. Vector store query | `src/services/ragService.ts` | `queryDocuments(tenantId, agentId, query, topK, maxTokens, policyRules)` | Collection: `tenant_{tenantId}`, where: `{ agentId }` |
| 7. Policy scoring | `src/services/ragService.ts` | `applyPolicyScoring(docs, rules)` | restrict=×0.05, require=×2.0, allow=×1.0 |
| 8. Prompt assembly | `src/services/promptAssembly.ts` | `buildSystemPrompt(ctx)` | 7-section prompt: safety → tenant → brand → agent → few-shot → escalation → policy |
| 9. LLM generation | `src/services/ragService.ts` | `generateResponse(systemPrompt, context, query, conversationHistory, tokenLimit, model)` | Groq API (`llama-3.3-70b-versatile` default; per-tenant model via `resolveModel()`) |
| 10. TTS synthesis | `src/services/ttsService.ts` | `synthesiseForCall(text, voiceId)` | Chatterbox TTS or AWS Polly fallback |
| 11. Response delivery | `src/routes/twilioVoice.ts` | TwiML `<Say>` + `<Gather>` loop | Continues conversation |
| 12. Call ended | `src/routes/twilioVoice.ts` | `POST /twilio/voice/status` | Persists CallLog + async call analysis |

**Per-tenant LLM model selection:** `src/services/ragService.ts` — `resolveModel(agent)` reads `agent.llmPreferences.model` and validates against a 4-model Groq production allowlist (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b`). Falls back to `llama-3.3-70b-versatile` if not set or invalid. Model is passed to `generateResponse()` in all code paths.

**WebRTC alternative path (Claim 1 variant):**

| Step | File | Notes |
|------|------|-------|
| 1. Browser connects | `src/services/webrtcService.ts` | Socket.IO on `/ws` with `{ agentId, tenantId }` |
| 2-9. Same pipeline | Same services | ContextInjector → RAG → Policy → Prompt → LLM (conversation history included) |
| 10. Server-side STT | `webrtcService.ts` | Groq Whisper `whisper-large-v3-turbo` transcribes client audio |
| 11. Server-side TTS | `src/services/ttsService.ts` | `synthesiseForWebRTC(text, voiceId)` via Chatterbox TTS; audio URL returned to client |
| 12. CallLog persisted | `webrtcService.ts` on `disconnect` | Same schema as Twilio calls |

---

## Claim 2 — Hierarchical Context Injection (5-Layer)

**File:** `src/services/contextInjector.ts`
**Class:** `ContextInjector`
**Method:** `assemble(tenantId, agentId, sessionId, brandIdOverride?)`

| Layer | Source | Data |
|-------|--------|------|
| 1. Global | Hardcoded constant `GLOBAL_RULES` | Safety rules, prompt injection prevention |
| 2. Tenant | `Prisma: Tenant.settings`, `Tenant.policyRules` | Org name, industry, use case, tenant policies |
| 3. Brand | `Prisma: Brand.brandVoice`, `Brand.allowedTopics`, `Brand.restrictedTopics`, `Brand.policyRules` | Brand voice guidelines, topic constraints |
| 4. Agent | `Prisma: AgentTemplate.baseSystemPrompt`, `AgentConfiguration.*`, `Agent.systemPrompt` | Persona, template, custom instructions, capabilities |
| 5. Session | `Redis: conversation:{tenantId}:{agentId}:{sessionId}` | Last 20 conversation turns (passed through to LLM as `conversationHistory` in all code paths: Twilio, WebRTC, chat, widget) |

**Merge strategy:** Lower layers override higher for same `(target, value)` key. Global rules are immutable (`mergePolicyRules()` method, line ~231).

**Return type:** `AssembledContext` interface (30+ fields, fully typed).

---

## Claim 3 — Per-Tenant Vector Store Isolation

**Ingestion service:** `ingestion-service/main.py`
- Collection naming: `f"tenant_{tenant_id}"` (lines 315, 485, 512, 522)
- Agent isolation via metadata: `{ agentId }` in every chunk
- Input validation: `tenant_id` required on all endpoints (lines 112-115, 454-455)

**Query service:** `src/services/ragService.ts`
- Guard: `if (!tenantId) throw new Error('tenantId required')` (line 59)
- Query scoped: `where: { agentId }` in both semantic and keyword search
- No cross-tenant data leakage possible — collection name is the isolation boundary

---

## Claim 4 — Policy-Based Retrieval Scoring

**File:** `src/services/ragService.ts`
**Method:** `applyPolicyScoring(docs, rules)`

- **Input:** Retrieved `ScoredDocument[]` with metadata + `PolicyRule[]` from context hierarchy
- **Scoring:** Each rule checks `doesPolicyMatch(doc, rule)` which inspects:
  - `topic` → content text matching
  - `documentSource` → metadata.source matching
  - `documentTag` → metadata.tags matching
- **Multipliers:** `restrict` → ×0.05 (nearly suppressed), `require` → ×2.0 (boosted), `allow` → ×1.0 (unchanged)
- **Policy rules source:** Merged from Tenant + Brand + Agent via `ContextInjector.mergePolicyRules()`

---

## Claim 5 — Dynamic Multi-Section Prompt Assembly

**File:** `src/services/promptAssembly.ts`
**Function:** `buildSystemPrompt(ctx: AssembledContext): string`

7 sections joined by `\n\n---\n\n`:

1. **Global safety rules** — Immutable, never overridden
2. **Tenant context** — Organisation name, industry, policy summary
3. **Brand guidelines** — Brand voice, allowed/restricted topics
4. **Agent configuration** — Name, persona, template (with `{{placeholder}}` replacement), custom instructions
5. **Learned examples** — Few-shot pairs from retraining pipeline (in-context learning)
6. **Escalation rules** — Trigger → action pairs
7. **Active policy rules** — Human-readable summary of restrictions and requirements

---

## Claim 6 — Brand-Level Configuration

**Schema:** `prisma/schema.prisma` — `model Brand`

| Field | Type | Purpose |
|-------|------|---------|
| `brandVoice` | `String @db.Text` | Voice/tone guidelines for all agents under this brand |
| `allowedTopics` | `Json` | Array of topics the brand permits |
| `restrictedTopics` | `Json` | Array of topics the brand forbids |
| `policyRules` | `Json` | `PolicyRule[]` — brand-level retrieval scoring rules |

**API:** `src/routes/brands.ts` — Full CRUD with Joi validation and tenant isolation.
**Agent assignment:** `Agent.brandId` field; set during onboarding or later via API.

---

## Claim 7 — Real-Time Knowledge Updates (Continuous Improvement Loop)

**Retraining pipeline:** `src/services/retrainingService.ts`

1. Business rates/flags bad calls → `CallLog.flaggedForRetraining = true` (via `POST /api/logs/:id/flag`)
2. Nightly cron (`src/services/retrainingScheduler.ts`) runs `processFlaggedCallLogs()`:
   - Extracts user-query / bad-response pairs from transcript
   - Creates `RetrainingExample` records (status: "pending")
   - Marks CallLog as `retrained: true`
3. Admin reviews examples (`/dashboard/retraining` page), edits ideal response, approves
4. Approved examples loaded by `getApprovedExamples()` → injected into `AssembledContext.fewShotExamples`
5. `buildSystemPrompt()` includes them as **LEARNED EXAMPLES** section (in-context learning)
6. Agent immediately responds better to similar queries — **no fine-tuning needed**

**Schema:** `model RetrainingExample` with status tracking and audit fields.
**Admin UI:** `app/dashboard/retraining/page.tsx`

---

## Claim 8 — Multi-Channel Delivery

| Channel | Implementation | File |
|---------|---------------|------|
| **Twilio voice** | TwiML webhooks, `<Gather>` + `<Say>` loop | `src/routes/twilioVoice.ts` |
| **WebRTC browser calls** | Socket.IO signaling, Groq Whisper STT + Chatterbox TTS (server-side) | `src/services/webrtcService.ts` |
| **Web chat** | REST API `POST /api/runner/chat` | `src/routes/runner.ts` |
| **Embeddable widget** | Self-contained JS snippet | `src/routes/widget.ts` (`GET /api/widget/:agentId/embed.js`) |

All channels share the same RAG pipeline: ContextInjector → queryDocuments → policyScoring → promptAssembly → LLM.

---

## Claim 9 — Per-Tenant Twilio Credentials (Encrypted)

**File:** `src/services/twilioClientService.ts`
**Encryption:** AES-256-GCM with per-deployment `TWILIO_ENCRYPTION_KEY`
**Storage:** `Tenant.settings.twilioCredentials` (encrypted JSON in Postgres)
**API:** `POST /api/settings/twilio` (save), `GET /api/settings/twilio` (status), `DELETE /api/settings/twilio` (remove)

---

## Claim 10 — Agent Template System

**Schema:** `model AgentTemplate` with `baseSystemPrompt`, `defaultCapabilities`, `suggestedKnowledgeCategories`, `defaultTools`
**Seeded templates:** 6 industry-specific templates (Customer Support, Sales, Healthcare, Legal, etc.)
**API:** `src/routes/templates.ts` — CRUD operations, template selection during onboarding
**Usage:** Template's `baseSystemPrompt` is used as the base for dynamic prompt assembly with `{{placeholder}}` replacement.

---

## Claim 11 — Automated Document Ingestion

**Service:** `ingestion-service/main.py` (FastAPI + Sentence-Transformers)

| Source | Endpoint | Processing |
|--------|----------|-----------|
| URLs | `POST /ingest` | Trafilatura / Playwright / Crawl4AI |
| S3 files | `POST /ingest` | PDF (pdfminer), DOCX, PPTX, XLSX, images (OCR) |
| Company website | `POST /ingest/company` | Multi-page crawl with smart scraping |

**Chunking:** `RecursiveCharacterTextSplitter` (1000 chars, 200 overlap)
**Embeddings:** `all-MiniLM-L6-v2` via `SentenceTransformer`
**Storage:** ChromaDB collection `tenant_{tenantId}` with `agentId` metadata

---

## Claim 12 — Call Analytics and Post-Call Analysis

**CallLog persistence:** `model CallLog` with transcript, duration, rating, analysis JSON
**Post-call analysis:** `src/services/callAnalysis.ts` — LLM-powered analysis stored in `CallLog.analysis`
**Analytics API:** `src/routes/analytics.ts` — Real Prisma queries for:
- `/analytics/overview` — Total calls, avg duration, success rate
- `/analytics/realtime` — Live metrics
- `/analytics/metrics-chart` — Time-series data
- `/analytics/agent-comparison` — Per-agent performance

---

## Claim 13 — Tenant Rate Limiting

**File:** `src/middleware/rateLimit.ts`
**Method:** `createTenantRateLimit(redis)` — Per-tenant sliding window rate limiter using Redis
**Applied globally** via `app.use(createTenantRateLimit(redis))` in index.ts

---

## Claim 14 — Guided Agent Onboarding

**Backend:** `src/routes/onboarding.ts` — Multi-step wizard API
**Frontend:** `app/onboarding/` — 7-step flow:
1. Company setup (with auto-scraping)
2. Agent template selection
3. Knowledge upload (files + URLs)
4. Voice personality configuration
5. Channel setup (Twilio/WebRTC)
6. Agent configuration (name, role, behaviour)
7. Deployment + go-live

**Progress persistence:** `model OnboardingProgress` — Server-side resume support

---

## Claim 15 — WebRTC Voice Channel (Twilio-Free)

**Signaling:** `src/services/webrtcService.ts` — Socket.IO server on `/ws`
**Widget:** `src/routes/widget.ts` — Embeddable `<script>` tag
**Server STT:** Groq Whisper (`whisper-large-v3-turbo`) — client sends audio via Socket.IO binary, server transcribes
**Server TTS:** Chatterbox TTS via `synthesiseForWebRTC()` — server generates speech, returns audio URL to client
**Pipeline:** Same ContextInjector → RAG → Policy → Prompt → LLM as Twilio calls (conversation history included in all paths)

---

## Partially Implemented Claims

| Claim | Gap | What remains |
|-------|-----|-------------|
| Fine-tuning | Only in-context learning (few-shot) is implemented | Full model fine-tuning via LoRA/QLoRA not implemented (by design — too slow/expensive for MVP) |
| Multi-language | Agent `language` field exists in onboarding | No automatic language detection or translation pipeline |
| Custom TTS voices | Voice cloning endpoint exists (`POST /api/tts/clone-voice`) with quality validation | Chatterbox TTS integration works; upload validated for format, size, and duration with actionable feedback |

---

## Architecture Diagram (for patent figures)

```
┌────────────────────────────────────────────────────────────┐
│                    INBOUND CHANNELS                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │  Twilio   │  │  WebRTC  │  │ Web Chat │  │  Widget   │ │
│  │  Voice    │  │  Socket  │  │  REST    │  │  Embed    │ │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬─────┘ │
└────────┼──────────────┼────────────┼──────────────┼────────┘
         │              │            │              │
         └──────────────┼────────────┼──────────────┘
                        ▼
              ┌──────────────────┐
              │ Tenant Resolution │
              │  (Auth / Lookup)  │
              └────────┬─────────┘
                       ▼
              ┌──────────────────┐
              │ Context Injector  │ ◄── 5-Layer Hierarchy
              │  (Prisma + Redis) │     Global → Tenant → Brand
              └────────┬─────────┘     → Agent → Session
                       ▼
         ┌─────────────┴─────────────┐
         ▼                           ▼
┌──────────────────┐     ┌────────────────────┐
│  ChromaDB Query   │     │  Few-Shot Examples  │
│  (tenant-isolated)│     │  (Retraining DB)    │
└────────┬─────────┘     └──────────┬─────────┘
         │                          │
         ▼                          │
┌──────────────────┐                │
│  Policy Scoring   │                │
│  (restrict/boost) │                │
└────────┬─────────┘                │
         │                          │
         └──────────┬───────────────┘
                    ▼
         ┌──────────────────┐
         │ Prompt Assembly   │ ◄── 7-Section System Prompt
         │  (buildSystemPrompt) │
         └────────┬─────────┘
                  ▼
         ┌──────────────────┐
         │    Groq LLM      │
         │  (Generation)     │
         └────────┬─────────┘
                  ▼
         ┌──────────────────┐
         │   TTS Synthesis   │ ◄── Chatterbox / Polly (Twilio & WebRTC: server-side)
         └────────┬─────────┘
                  ▼
         ┌──────────────────┐
         │ Response Delivery │ ◄── TwiML / Socket.IO / REST JSON
         └────────┬─────────┘
                  ▼
         ┌──────────────────┐
         │  CallLog + Analysis│ ◄── Persistent storage + LLM analysis
         └──────────────────┘
```
