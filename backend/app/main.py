from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.routers import (
    agent,
    chat,
    connections,
    documents,
    health,
    memory,
    search,
    voice,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    print("")
    print("========== NERVA STARTUP ==========")

    from app.config import (
        LOCAL_RAG_ENABLED,
        RAG_FALLBACK_TO_LOCAL,
        RAG_PROVIDER,
    )
    from app.supermemory.client import is_configured as sm_configured

    print(f"LOCAL_RAG_ENABLED={LOCAL_RAG_ENABLED}")
    print(f"RAG_PROVIDER={RAG_PROVIDER}")
    print(
        "Supermemory: "
        + ("configured" if sm_configured() else "not configured")
    )
    from app.config import NERVA_USER_ID, SUPERMEMORY_CONTAINER_TAG

    print(f"NERVA_USER_ID={NERVA_USER_ID}")
    print(f"SUPERMEMORY_CONTAINER_TAG={SUPERMEMORY_CONTAINER_TAG}")
    print(f"RAG_FALLBACK_TO_LOCAL={RAG_FALLBACK_TO_LOCAL}")

    if LOCAL_RAG_ENABLED:
        # Load the embedding model once at startup.
        print("Loading embedding model (local RAG enabled)...")
        from app.embeddings.qwen import get_embedding_model

        get_embedding_model()
        print("Embedding model ready.")
        print(
            "BGE reranker will be loaded on first local retrieval."
        )
    else:
        print(
            "Local RAG disabled — skipping Qwen/Chroma load. "
            "Knowledge is Supermemory-only."
        )

    print("========== NERVA READY ==========")
    print("")

    yield


app = FastAPI(
    title="Nerva API",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health.router)
app.include_router(documents.router)
app.include_router(connections.router)
app.include_router(memory.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(agent.router)
app.include_router(voice.router)
