from sentence_transformers import SentenceTransformer

from app.config import EMBEDDING_MODEL_NAME

model = SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_texts(texts):
    return model.encode(
        texts,
        normalize_embeddings=True
    )


def embed_query(query):
    return model.encode(
        query,
        normalize_embeddings=True
    )
