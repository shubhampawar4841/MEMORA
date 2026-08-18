import uuid
import chromadb


client = chromadb.PersistentClient(
    path="./data/chroma"
)


collection = client.get_or_create_collection(
    name="nerva",
    configuration={
        "hnsw": {
            "space": "cosine"
        }
    }
)


def add_documents(
    chunks,
    embeddings,
    metadata
):

    document_id = str(uuid.uuid4())

    ids = [
        f"{document_id}_chunk_{i}"
        for i in range(len(chunks))
    ]

    enriched_metadata = []

    for i, item in enumerate(metadata):

        enriched_metadata.append({
            **item,
            "document_id": document_id,
            "chunk_index": i
        })

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings.tolist(),
        metadatas=enriched_metadata
    )

    return {
        "document_id": document_id,
        "chunks": len(ids)
    }


def search(
    query_embedding,
    top_k=5,
    document_id=None
):

    where = None

    if document_id:
        where = {
            "document_id": document_id
        }

    return collection.query(
        query_embeddings=[
            query_embedding.tolist()
        ],
        n_results=top_k,
        where=where
    )


def list_documents():

    data = collection.get(
        include=["metadatas"]
    )

    documents = {}

    for metadata in data["metadatas"]:

        document_id = metadata.get(
            "document_id"
        )

        if not document_id:
            continue

        if document_id not in documents:

            documents[document_id] = {
                "document_id": document_id,
                "source": metadata.get("source"),
                "pages": set(),
                "chunks": 0
            }

        documents[document_id]["chunks"] += 1

        page = metadata.get("page")

        if page is not None:
            documents[document_id]["pages"].add(page)


    output = []

    for document in documents.values():

        document["pages"] = sorted(
            document["pages"]
        )

        output.append(document)

    return output