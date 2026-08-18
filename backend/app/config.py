import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_ROOT = Path(__file__).resolve().parent.parent

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CHROMA_PATH = os.getenv(
    "CHROMA_PATH",
    str(BACKEND_ROOT / "data" / "chroma"),
)

CHROMA_COLLECTION_NAME = "nerva"

PDF_STORAGE_PATH = os.getenv(
    "PDF_STORAGE_PATH",
    str(BACKEND_ROOT / "data" / "pdfs"),
)

CHATS_PATH = os.getenv(
    "CHATS_PATH",
    str(BACKEND_ROOT / "data" / "chats"),
)

EMBEDDING_MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
GROQ_MODEL_NAME = "openai/gpt-oss-20b"

VECTOR_TOP_K = 10
KEYWORD_TOP_K = 10
SEARCH_RERANK_TOP_K = 5
ASK_RERANK_TOP_K = 3
RERANK_SCORE_MARGIN = 0.25
# Skip Groq when best rerank score is below this threshold.
MIN_RERANK_SCORE = 0.01

USE_HYBRID_SEARCH = os.getenv("USE_HYBRID_SEARCH", "true").lower() in {
    "1",
    "true",
    "yes",
}

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]
