import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Backend root: backend/
BACKEND_ROOT = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------
# Environment
# ------------------------------------------------------------

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CHROMA_PATH = os.getenv(
    "CHROMA_PATH",
    str(BACKEND_ROOT / "data" / "chroma"),
)

CHROMA_COLLECTION_NAME = "nerva"

# ------------------------------------------------------------
# Models (do not change without an explicit decision)
# ------------------------------------------------------------

EMBEDDING_MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
GROQ_MODEL_NAME = "openai/gpt-oss-20b"

# ------------------------------------------------------------
# Retrieval defaults (match current main.py behavior)
# ------------------------------------------------------------

VECTOR_TOP_K = 10
SEARCH_RERANK_TOP_K = 5
ASK_RERANK_TOP_K = 3
RERANK_SCORE_MARGIN = 0.25

# ------------------------------------------------------------
# CORS
# ------------------------------------------------------------

# Keep permissive local-dev behavior from the current app.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]
