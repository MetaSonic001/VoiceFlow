# VoiceFlow Frontend — Page-by-Page UI Inventory

This document describes what each sidebar page displays, which controls exist, and what they do. It is based on the Django templates under `frontend/templates/` and the sidebar definition in `frontend/templates/partials/sidebar.html`.

**Note:** In the sidebar, **Billing** and **Audit** are separate items: **Billing & Usage** (`/dashboard/billing/`) and **Audit Logs** (`/dashboard/audit/`). There is no single combined “Billing & Audit” page.

---

## Table of contents

1. [AI Agents](#1-ai-agents)
2. [Voice Agent](#2-voice-agent)
3. [Voice Library](#3-voice-library)
4. [Campaigns](#4-campaigns)
5. [Agent Builder](#5-agent-builder)
6. [Create Agent](#6-create-agent)
7. [Webhooks](#7-webhooks)
8. [Settings](#8-settings)
9. [Billing & Usage](#9-billing--usage)
10. [Phone Numbers](#10-phone-numbers)
11. [SIP Trunking](#11-sip-trunking)
12. [Live Monitor](#12-live-monitor)
13. [Reports](#13-reports)
14. [Analytics](#14-analytics)
15. [Audit Logs](#15-audit-logs)
16. [Team](#16-team)

---

## 1. AI Agents

**Route:** `/dashboard/`  
**Template:** `dashboard/index.html`  
**Sidebar label:** AI Agents

### Purpose

Main dashboard: workspace overview, agent list, recent calls, and quick navigation.

### Header

| Element | Function |
|--------|----------|
| **Title** “Dashboard” | Page heading |
| **+ Create Agent** | Links to onboarding flow (`/onboarding/`) |

### First-time / empty workspace

| Element | Function |
|--------|----------|
| Welcome card | Shown when there are zero agents; explains LLM key requirement |
| **Create Your First Agent** | → onboarding |
| **Help** | Opens modal with getting-started steps (Settings → Create Agent → Knowledge → Deploy) |
| **Got it!** | Closes help modal |

### KPI cards (6)

Each card shows a metric and a small sparkline chart:

- Total Agents  
- Active (status `active`)  
- Interactions  
- Success Rate  
- Avg Response  
- Satisfaction  

Data is bootstrapped from server JSON (`agents`, `metrics`).

### Quick Actions (4 tiles)

| Tile | Destination |
|------|----------------|
| Create Agent | Onboarding |
| Upload Doc | Knowledge Base |
| Start Campaign | Campaigns |
| View Analytics | Analytics |

### Recent Calls

- Table: Agent, Duration, Status (badge), Time  
- **View all →** → Call Logs (`/dashboard/calls/`)  
- Loads last 8 calls via `GET /api/call-logs/?limit=8`

### Agents section

| Element | Function |
|--------|----------|
| **Search agents…** | Filters agent cards by name |
| **All / Active / Paused / Draft** | Status filter buttons |
| **Agent cards** (grid) | Click card → agent detail (`/dashboard/agents/{id}/`) |
| Per card: name, role/template, status badge, call count, success % | Display only |
| **Chat** | → agent chat (`/dashboard/agents/{id}/chat/`) |
| **Pause / Activate** | `POST /api/agents/{id}/pause/` or `activate/` |
| **Delete** | Confirm dialog → `DELETE /api/agents/{id}/` |
| Empty state **Create Agent** | → onboarding |

### Global chrome (all dashboard pages)

- Left sidebar: navigation sections (Core, Channels, Intelligence, Data, Platform, Admin)  
- Bottom: user email, **Sign Out**

---

## 2. Voice Agent

**Route:** `/dashboard/voice-agent/`  
**Template:** `dashboard/voice_agent.html`

### Purpose

Browser-based voice conversation test bench: pick an agent, voice, talk via mic, see transcript.

### Header

| Element | Function |
|--------|----------|
| **Agent dropdown** | Select agent; resets session and loads background-sound config |

### Agent Voice panel

| Element | Function |
|--------|----------|
| **Kokoro TTS** tab | Local Kokoro + clone voices grid |
| **Edge TTS (13 voices)** tab | Cloud Edge voices |
| **Clone Voice** | Disabled; labeled “Soon” |
| Voice cards | Click to select; hover **play** previews via `POST /api/tts/preview/` |
| **Preview selected** | Plays current voice sample |
| Link **Open Voice Library / Create Voice Clone** | → Voice Library `#clone-section` |

### Main voice UI (dark visualization area)

| Element | Function |
|--------|----------|
| State indicator | idle / listening / processing / speaking (animated) |
| Waveform bars | Visual feedback by state |
| **liveTranscript** | Current utterance text overlay |
| **Mute / Unmute** | Mutes TTS playback |
| **Continuous** toggle | Auto listen → reply → listen loop |
| **Large mic button** | Hold-to-talk (non-continuous) or click toggle (continuous); disabled without agent |
| **End session (X)** | Stops audio, closes WebSocket, clears transcript |

WebSocket: `ws://{host}:8040/api/voice/ws/{agentId}` with audio chunks and `config` (voiceId).

Fallback: `POST /api/tts/` or browser `speechSynthesis` on errors.

### Conversation Transcript

Scrollable user/agent message list for the session.

### Background Ambient Sound (when agent selected)

| Element | Function |
|--------|----------|
| Ambient type radio | none, office, callcenter, café, street |
| Volume slider | 0–100% |
| **Save** | `PUT /api/background-sound/{agentId}/` |

---

## 3. Voice Library

**Route:** `/dashboard/voice-library/`  
**Template:** `dashboard/voice_library.html`

### Purpose

Browse catalog voices, preview, assign to agents, manage voice clones.

### Header

| Element | Function |
|--------|----------|
| Voice count subtitle | Filtered count from catalog |
| **+ Clone a Voice** | Scrolls to clone section |

### Filter bar

| Element | Function |
|--------|----------|
| Search | Name, language, style, accent |
| **All Languages** dropdown | Filter by language code |
| **All Genders** | Female / Male |
| **Provider pills** | edge, sarvam, kokoro, piper (with counts; KEY badge if API key missing) |
| **Category pills** | e.g. professional, conversational, etc. |
| **Clear filters** | Resets all filters |

Catalog: `GET /api/voices/catalog/`. Pagination: 24 per page, Prev/Next.

### Voice grid

Each card: provider badge, avatar, name, language, style, category tags, hover **preview** (`POST /api/voices/preview/`). Click card → selection panel below.

### Selected voice panel

| Element | Function |
|--------|----------|
| **Preview** | Play sample |
| **Assign to agent…** dropdown + **Use this voice** | `PUT /api/agents/{id}/` with `llmPreferences.voiceId` |

### Cloned Voices section (`#clone-section`)

| Element | Function |
|--------|----------|
| **+ New Clone** / **Cancel** | Toggle upload form |
| Clone name, Primary language | Form fields |
| Drag-and-drop / click upload | MP3, WAV, WebM, OGG; max 50 MB |
| **Upload Clone** | `POST /api/voices/clones/` |
| Clone cards | Preview, assign **Use**, delete |
| Empty state | Prompt to upload |

---

## 4. Campaigns

**Route:** `/dashboard/campaigns/`  
**Template:** `dashboard/campaigns.html`

### Purpose

Outbound calling campaigns: create, upload contacts, start/pause, live stats.

### Header

| Element | Function |
|--------|----------|
| **New Campaign** | Opens create modal |

### Create Campaign modal

| Field | Required |
|-------|----------|
| Campaign Name | Yes |
| Agent | Yes (dropdown from agents API) |
| Scheduled Start | Optional datetime |
| **Create** | `POST /api/campaigns/` |
| **Cancel** | Close modal |

### Upload Contacts CSV modal

| Element | Function |
|--------|----------|
| Drag-drop / file picker | `.csv` only, max 5 MB |
| Required column | `phone_number`; optional `name` + variables |
| **Upload** | `POST /api/campaigns/{id}/contacts/upload/` |
| **Cancel** | Close |

### Campaign cards (grid)

**Displayed per campaign:**

- Name, assigned agent name  
- Status badge: running, paused, draft/pending, completed  
- Progress bar: answered vs total  
- Stats: Total, Answered, Failed  
- Retry breakdown: 1st try, 2nd try, 3rd try, Max hit  

**Actions:**

| Button | Function |
|--------|----------|
| **CSV** | Open upload modal for that campaign |
| **Start** | `POST /api/campaigns/{id}/start/` (when not running) |
| **Pause** | `POST /api/campaigns/{id}/pause/` (when running) |

Stats refresh every 5 seconds via `GET /api/campaigns/{id}/stats`.

Empty state: **Create First Campaign**.

---

## 5. Agent Builder

**Route:** `/dashboard/agents/builder/` (optional `?agent_id=` for existing agent)  
**Template:** `agents/builder.html`  
**Sidebar label:** Agent Builder

### Purpose

Visual conversation flow editor (n8n-style canvas): nodes, edges, inspector, save to agent.

### Header

| Element | Function |
|--------|----------|
| **Back arrow** | Agent detail if `agent_id`, else agents list |
| Title | Agent name or “New Agent Flow” |
| **Auto-generate** | Scaffolds flow from agent context/knowledge (existing agent only, empty canvas) |
| **Flow Map** | Toggle Mermaid diagram panel |
| **Save Flow** | Creates agent if new (name required), then `POST /api/agents/{id}/flow/` |

### Flow Map panel (optional)

Mermaid flowchart; **Refresh** renders from nodes/edges.

### Left palette — Add Nodes

| Node type | Role |
|-----------|------|
| Start | Entry |
| Greeting | Opening message |
| Instruction | Agent instruction step |
| Collect slot | Slot collection |
| Knowledge | RAG / knowledge lookup |
| Condition | Branch yes/no |
| API Call | Tool invocation |
| Human Transfer | Transfer to number |
| End | Terminate |

**View controls:** Zoom In, Zoom Out, Fit All, Reset.

### Canvas

- Pan (drag background), zoom (wheel)  
- Drag nodes; connect **output port** (green) → **input port** (grey)  
- Selected node: red **✕** delete (not on Start)  
- Footer: zoom %, canvas height +/- , node/edge count  

### Right inspector (selected node)

| Field | Applies to |
|-------|------------|
| Label | All |
| Type | All (change node type) |
| Message / Prompt | greeting, end, knowledge |
| Condition + Yes/No → Node | condition |
| Tool Name | api_call |
| Transfer Number | human_transfer |
| Next Node | non-condition, non-end |
| X, Y | Position |
| **Agent Name** | New agent only (required to save) |
| **Flow JSON** (readonly, collapsible) | Debug export |

Empty canvas hint: add from palette or Auto-generate.

---

## 6. Create Agent

**Route:** `/dashboard/agents/create/`  
**Template:** `agents/creator.html`

### Purpose

Choose creation path: AI prompt wizard vs visual flow builder.

### Method selection (initial screen)

| Card | Action |
|------|--------|
| **Prompt to Agent** | Starts 5-step wizard (`mode = 'prompt'`) |
| **Visual Flow Builder** | Navigates to `/dashboard/agents/builder/` |

**Back to Agents** link → `/dashboard/agents/` (note: main list is `/dashboard/`).

### Prompt wizard — progress steps

1. Describe  
2. Sections  
3. Voice  
4. Variables  
5. Done  

### Step 0 — Describe

| Element | Function |
|--------|----------|
| Textarea | Business/agent description (1–3 sentences) |
| Live **Detected** chips | Debounced intent extract: `POST .../generate-from-prompt/preview/` with `extract_only: true` |
| **Generate Agent →** | Full preview generation → Step 1 |

### Step 1 — Sections

| Element | Function |
|--------|----------|
| Editable agent name & description | Top card |
| **Context Sections** | Drag-reorder, edit title/body, enable toggle, quality stars, Auto-Compliance badge |
| **+ Add Section** | New section |
| Edit / Done / Delete (non-compliance) | Per section |
| **Caller Personas** | Read-only cards: name, frustration, goal, sample utterance |
| **← Back** / **Next: Voice & Welcome →** | Navigation |

### Step 2 — Voice

| Element | Function |
|--------|----------|
| Welcome message textarea | First spoken line |
| **Preview Voice** | `POST /api/tts/` |
| Female / Male voice type buttons | |
| Language config chips | From generated config |
| **← Back** / **Next: Data Extraction →** | |

### Step 3 — Variables

Post-call extraction variables: variable name, extraction prompt, data type (text, date, phone, number, yes/no).

| Element | Function |
|--------|----------|
| **+ Add Variable** | New row |
| **✕** | Remove row |
| **Create Agent →** | `POST .../generate-from-prompt/create/` with `auto_simulate: true` |

### Step 4 — Done

| Element | Function |
|--------|----------|
| Readiness score circle | Grade + summary (if returned) |
| Improvement Opportunities | Gap list by priority |
| Auto-Generated Test Suite | Scenario list (run in agent Test tab) |
| **Open Agent Dashboard →** | Agent detail |
| **Open Flow Builder** | Workflow page |
| **Create Another Agent** | Reset create flow |

---

## 7. Webhooks

**Route:** `/dashboard/webhooks/`  
**Template:** `dashboard/webhooks.html`

### Purpose

Register HTTPS endpoints for platform events (HMAC-SHA256 signed).

### Header

| Element | Function |
|--------|----------|
| **Import to Zapier / n8n** | Opens `/api/webhooks/schema` (new tab) |
| **Add Endpoint** | Toggle create form |

### New Endpoint form

| Field | Function |
|-------|----------|
| Endpoint URL * | HTTPS webhook URL |
| Description | Optional |
| Events * | Checkboxes: `call.completed`, `campaign.finished`, `escalation.triggered`, `retraining.flagged` |
| **Save Endpoint** | `POST /api/webhooks/` |
| **Cancel** | Close form and reset |

### Registered Endpoints table

Columns: URL, Events (tags), Status (Active/Inactive), Secret (masked last 4), Created, **Delete**.

`GET /api/webhooks/` on load.

### Supported Events reference

Documentation cards for each event type + security note (`X-VoiceFlow-Signature`).

---

## 8. Settings

**Route:** `/dashboard/settings/`  
**Template:** `dashboard/settings.html`

### Purpose

BYOK API keys, telephony credentials, general workspace flags. Keys described as AES-256-GCM encrypted.

### Tabs

LLM Providers | Voice & Speech | Telephony | General

### LLM Providers tab

Per provider card (Groq, OpenAI, Anthropic, Gemini):

| Element | Function |
|--------|----------|
| Status badge | Configured / Not set / Using default (Groq) |
| Masked current key display | If configured |
| Password input + **Save Key** | `POST /api/settings/{provider}/` |
| **Remove** | `DELETE` with confirm |

External “Get key” links to each provider console.

### Voice & Speech tab

Same pattern for:

- **ElevenLabs** (TTS)  
- **Sarvam AI** (TTS + STT)  
- **Deepgram** (STT)  
- **AssemblyAI** (STT)  

### Telephony tab

**Twilio:** Account SID, Auth Token → **Save Credentials** / **Remove**

**Exotel:** Account SID, API Key, API Token → **Save Exotel Credentials** / **Remove**

**SIP Trunking (BYOC):** Server, Username, Password, From Number → **Save SIP Credentials** / **Remove**; help text + link to SIP Trunking page

**Truecaller Business:** Partner key for caller enrichment → Save / Remove

### General tab

| Checkbox | Maps to |
|----------|---------|
| Email notifications | `notifications.emailNotifications` |
| Maintenance mode | `system.maintenanceMode` |
| Debug logging | `system.debugLogging` |

**Save Settings** → `PUT /api/settings/`

Key statuses loaded server-side via `all_keys` in template.

---

## 9. Billing & Usage

**Route:** `/dashboard/billing/`  
**Template:** `dashboard/billing.html`  
**Sidebar label:** Billing & Usage

### Purpose

Usage snapshot and plan comparison (no payment UI in beta).

### Sections

| Section | Content |
|---------|---------|
| **FREE BETA** banner | All features during beta |
| Usage cards (3) | Agents Created, Conversations Logged, Documents Indexed (server-rendered counts) |
| **Plan Comparison** | Three columns |

### Plans

| Plan | Price | Notes |
|------|-------|-------|
| **Free Beta** (current) | $0/mo | Up to 5 agents, 100 conversations/mo, 50 MB docs, community support |
| **Pro** | $49/mo | **Coming Soon** (disabled button) |
| **Enterprise** | Custom | **Contact Sales** (disabled button) |

No interactive billing actions on this page (read-only + disabled upgrade buttons).

---

## 10. Phone Numbers

**Route:** `/dashboard/phone-numbers/`  
**Template:** `dashboard/phone_numbers.html`

### Purpose

Search/buy Twilio numbers, assign to agents, release numbers.

### Header

| Element | Function |
|--------|----------|
| **Buy Number** | Opens search modal |

### Your Numbers table

Columns: Number, Provider, Capabilities (Voice/SMS), Assigned Agent, Actions.

| Action | Function |
|--------|----------|
| **Assign agent** dropdown | `POST /api/phone-numbers/{phone}/assign` |
| **Unassign** | When assigned |
| **Release** | Confirm modal → `DELETE /api/phone-numbers/{sid}` |

`GET /api/phone-numbers/owned`

### Buy a Phone Number modal

| Filter | Options |
|--------|---------|
| Country | US, GB, IN, AU, CA, DE, SG, AE |
| Type | local, toll_free, mobile |
| Area Code | Optional |
| **Search** | `GET /api/phone-numbers/search` |

Results: number, location, monthly price, Voice/SMS badges, **Buy** (confirm → `POST /api/phone-numbers/purchase`).

Requires Twilio credentials in Settings.

### India / Exotel info card

Links to Exotel dashboard and Settings for Indian DLT numbers (not purchased through this UI).

---

## 11. SIP Trunking

**Route:** `/dashboard/sip-trunking/`  
**Template:** `dashboard/sip_trunking.html`

### Purpose

Per-trunk BYOC configuration (distinct from global SIP credentials in Settings).

### Header

| Element | Function |
|--------|----------|
| **Add SIP Trunk** | Opens create modal |

### Info banner

Explains routing inbound calls via carrier to VoiceFlow webhook URI.

### Trunk cards

**Display:** name, provider badge (Twilio BYOC / Generic SIP), Active/Inactive, SIP URI, From number, Agent ID, Updated date, inbound webhook URI (copy button).

| Action | Function |
|--------|----------|
| **Test** | `POST /api/sip-trunking/trunks/{id}/test/` |
| **Delete** | Confirm → `DELETE` |
| **Copy webhook** | Clipboard |

Webhook URI loaded via `GET /api/sip-trunking/webhook-uri/{agentId}/`

### Add SIP Trunk modal

| Field | Notes |
|-------|-------|
| Trunk Name * | |
| Provider * | twilio_byoc \| generic_sip |
| SIP URI * | |
| SIP Username / Password | |
| Twilio Account SID / Auth Token | Shown for twilio_byoc |
| Agent ID | Routes inbound calls |
| From Number | Outbound CLI |
| **Save Trunk** | `POST /api/sip-trunking/trunks/` |
| **Cancel** | |

---

## 12. Live Monitor

**Route:** `/dashboard/live-monitor/`  
**Template:** `dashboard/live_monitor.html`

### Purpose

Supervisor view of active calls: transcript, takeover, whisper, end call.

### Header

| Element | Function |
|--------|----------|
| Live pulse indicator | Visual “on air” |
| Active call count | Auto-refresh every 3s |
| **Refresh** | Manual `GET /api/live-monitor/calls` |

### Empty state

“No active calls right now.”

### Per-call card

**Display:** caller number, agent name, state (listening/thinking/speaking), duration, sentiment badge, last ~4 transcript turns, extracted variable chips.

| Button | Function |
|--------|----------|
| **Monitor** | Full transcript modal |
| **Take Over** | Transfer modal |
| **End call** (phone icon) | `POST .../calls/{sid}/end` |

### Monitor modal

Full transcript; **supervisor note** + **Note** (`POST .../note`); **Whisper** hint to agent (`POST .../whisper` — caller does not hear).

### Take Over modal

| Field | Function |
|-------|----------|
| Transfer to (E.164) * | Human agent number |
| Whisper message | Heard by agent receiving transfer |
| **Transfer Now** | `POST .../takeover` |
| **Cancel** | |

---

## 13. Reports

**Route:** `/dashboard/reports/`  
**Template:** `dashboard/reports.html`

### Purpose

Generate named report jobs and download CSV exports.

### Generated reports list

Grid of cards: report name, type + created date, **Download** (builds CSV client-side from APIs).

Initial list from server `reports` context.

### Generate Report panel

| Field | Options |
|-------|---------|
| Type | Analytics Summary, Call Logs, Agent Performance |
| Period | Last 7 / 30 / 90 days |
| **Generate** | `POST /api/reports/` |

**Download** logic:

- Call Logs → `/api/call-logs/` CSV  
- Agent Performance → `/api/agents/` CSV  
- Analytics Summary → `/api/analytics/overview/` key-value CSV  

---

## 14. Analytics

**Route:** `/dashboard/analytics/`  
**Template:** `dashboard/analytics.html`

### Purpose

Operational and BI analytics with time range, charts, and CSV export.

### Header

| Element | Function |
|--------|----------|
| **7d / 30d / 90d** | Reloads all metrics and charts |

### KPI rows (server + dynamic)

**Row 1:** Total Interactions, Success Rate, Avg Response Time, Active Agents  

**Row 2 (API):** Resolution Rate, Escalation Rate, Avg Cost/Call, Avg Quality Score  

**Row 3 (BI summary):** Conversion rate, Qualification rate, Recording coverage, Channels (phone/chat avg duration)

### Quick links

Conversations, Live monitor, Campaigns, Recordings, **Export CSV** → `/api/analytics/export.csv?timeRange=`

### Agent leaderboard table

Agent, Interactions, Conv. rate, Avg duration (from BI API).

### Charts (Chart.js)

| Chart | API |
|-------|-----|
| Interactions Over Time | `/api/analytics/overview/` |
| Top Intents (horizontal bar) | `/api/analytics/top-intents/` |

### Bottom panels

- **Agent Performance** — static list from template: calls + chats per agent  
- **Top Failure Modes** — missed opportunities, hallucination risk stats (`/api/analytics/failure-modes/`)

---

## 15. Audit Logs

**Route:** `/dashboard/audit/`  
**Template:** `dashboard/audit.html`  
**Sidebar label:** Audit Logs

### Purpose

Compliance / security audit trail of user and system actions.

### Header

| Element | Function |
|--------|----------|
| Total entries count | |
| **Refresh** | `GET /api/audit/?limit=200` |

### Filters

| Element | Function |
|--------|----------|
| Text search | action, user, resource |
| Action dropdown | All, create, update, delete, login |

### Table columns

Time, User, Action (color-coded badge), Resource, IP

Initial data server-rendered; filtering is client-side.

---

## 16. Team

**Route:** `/dashboard/users/`  
**Template:** `dashboard/users.html`  
**Sidebar label:** Team

### Purpose

Workspace user management (name, email, role).

### Header

| Element | Function |
|--------|----------|
| **Add User** | Opens create modal |

### Users table

Columns: Name, Email, Role (admin badge vs user), Actions.

| Action | Function |
|--------|----------|
| **Edit** | Modal with existing user |
| **Delete** | Confirm → `DELETE /api/users/{id}/` |

### Add / Edit User modal

| Field | Options |
|-------|---------|
| Name | |
| Email | |
| Role | user \| admin |
| **Save** | `POST /api/users/` or `PUT /api/users/{id}/` |
| **Cancel** | |

---

## Shared UI patterns (all dashboard pages)

| Pattern | Behavior |
|---------|----------|
| `vf-card`, `vf-btn`, badges | Consistent Tailwind + Alpine styling |
| `vfConfirm` | Destructive action confirmations |
| `showToast` / `vfToast` | Success/error notifications |
| `apiFetch` | JSON API helper with CSRF |
| `base_dashboard.html` | Layout: sidebar, main content, dark mode classes |
| Alpine.js (`x-data`) | Client-side state and API calls |

---

## Sidebar mapping reference

| Sidebar label | URL |
|---------------|-----|
| AI Agents | `/dashboard/` |
| Voice Agent | `/dashboard/voice-agent/` |
| Voice Library | `/dashboard/voice-library/` |
| Campaigns | `/dashboard/campaigns/` |
| Agent Builder | `/dashboard/agents/builder/` |
| Create Agent | `/dashboard/agents/create/` |
| Webhooks | `/dashboard/webhooks/` |
| Settings | `/dashboard/settings/` |
| Billing & Usage | `/dashboard/billing/` |
| Phone Numbers | `/dashboard/phone-numbers/` |
| SIP Trunking | `/dashboard/sip-trunking/` |
| Live Monitor | `/dashboard/live-monitor/` |
| Reports | `/dashboard/reports/` |
| Analytics | `/dashboard/analytics/` |
| Audit Logs | `/dashboard/audit/` |
| Team | `/dashboard/users/` |

---

*Generated from the VoiceFlow frontend templates. Update this file when templates or routes change.*
