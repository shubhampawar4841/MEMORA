# Nerva

**Personal AI assistant with persistent memory, document knowledge, web agent tools, Telegram, and voice.**

Nerva (repo: **Memora**) is a single-user knowledge workspace: upload documents, connect external sources, search a long-term memory layer powered by [Supermemory](https://supermemory.ai), chat with a planner-routed agent (RAG + web), talk over LiveKit voice, and message a Telegram bot. It is **not** a generic multi-tenant SaaS yet — it is built around one configured user (`NERVA_USER_ID`) and local/self-hosted deployment.

---

## Overview

### What is Nerva?

Nerva combines:

1. **A web dashboard** (Next.js) for chat, knowledge base, memory graph, integrations, and voice calls.
2. **A FastAPI backend** for ingestion, retrieval, agent orchestration, OAuth bridges, and webhooks.
3. **Supermemory** as the default memory/RAG backend (hosted indexing, profile, connectors, MCP).
4. **Optional local RAG** (Chroma + Qwen embeddings + BGE reranker) when explicitly enabled.
5. **Telegram** as a mobile text interface with Supermemory search and file upload.
6. **LiveKit voice** as a realtime speech interface with MCP toolsets (Supermemory, Firecrawl, Google Workspace, GitHub).

### What problem does it solve?

It gives one person a **memory-backed assistant** that can answer from uploaded docs and synced connectors, browse the live web when needed, remember notes, accept files from Telegram, and speak over voice — instead of a stateless chatbot with no persistent knowledge.

### How is it different from a normal chatbot?

- **Persistent memory** via Supermemory (profile, documents, hybrid search, graph in UI).
- **Planner-routed agent** chooses RAG vs web vs hybrid vs ingest paths (`app/agent/planner.py`).
- **Tool use** via MCP (Firecrawl web tools; Supermemory MCP on Telegram/voice).
- **Multiple interfaces** (web, Telegram, voice) over one backend and memory layer.
- **Document pipeline** with folders, reindex, and Supermemory sync.

---

## Architecture

Derived from the codebase (not aspirational):

```text
                         ┌─────────────────────────────────────┐
                         │           User interfaces            │
                         ├──────────┬──────────┬───────────────┤
                         │ Next.js  │ Telegram │ LiveKit voice │
                         │  :3000   │ webhook  │    worker     │
                         └────┬─────┴────┬─────┴───────┬───────┘
                              │          │             │
                              ▼          ▼             ▼
                    ┌─────────────────────────────────────────┐
                    │     FastAPI (app/main.py) — local full   │
                    │  OR Vercel slim (health + Telegram only) │
                    └─────────┬───────────────────┬─────────────┘
                              │                   │
         ┌────────────────────┼───────────────────┼────────────────────┐
         ▼                    ▼                   ▼                    ▼
   Documents/chat        Agent orchestrator   Telegram service    Voice token API
   Memory routers        Planner + gateway    nerva_telegram.py   /voice/token
         │                    │                   │                    │
         └──────────────┬─────┴─────────┬─────────┴────────────┬───────┘
                        ▼               ▼                      ▼
                 Supermemory HTTP   Groq LLM            LiveKit Inference
                 (REST v3/v4)       (text/agent/TG)     (STT/TTS/voice LLM)
                        │
                 Supermemory MCP ──── (Telegram search, voice search)
                        │
              Optional local RAG ─── Chroma + Qwen + BGE (LOCAL_RAG_ENABLED=true)
                        │
              Firecrawl MCP/SDK ──── web agent + optional web ingest
                        │
              Google OAuth bridge ── Gmail/Calendar MCP headers for voice worker
                        │
              GitHub remote MCP ──── live GitHub data in voice (GITHUB_TOKEN)
```

### Deployment surfaces

| Surface | Entry | What runs |
|---------|--------|-----------|
| **Local full stack** | `npm run dev` | FastAPI all routers + Next.js client |
| **Vercel serverless** | `backend/api/index.py` | Health + Telegram only (`app/vercel_app.py`) |
| **LiveKit worker** | `python run_voice_agent.py dev` | Voice agent process (separate from API) |

---

## How it works

### Memory & RAG (question → answer)

**Web UI / API search & chat (default: Supermemory REST)**

1. User asks via chat, search, or `/ask`.
2. `app/retrieval/factory.py` selects backend from `RAG_PROVIDER` / `LOCAL_RAG_ENABLED`.
3. Default: `SupermemoryRetriever` calls `POST /v4/search` with container tag `user_{NERVA_USER_ID}` (`app/supermemory/client.py`).
4. Hits are reranked by Supermemory; context is built (`app/agent/context.py` or `app/services/generation.py`).
5. **Groq** (`openai/gpt-oss-20b`) generates the answer (`app/llm.py`, `app/services/generation.py`).
6. Response streams (SSE) or returns JSON with citations.

**Telegram & voice (Supermemory MCP — no container tag on search)**

1. User message or voice utterance.
2. Telegram: `app/supermemory/mcp_client.py` → `search_memory` on `https://mcp.supermemory.ai/mcp` with profile included.
3. Voice: LiveKit `MCPToolset` with the same MCP endpoint (`app/voice/agent.py`).
4. Groq (Telegram) or LiveKit Inference LLM (voice) produces the reply from retrieved context.

> **Important:** MCP search and Telegram file upload use Supermemory’s **default account namespace**. REST routes and web uploads use **`SUPERMEMORY_CONTAINER_TAG` / `user_{NERVA_USER_ID}`**. Data may not appear in both scopes until aligned — this is a known architectural split.

### Agent / tool flow (web chat)

1. `POST /api/agent/chat/stream` → `app/agent/planner.py` routes to `rag`, `web`, `hybrid`, or `ingest_web`.
2. `app/agent/orchestrator.py` runs a Groq tool loop against `app/agent/gateway.py`.
3. Tools:
   - **RAG:** in-process `rag_search` (Supermemory or local Chroma depending on config).
   - **Web:** Firecrawl hosted MCP (search, scrape, crawl, map, interact).
4. `ContextBuilder` merges evidence; optional synthesis pass; streamed status events to client.

### Document upload (web)

1. `POST /upload-document` → `app/services/ingestion.py`.
2. File saved under `PDF_STORAGE_PATH`; metadata catalog updated.
3. If `LOCAL_RAG_ENABLED=true`: extract → chunk → embed → Chroma.
4. **Supermemory sync:** `app/supermemory/sync.py` → `POST /v3/documents/file` (Supermemory handles parse/OCR/indexing).

### Document upload (Telegram)

1. User sends photo/PDF or replies “upload …” to a file message.
2. `app/services/nerva_telegram.py` intent router resolves attachment (inline, reply-to, or 15‑min pending cache).
3. `telegram_client.download_file` → `sync_telegram_upload` → Supermemory file ingest **without container tag** (MCP-visible namespace).
4. User gets a confirmation message; indexing is async on Supermemory’s side.

---

## Core capabilities

Only items verified in code:

| Capability | Status | How | Key modules |
|------------|--------|-----|-------------|
| Web dashboard (chat, knowledge, memory, settings, voice UI) | ✅ Working locally | Next.js SPA → `client/lib/api.ts` | `client/app/page.tsx`, `client/components/**` |
| Document upload (PDF, images, text, docx, …) | ✅ Working | Multipart upload + Supermemory sync | `app/routers/documents.py`, `app/services/ingestion.py` |
| Supermemory hybrid search & profile | ✅ Working (with API key) | REST `/v4/search`, `/v4/profile` | `app/services/memory.py`, `app/routers/memory.py` |
| Memory graph & activity UI | ✅ Working (with API key) | Graph built from search results | `client/components/memory/**` |
| Agent chat (RAG / web / hybrid) | ✅ Working (Groq + optional Firecrawl) | Planner + orchestrator + MCP | `app/routers/agent.py`, `app/agent/**` |
| Classic RAG `/ask`, `/search` | ✅ Working | Retrieve + Groq | `app/routers/chat.py`, `app/routers/search.py` |
| Conversation history (JSON files) | ✅ Working locally | `CHATS_PATH` on disk | `app/services/conversations.py` |
| Supermemory Gmail/GitHub connectors | 🟡 Partial | OAuth via Supermemory; requires Scale/Enterprise | `app/services/connections.py` |
| Google OAuth (Gmail/Calendar for voice MCP) | 🟡 Partial | OAuth + token store + MCP bridge | `app/auth/**`, `app/routers/auth.py` |
| Telegram bot (search, remember, upload) | ✅ Working | Webhook + MCP + Groq | `app/services/nerva_telegram.py` |
| Telegram session / follow-up context | 🟡 Partial | In-memory; lost on Vercel cold start | `app/services/telegram_session.py` |
| LiveKit voice agent | 🟡 Partial | Separate worker; needs LiveKit + keys | `app/voice/agent.py`, `run_voice_agent.py` |
| GitHub live MCP (voice) | 🟡 Partial | Remote MCP with `GITHUB_TOKEN` | `app/voice/github_mcp*.py` |
| Local Chroma RAG | 🟡 Optional | Off by default (`LOCAL_RAG_ENABLED=false`) | `app/vectorstore/chroma.py`, `app/embeddings/qwen.py` |
| Website ingest API | ✅ Implemented | `POST /api/agent/ingest` | `app/services/web_ingest.py` |
| Website ingest UI | 🔜 Planned | Upload modal shows “Coming soon” | `client/components/overlays/UploadModal.tsx` |
| Eval harness | 🧪 Experimental | Offline metrics | `backend/eval/run_eval.py` |
| Vercel Telegram deploy | ✅ Working | Slim Python function | `backend/vercel.json`, `backend/api/index.py` |
| Multi-user auth / tenant isolation | ❌ Not implemented | Single `NERVA_USER_ID` | `backend/PRODUCTION.md` Phase G |

---

## Integrations

| Integration | Status | Purpose | Verification |
|-------------|--------|---------|--------------|
| **Supermemory (HTTP)** | ✅ Working | Primary memory, ingest, search, connectors | `app/supermemory/client.py` |
| **Supermemory (MCP)** | ✅ Working | Telegram + voice memory search | `app/supermemory/mcp_client.py`, `app/voice/agent.py` |
| **Groq** | ✅ Working | Text LLM (chat, agent, Telegram) | `app/llm.py` — **required** at import |
| **Firecrawl MCP** | ✅ Working (with key) | Web agent tools | `app/mcp/firecrawl_client.py` |
| **Firecrawl SDK** | ✅ Working (with key) | Web ingest, SDK-based tools | `app/firecrawl/client.py` |
| **Telegram Bot API** | ✅ Working (with token + webhook) | Text interface, file upload | `app/integrations/telegram_client.py` |
| **LiveKit** | 🟡 Partial | Voice rooms + agent dispatch | `app/routers/voice.py`, `app/voice/agent.py` |
| **LiveKit Inference** | 🟡 Partial | Voice STT/TTS/LLM | `app/voice/agent.py` |
| **Google OAuth** | 🟡 Partial | Gmail/Calendar tokens for voice MCP | `app/auth/google_oauth.py` |
| **Gmail (Supermemory connector)** | 🟡 Partial | Sync via Supermemory OAuth | `app/services/connections.py` |
| **GitHub (Supermemory connector)** | 🟡 Partial | Sync via Supermemory OAuth | `app/services/connections.py` |
| **GitHub (remote MCP, voice)** | 🟡 Partial | Live repo/issue context in voice | `app/voice/github_mcp.py` |
| **Notion / Slack / Discord** | ❌ Not implemented | — | Not in codebase |
| **PostgreSQL / Redis / S3** | ❌ Not implemented | Local JSON + filesystem only | `PRODUCTION.md` |

---

## Technology stack

Verified from `requirements-local.txt`, `client/package.json`, and imports:

### AI / LLM

| Component | Technology |
|-----------|------------|
| Text LLM | Groq — `openai/gpt-oss-20b` |
| Voice LLM | LiveKit Inference — `google/gemma-4-31b-it` |
| Voice STT | LiveKit Inference — `deepgram/nova-3` |
| Voice TTS | LiveKit Inference — `cartesia/sonic-3` |
| Agent framework | Custom planner + orchestrator + MCP gateway |
| Embeddings (optional local) | `sentence-transformers` — Qwen3-Embedding-0.6B |
| Reranker (optional local) | BGE cross-encoder — `BAAI/bge-reranker-v2-m3` |

### Memory / RAG

| Component | Technology |
|-----------|------------|
| Primary vector/memory | Supermemory API v3/v4 + MCP |
| Optional local store | ChromaDB |
| Chunking / extract | PyMuPDF, custom chunking (`app/chunking.py`, `app/services/extractors.py`) |

### Backend

| Component | Technology |
|-----------|------------|
| Language | Python 3.12+ (Vercel default) |
| Framework | FastAPI, Uvicorn |
| HTTP client | httpx |
| Serverless | Mangum (Vercel) |
| Async | asyncio (Telegram, httpx) |

### Frontend

| Component | Technology |
|-----------|------------|
| Framework | Next.js 16, React 19 |
| Styling | Tailwind CSS 4, shadcn/base-ui |
| Voice UI | LiveKit client SDK |
| Analytics | Vercel Analytics (production) |

### Infrastructure

| Component | Status |
|-----------|--------|
| Vercel | ✅ Backend Telegram deploy (`backend/vercel.json`) |
| Docker | ❌ Not configured |
| CI/CD (GitHub Actions) | ❌ Not configured |

---

## Engineering skills demonstrated

### AI engineering

- LLM integration (Groq, LiveKit Inference)
- RAG with hosted and optional local retrieval
- Agentic workflows (planner, tool loop, context builder)
- MCP orchestration (Supermemory, Firecrawl, Google, GitHub)
- Prompt engineering (planner, voice instructions, Telegram answers)
- Hybrid search and reranking (Supermemory + optional BGE)

### Backend engineering

- FastAPI router design and Pydantic schemas
- Webhook handling (Telegram) with secret validation
- OAuth flows (Google; Supermemory connector redirects)
- Service layer separation (ingestion, memory, connections, generation)
- Streaming SSE for agent and chat
- Dual deployment (monolith vs Vercel slim)

### Systems / realtime

- LiveKit voice worker architecture
- MCP HTTP/SSE clients
- In-memory session state (Telegram) with TTL
- External API orchestration and timeouts

### Data

- Document ingestion pipeline (multi-format)
- Supermemory file + text ingest
- JSON-file conversation persistence
- Local filesystem storage for originals

### Product

- Multi-surface assistant (web, Telegram, voice)
- File upload workflows with reply-to semantics
- Memory graph visualization
- Integrations panel for connectors

---

## Security

Mechanisms present in code (no secret values):

| Control | Implementation |
|---------|----------------|
| Telegram access | Allowlist via `TELEGRAM_CHAT_ID` (`app/services/nerva_telegram.py`) |
| Telegram webhook | Optional `TELEGRAM_WEBHOOK_SECRET` header validation |
| Google MCP bridge | `GOOGLE_MCP_BRIDGE_SECRET` on `/auth/google/mcp/headers` |
| API keys | Environment variables only; loaded in `app/config.py` |
| OAuth tokens | Stored server-side (`app/auth/token_store.py`, `backend/data/google_oauth/`) |
| CORS | Configurable `CORS_ORIGINS` (default `*`) |
| File upload validation | Extension allowlist (`app/services/file_types.py`) |
| Agent safety gate | Pauses on consequential tools (`app/agent/safety.py`) |

**Gaps (honest):**

- No authentication on most FastAPI routes (single-tenant prototype).
- No rate limiting.
- CORS defaults to `*` in `.env.example`.
- Secrets in `.env` must never be committed (`.gitignore` covers `.env`).
- Telegram session state is in-process only.

---

## Project structure

```text
Memora/
├── README.md                 # This file
├── package.json              # Root: npm run dev (backend + client)
├── scripts/
│   └── dev-backend.cmd       # Windows uvicorn launcher
├── client/                   # Next.js Nerva dashboard
│   ├── app/page.tsx          # Single-page app shell
│   ├── components/           # Chat, knowledge, memory, voice, …
│   └── lib/api.ts            # Backend API client
└── backend/
    ├── app/
    │   ├── main.py           # Full FastAPI app
    │   ├── vercel_app.py     # Slim app (Telegram + health)
    │   ├── config.py
    │   ├── agent/            # Planner, orchestrator, gateway, tools
    │   ├── auth/             # Google OAuth + MCP bridge
    │   ├── integrations/     # Telegram client
    │   ├── mcp/              # Firecrawl MCP client
    │   ├── routers/          # HTTP endpoints
    │   ├── services/         # Business logic
    │   ├── supermemory/      # HTTP client, MCP client, sync
    │   ├── voice/            # LiveKit voice agent
    │   ├── retrieval/        # Supermemory / local / both
    │   └── vectorstore/      # Chroma (optional)
    ├── api/index.py          # Vercel Mangum handler
    ├── vercel.json
    ├── requirements.txt      # Slim (Vercel)
    ├── requirements-local.txt
    ├── tests/
    ├── eval/
    └── PRODUCTION.md         # Deferred Phase G work
```

---

## Setup

### Requirements

- **Node.js** 18+ (root + client)
- **Python** 3.12+ recommended
- **npm** at repo root
- API keys: at minimum **`GROQ_API_KEY`** and **`SUPERMEMORY_API_KEY`** for core functionality

### Installation

```bash
# Repo root
npm install

# Backend Python env (from backend/)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements-local.txt

# Client deps (if not hoisted)
npm install --prefix client
```

### Environment

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — see table below
```

Optional local overrides: `backend/.env.local` (see `backend/.env.local.example` for Google OAuth).

Client optional:

```bash
# client/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Environment variables

From `backend/.env.example` and `app/config.py`. **Never commit real values.**

| Variable | Purpose | Required |
|----------|---------|----------|
| `GROQ_API_KEY` | Groq LLM for chat, agent, Telegram | **Yes** (import-time check) |
| `SUPERMEMORY_API_KEY` | Memory ingest, search, connectors | **Yes** for memory features |
| `SUPERMEMORY_BASE_URL` | Supermemory API base | No (default `https://api.supermemory.ai`) |
| `NERVA_USER_ID` | Single-tenant user id | No (default `default`) |
| `SUPERMEMORY_CONTAINER_TAG` | REST ingest/search scope | No (auto `user_{NERVA_USER_ID}`) |
| `LOCAL_RAG_ENABLED` | Enable Chroma + local embeddings | No (default `false`) |
| `RAG_PROVIDER` | `supermemory` \| `local` \| `both` | No |
| `FIRECRAWL_API_KEY` | Web agent + ingest | For web agent |
| `FIRECRAWL_MCP_URL` | Firecrawl MCP endpoint | No (has default) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot | For Telegram |
| `TELEGRAM_CHAT_ID` | Allowed Telegram chat | For Telegram |
| `TELEGRAM_WEBHOOK_SECRET` | Webhook header validation | Recommended |
| `TELEGRAM_WEBHOOK_URL` | Explicit webhook URL | No (auto on Vercel) |
| `LIVEKIT_URL` | LiveKit server | For voice |
| `LIVEKIT_API_KEY` | LiveKit API key | For voice |
| `LIVEKIT_API_SECRET` | LiveKit secret | For voice |
| `GOOGLE_CLIENT_ID` | Google OAuth | For voice Gmail/Calendar MCP |
| `GOOGLE_CLIENT_SECRET` | Google OAuth | For voice Gmail/Calendar MCP |
| `GOOGLE_REDIRECT_URI` | OAuth callback | For Google OAuth |
| `GOOGLE_MCP_BRIDGE_SECRET` | Voice worker bridge auth | For voice + Google MCP |
| `GITHUB_TOKEN` | GitHub remote MCP (voice) | For voice GitHub tools |
| `CHROMA_PATH` | Local Chroma data dir | If local RAG |
| `PDF_STORAGE_PATH` | Uploaded file storage | No |
| `CHATS_PATH` | Conversation JSON storage | No |
| `CORS_ORIGINS` | CORS allowlist | No (default `*`) |
| `CONNECTIONS_REDIRECT_URL` | Supermemory OAuth return URL | For connectors |
| `FRONTEND_URL` | Post-OAuth redirect base | For Google OAuth |

---

## Running locally

### Full stack (recommended)

From repo root:

```bash
npm run dev
```

- **Client:** http://localhost:3000  
- **API:** http://localhost:8000  
- **Swagger:** http://localhost:8000/docs  

> Root `dev:backend` uses `scripts/dev-backend.cmd` (Windows). On macOS/Linux, run uvicorn manually from `backend/`:
>
> ```bash
> python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app
> ```

### Voice agent (separate terminal)

Requires LiveKit env vars in `backend/.env`:

```bash
cd backend
python run_voice_agent.py dev
```

Use the **Call** view in the web UI to join a LiveKit room (token from `/voice/token`).

### Telegram webhook (local dev)

1. Run API on port **8000**.
2. Expose with ngrok: `ngrok http 8000`
3. Set webhook (replace token and URL):

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://<ngrok-host>/api/telegram/webhook", "secret_token": "<SECRET>"}'
```

4. Check: `GET /api/telegram/status` — should show `retrieval_backend: supermemory_mcp`.

**Production Telegram:** deploy `backend/` to Vercel (slim `requirements.txt`), set env vars, webhook → `https://<app>.vercel.app/api/telegram/webhook`.

---

## Testing

From `backend/` with `requirements-local.txt` installed:

```bash
python -m pytest tests/ -q
```

| Test file | Coverage |
|-----------|----------|
| `tests/test_agent.py` | Planner, orchestrator, gateway, safety |
| `tests/test_google_oauth.py` | OAuth, MCP bridge |
| `tests/test_github_mcp.py` | GitHub MCP voice tools |
| `tests/test_telegram_webhook.py` | Telegram auth, upload, MCP, session |

Eval (optional local RAG metrics):

```bash
python -m eval.run_eval
```

---

## Current status

| Area | Status |
|------|--------|
| Supermemory-first RAG | Default production path |
| Web dashboard | Functional for local dev |
| Agent + Firecrawl | Functional with keys |
| Telegram | Functional; file upload + MCP search |
| Voice | Requires separate worker + LiveKit setup |
| Vercel | Telegram + health only (not full API) |
| Production hardening | Deferred (`backend/PRODUCTION.md`) |

---

## Known limitations

- **Single-tenant:** no per-user API auth or data isolation.
- **Storage:** conversations and files on local disk — not suitable for serverless full API.
- **Telegram session:** in-memory pending files/history; use **reply-to** on Vercel for reliable uploads.
- **Supermemory namespace split:** MCP (Telegram/voice) vs REST container tag (web) may not see the same documents until tags are aligned.
- **Connectors:** Gmail/GitHub via Supermemory require Supermemory Scale/Enterprise.
- **Upload modal:** GitHub / YouTube / Website buttons are UI stubs (“Coming soon”); API ingest exists for web.
- **No CI/CD, Docker, or client deploy config** in repo.
- **Windows dev script:** `dev-backend.cmd` is Windows-oriented; Unix users run uvicorn directly.
- **Groq required at import:** missing `GROQ_API_KEY` crashes any path loading `app.llm`.
- **Local RAG on Windows:** cross-encoder + Qwen same process can crash (documented in `.env.example`).
- **Rate limiting / monitoring:** not implemented.

---

## Roadmap

Based on `PRODUCTION.md`, TODOs, and code gaps:

### Near term

1. Align Supermemory container tags across REST, MCP, and Telegram uploads.
2. Persistent Telegram session store (or document reply-to as primary UX on Vercel).
3. Wire upload modal “Website ingest” to existing `/api/agent/ingest` API.
4. Client deployment story + `NEXT_PUBLIC_API_URL` documentation.
5. CI: pytest + client lint/build.

### Future (Phase G — `backend/PRODUCTION.md`)

1. Authentication and per-user document isolation  
2. PostgreSQL for metadata  
3. Object storage for originals (S3/R2/GCS)  
4. Rate limiting and structured logging (e.g. Sentry)  
5. Background ingestion workers  

---

## Additional docs

- [`backend/README.md`](backend/README.md) — backend-focused setup (note: some pipeline docs still describe Chroma-first; defaults are Supermemory-first).
- [`backend/PRODUCTION.md`](backend/PRODUCTION.md) — explicitly deferred production work.

---

## License

No license file is present in this repository. All rights reserved by the repository owner unless stated otherwise.
