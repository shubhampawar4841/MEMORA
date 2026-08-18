import uuid

import chromadb

from app.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PATH,
    KEYWORD_TOP_K,
    VECTOR_TOP_K,
)

client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = client.get_or_create_collection(
    name=CHROMA_COLLECTION_NAME,
    configuration={
        "hnsw": {
            "space": "cosine"
        }
    },
)


def add_documents(chunks, embeddings, metadata, document_id: str | None = None):
    document_id = document_id or str(uuid.uuid4())

    ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]

    enriched_metadata = []
    for i, item in enumerate(metadata):
        enriched_metadata.append({
            **item,
            "document_id": document_id,
            "chunk_index": i,
        })

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings.tolist(),
        metadatas=enriched_metadata,
    )

    return {
        "document_id": document_id,
        "chunks": len(ids),
    }


def search(query_embedding, top_k=VECTOR_TOP_K, document_id=None):
    where = None
    if document_id:
        where = {"document_id": document_id}

    return collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=top_k,
        where=where,
    )


def keyword_search(query: str, top_k=KEYWORD_TOP_K, document_id=None):
    """Simple keyword retrieval over stored chunk text."""
    if document_id:
        data = collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"],
        )
    else:
        data = collection.get(include=["documents", "metadatas"])

    documents = data.get("documents") or []
    metadatas = data.get("metadatas") or []
    ids = data.get("ids") or []

    if not documents:
        return {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

    terms = [t.lower() for t in query.split() if t.strip()]
    scored = []

    for i, text in enumerate(documents):
        haystack = (text or "").lower()
        if not terms:
            score = 0.0
        else:
            score = sum(haystack.count(term) for term in terms) / len(terms)
        if score > 0:
            distance = 1.0 / (1.0 + score)
            scored.append((score, distance, text, metadatas[i], ids[i]))

    scored.sort(key=lambda item: item[0], reverse=True)
    top = scored[:top_k]

    return {
        "ids": [[item[4] for item in top]],
        "documents": [[item[2] for item in top]],
        "metadatas": [[item[3] for item in top]],
        "distances": [[item[1] for item in top]],
    }


def list_documents():
    data = collection.get(include=["metadatas"])
    documents = {}

    for metadata in data["metadatas"]:
        document_id = metadata.get("document_id")
        if not document_id:
            continue

        if document_id not in documents:
            documents[document_id] = {
                "document_id": document_id,
                "source": metadata.get("source"),
                "pages": set(),
                "chunks": 0,
            }

        documents[document_id]["chunks"] += 1
        page = metadata.get("page")
        if page is not None:
            documents[document_id]["pages"].add(page)

    output = []
    for document in documents.values():
        document["pages"] = sorted(document["pages"])
        output.append(document)

    return output


def delete_document_chunks(document_id: str) -> int:
    data = collection.get(
        where={"document_id": document_id},
        include=[],
    )
    ids = data.get("ids") or []
    if not ids:
        return 0
    collection.delete(ids=ids)
    return len(ids)


def rename_document_source(document_id: str, source: str) -> bool:
    data = collection.get(
        where={"document_id": document_id},
        include=["metadatas"],
    )
    ids = data.get("ids") or []
    if not ids:
        return False

    metadatas = data["metadatas"]
    for metadata in metadatas:
        metadata["source"] = source

    collection.update(ids=ids, metadatas=metadatas)
    return True


def document_exists(document_id: str) -> bool:
    data = collection.get(
        where={"document_id": document_id},
        include=[],
    )
    return bool(data.get("ids"))
