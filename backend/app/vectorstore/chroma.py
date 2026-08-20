import uuid

import chromadb

from app.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PATH,
    KEYWORD_TOP_K,
    VECTOR_TOP_K,
)
from app.folders import DEFAULT_FOLDER, normalize_folder

client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = client.get_or_create_collection(
    name=CHROMA_COLLECTION_NAME,
    configuration={
        "hnsw": {
            "space": "cosine"
        }
    },
)


def _build_where(
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    folder: str | None = None,
):
    clauses = []

    if document_id:
        clauses.append({"document_id": document_id})
    elif document_ids:
        ids = [str(i) for i in document_ids if i]
        if len(ids) == 1:
            clauses.append({"document_id": ids[0]})
        elif ids:
            clauses.append({"document_id": {"$in": ids}})

    if folder:
        clauses.append({"folder": normalize_folder(folder)})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def ensure_default_folders() -> int:
    """Backfill missing folder metadata to 'other' (legacy chunks)."""
    data = collection.get(include=["metadatas"])
    ids = data.get("ids") or []
    metadatas = data.get("metadatas") or []
    if not ids:
        return 0

    update_ids = []
    update_metas = []
    for chunk_id, meta in zip(ids, metadatas):
        meta = dict(meta or {})
        if meta.get("folder"):
            continue
        meta["folder"] = DEFAULT_FOLDER
        update_ids.append(chunk_id)
        update_metas.append(meta)

    if update_ids:
        collection.update(ids=update_ids, metadatas=update_metas)
    return len(update_ids)


def add_documents(chunks, embeddings, metadata, document_id: str | None = None):
    document_id = document_id or str(uuid.uuid4())

    ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]

    enriched_metadata = []
    for i, item in enumerate(metadata):
        row = {
            **item,
            "document_id": document_id,
            "chunk_index": i,
        }
        row["folder"] = normalize_folder(row.get("folder"))
        enriched_metadata.append(row)

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


def search(
    query_embedding,
    top_k=VECTOR_TOP_K,
    document_id=None,
    document_ids: list[str] | None = None,
    folder: str | None = None,
):
    where = _build_where(
        document_id=document_id,
        document_ids=document_ids,
        folder=folder,
    )

    return collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=top_k,
        where=where,
    )


def keyword_search(
    query: str,
    top_k=KEYWORD_TOP_K,
    document_id=None,
    document_ids: list[str] | None = None,
    folder: str | None = None,
):
    """Simple keyword retrieval over stored chunk text."""
    where = _build_where(
        document_id=document_id,
        document_ids=document_ids,
        folder=folder,
    )

    if where:
        data = collection.get(
            where=where,
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

    stopwords = {
        "a", "an", "the", "and", "or", "of", "to", "in", "on", "for",
        "is", "are", "was", "were", "be", "been", "being",
        "i", "me", "my", "you", "your", "we", "our", "they", "their",
        "this", "that", "these", "those", "it", "its",
        "about", "tell", "what", "which", "who", "whom", "whose",
        "how", "when", "where", "why", "do", "does", "did", "please",
        "with", "from", "into", "over", "under", "can", "could",
        "would", "should", "will", "just", "also", "any", "some",
    }

    raw_terms = [
        t.lower().strip(".,!?;:\"'()[]{}")
        for t in query.split()
        if t.strip()
    ]
    terms = [
        t for t in raw_terms
        if t and t not in stopwords and len(t) > 1
    ]
    if not terms:
        terms = [t for t in raw_terms if t]

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
    ensure_default_folders()
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
                "folder": normalize_folder(metadata.get("folder")),
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


def update_document_metadata(
    document_id: str,
    *,
    source: str | None = None,
    folder: str | None = None,
) -> dict | None:
    """Update source and/or folder on all chunks for a document."""
    if source is None and folder is None:
        return None

    data = collection.get(
        where={"document_id": document_id},
        include=["metadatas"],
    )
    ids = data.get("ids") or []
    if not ids:
        return None

    metadatas = [dict(m or {}) for m in data["metadatas"]]
    for metadata in metadatas:
        if source is not None:
            metadata["source"] = source
        if folder is not None:
            metadata["folder"] = normalize_folder(folder)

    collection.update(ids=ids, metadatas=metadatas)

    sample = metadatas[0]
    return {
        "document_id": document_id,
        "source": sample.get("source"),
        "folder": normalize_folder(sample.get("folder")),
    }


def rename_document_source(document_id: str, source: str) -> bool:
    result = update_document_metadata(document_id, source=source)
    return result is not None


def document_exists(document_id: str) -> bool:
    data = collection.get(
        where={"document_id": document_id},
        include=[],
    )
    return bool(data.get("ids"))
