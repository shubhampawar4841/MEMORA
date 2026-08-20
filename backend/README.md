# Nerva API

PDF RAG backend for Nerva.

## Pipeline

```text
PDF
  → PyMuPDF text extraction
  → Chunking
  → Qwen embeddings (Qwen/Qwen3-Embedding-0.6B)
  → ChromaDB
  → Vector retrieval
  → BGE cross-encoder reranking (BAAI/bge-reranker-v2-m3)
  → Groq LLM (openai/gpt-oss-20b)
  → Answer + sources
```

## Setup

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set `GROQ_API_KEY`.

## Run FastAPI

From the `backend/` directory:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Prefer **no `--reload`** while using the web agent — reload + model loading can exhaust Windows threads and break chat streams. For code changes, restart manually. If you need reload: `--reload --reload-dir app` only.

ChromaDB data is stored locally under `data/chroma/` (no separate vector DB server required).

## URLs

- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs

## Endpoints

- `GET /` — health check
- `GET /documents` — list indexed PDFs
- `POST /upload-pdf` — upload and index a PDF
- `POST /search` — retrieve + rerank chunks
- `POST /ask` — full RAG answer with sources
- `POST /ask/stream` — streaming RAG answer (SSE)
- `POST /api/agent/chat` — planner-routed RAG / Firecrawl agent chat
- `POST /api/agent/chat/stream` — agent chat with high-level status events
- `POST /api/agent/ingest` — opt-in website → knowledge base ingest

Set `FIRECRAWL_API_KEY` in `.env` for web agent tools (hosted Firecrawl API only).

## Backend layout

```text
app/
  main.py                 # FastAPI app + routers
  config.py               # settings
  chunking.py             # PDF chunking (+ overlap)
  routers/                # documents, search, chat, agent, health
  schemas/                # Pydantic models
  embeddings/qwen.py
  reranking/cross_encoder.py
  vectorstore/chroma.py
  firecrawl/client.py     # hosted Firecrawl SDK wrapper
  agent/                  # planner + tool-calling orchestrator
  services/
    ingestion.py
    web_ingest.py         # opt-in web → Chroma
    retrieval.py          # hybrid vector + keyword
    generation.py         # Groq (+ streaming)
    documents.py
    conversations.py
eval/
  dataset.json
  run_eval.py
tests/
  test_agent.py
  fixtures/agent_test_page.html
```

## Evaluation

From `backend/`:

```bash
python -m eval.run_eval
```
