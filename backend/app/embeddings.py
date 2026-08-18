from sentence_transformers import SentenceTransformer


MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"


model = SentenceTransformer(MODEL_NAME)


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