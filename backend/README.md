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
python -m uvicorn app.main:app --reload
```

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

## Backend layout

```text
app/
  main.py                 # FastAPI app + routers
  config.py               # settings
  chunking.py             # PDF chunking (+ overlap)
  routers/                # documents, search, chat, health
  schemas/                # Pydantic models
  embeddings/qwen.py
  reranking/cross_encoder.py
  vectorstore/chroma.py
  services/
    ingestion.py
    retrieval.py          # hybrid vector + keyword
    generation.py         # Groq (+ streaming)
    documents.py
    conversations.py
eval/
  dataset.json
  run_eval.py
```

## Evaluation

From `backend/`:

```bash
python -m eval.run_eval
```
