import chromadb
import uuid


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

    document_id = str(
        uuid.uuid4()
    )


    ids = [
        f"{document_id}_chunk_{i}"
        for i in range(len(chunks))
    ]


    # Add document ID to metadata
    enriched_metadata = []

    for i, item in enumerate(metadata):

        enriched_metadata.append({

            **item,

            "document_id":
                document_id,

            "chunk_index":
                i

        })


    collection.add(

        ids=ids,

        documents=chunks,

        embeddings=embeddings.tolist(),

        metadatas=enriched_metadata

    )


    return len(ids)


def search(
    query_embedding,
    top_k=5
):

    return collection.query(

        query_embeddings=[
            query_embedding.tolist()
        ],

        n_results=top_k

    )