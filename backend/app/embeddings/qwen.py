from __future__ import annotations

from sentence_transformers import SentenceTransformer

from app.config import EMBEDDING_MODEL_NAME


_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    global _model

    if _model is None:
        print(
            f"Loading embedding model "
            f"({EMBEDDING_MODEL_NAME})..."
        )

        _model = SentenceTransformer(
            EMBEDDING_MODEL_NAME,
            device="cpu",
        )

        print("Embedding model loaded.")

    return _model


def embed_texts(texts):
    model = get_embedding_model()

    return model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )


def embed_query(query):
    model = get_embedding_model()

    return model.encode(
        query,
        normalize_embeddings=True,
        show_progress_bar=False,
    )