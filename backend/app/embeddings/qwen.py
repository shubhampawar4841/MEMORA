from __future__ import annotations

from sentence_transformers import SentenceTransformer

from app.config import EMBEDDING_MODEL_NAME

_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"Loading embedding model ({EMBEDDING_MODEL_NAME})...")
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        print("Embedding model loaded.")
    return _model


def embed_texts(texts):
    return get_embedding_model().encode(
        texts,
        normalize_embeddings=True,
    )


def embed_query(query):
    return get_embedding_model().encode(
        query,
        normalize_embeddings=True,
    )
