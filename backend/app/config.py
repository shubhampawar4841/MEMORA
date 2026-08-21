import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env then .env.local (LiveKit local credentials)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_ROOT / ".env")
load_dotenv(_BACKEND_ROOT / ".env.local", override=True)
load_dotenv()

BACKEND_ROOT = _BACKEND_ROOT

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

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

# ------------------------------------------------------------
# Agent / Firecrawl
# ------------------------------------------------------------

MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "15"))
FIRECRAWL_DEFAULT_CRAWL_LIMIT = int(
    os.getenv("FIRECRAWL_DEFAULT_CRAWL_LIMIT", "10")
)
FIRECRAWL_MAX_CRAWL_LIMIT = int(
    os.getenv("FIRECRAWL_MAX_CRAWL_LIMIT", "25")
)
AGENT_TOOL_CONTENT_LIMIT = int(
    os.getenv("AGENT_TOOL_CONTENT_LIMIT", "12000")
)
FIRECRAWL_MCP_URL = os.getenv(
    "FIRECRAWL_MCP_URL",
    "https://mcp.firecrawl.dev/v2/mcp",
)
FIRECRAWL_MCP_TIMEOUT = float(os.getenv("FIRECRAWL_MCP_TIMEOUT", "60"))
FIRECRAWL_MCP_SSE_READ_TIMEOUT = float(
    os.getenv("FIRECRAWL_MCP_SSE_READ_TIMEOUT", "300")
)
AGENT_CONTEXT_CHAR_LIMIT = int(
    os.getenv("AGENT_CONTEXT_CHAR_LIMIT", "12000")
)


# ------------------------------------------------------------
# Retrieval
# ------------------------------------------------------------

# Initial candidate pool.
# These are candidates BEFORE reranking.
VECTOR_TOP_K = 10
KEYWORD_TOP_K = 10

# Final results sent to the application.
SEARCH_RERANK_TOP_K = 5
ASK_RERANK_TOP_K = 5

# Keep candidates whose reranker score is reasonably close
# to the best candidate.
RERANK_SCORE_MARGIN = 0.25

# Skip generation when retrieval confidence is extremely low.
MIN_RERANK_SCORE = -1.0


# ------------------------------------------------------------
# Search strategy
# ------------------------------------------------------------

USE_HYBRID_SEARCH = os.getenv(
    "USE_HYBRID_SEARCH",
    "true",
).lower() in {
    "1",
    "true",
    "yes",
}

# BGE cross-encoder + Qwen in one Windows process often segfaults.
# Default off on win32; set USE_CROSS_ENCODER=true to force-enable.
USE_CROSS_ENCODER = os.getenv(
    "USE_CROSS_ENCODER",
    "false" if sys.platform == "win32" else "true",
).lower() in {
    "1",
    "true",
    "yes",
}


# ------------------------------------------------------------
# RAG provider (local | supermemory | both)
# ------------------------------------------------------------

# Local Chroma/Qwen/BGE path — kept in codebase but disabled by default
# for faster startup and Supermemory-first operation.
LOCAL_RAG_ENABLED = os.getenv(
    "LOCAL_RAG_ENABLED",
    "false",
).lower() in {
    "1",
    "true",
    "yes",
}

RAG_PROVIDER = os.getenv(
    "RAG_PROVIDER",
    "supermemory" if not LOCAL_RAG_ENABLED else "local",
).strip().lower()

if RAG_PROVIDER not in {"local", "supermemory", "both"}:
    RAG_PROVIDER = "supermemory" if not LOCAL_RAG_ENABLED else "local"

# When local RAG is disabled, never use local/both even if misconfigured.
if not LOCAL_RAG_ENABLED and RAG_PROVIDER in {"local", "both"}:
    RAG_PROVIDER = "supermemory"

SUPERMEMORY_API_KEY = os.getenv("SUPERMEMORY_API_KEY", "").strip() or None

SUPERMEMORY_BASE_URL = os.getenv(
    "SUPERMEMORY_BASE_URL",
    "https://api.supermemory.ai",
).rstrip("/")

# Default end-user id for single-tenant / local use.
# Connectors + uploads share container tag user_<NERVA_USER_ID>
# unless SUPERMEMORY_CONTAINER_TAG is set explicitly.
NERVA_USER_ID = os.getenv("NERVA_USER_ID", "default").strip() or "default"

_sm_tag_override = os.getenv("SUPERMEMORY_CONTAINER_TAG", "").strip()
if _sm_tag_override:
    SUPERMEMORY_CONTAINER_TAG = _sm_tag_override
else:
    _uid = "".join(
        ch if ch.isalnum() or ch in "_:-" else "_"
        for ch in NERVA_USER_ID
    ).strip("_") or "default"
    SUPERMEMORY_CONTAINER_TAG = f"user_{_uid}"

# Where Supermemory redirects after Gmail/GitHub OAuth.
# Use your frontend URL (e.g. http://localhost:3000/?integrations=connected).
CONNECTIONS_REDIRECT_URL = os.getenv(
    "CONNECTIONS_REDIRECT_URL",
    "http://localhost:3000/?integrations=connected",
).strip()

# Only meaningful when LOCAL_RAG_ENABLED=true.
RAG_FALLBACK_TO_LOCAL = os.getenv(
    "RAG_FALLBACK_TO_LOCAL",
    "false" if not LOCAL_RAG_ENABLED else "true",
).lower() in {
    "1",
    "true",
    "yes",
} and LOCAL_RAG_ENABLED



# ------------------------------------------------------------
# LiveKit voice
# ------------------------------------------------------------

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "").strip() or None
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "").strip() or None
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "").strip() or None
# Must match @server.rtc_session(agent_name=...) in app/voice/agent.py
LIVEKIT_AGENT_NAME = "Shubham_Assistent"


# ------------------------------------------------------------
# CORS
# ------------------------------------------------------------

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]