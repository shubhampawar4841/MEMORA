# Nerva API

Minimal FastAPI backend for Nerva.

## Setup

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

## Run FastAPI

```bash
python -m uvicorn app.main:app --reload
```

## Run Qdrant locally

```bash
docker run -p 6333:6333 qdrant/qdrant
```

## URLs

- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
