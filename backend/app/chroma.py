import uuid
import chromadb

from app.config import CHROMA_COLLECTION_NAME, CHROMA_PATH


# ============================================================
# CHROMADB CLIENT
# ============================================================

client = chromadb.PersistentClient(
    path=CHROMA_PATH
)


# ============================================================
# COLLECTION
# ============================================================

collection = client.get_or_create_collection(
    name=CHROMA_COLLECTION_NAME,
    configuration={
        "hnsw": {
            "space": "cosine"
        }
    }
)


# ============================================================
# ADD DOCUMENTS
# ============================================================

def add_documents(
    chunks,
    embeddings,
    metadata
):

    document_id = str(uuid.uuid4())


    # --------------------------------------------------------
    # Create unique IDs
    # --------------------------------------------------------

    ids = [
        f"{document_id}_chunk_{i}"
        for i in range(len(chunks))
    ]


    # --------------------------------------------------------
    # Add document metadata
    # --------------------------------------------------------

    enriched_metadata = []


    for i, item in enumerate(metadata):

        enriched_metadata.append({

            **item,

            "document_id":
                document_id,

            "chunk_index":
                i

        })


    # --------------------------------------------------------
    # Store in ChromaDB
    # --------------------------------------------------------

    collection.add(

        ids=ids,

        documents=chunks,

        embeddings=embeddings.tolist(),

        metadatas=enriched_metadata

    )


    return {

        "document_id":
            document_id,

        "chunks":
            len(ids)

    }


# ============================================================
# SEARCH
# ============================================================

def search(
    query_embedding,
    top_k=10,
    document_id=None
):

    # --------------------------------------------------------
    # Optional document filter
    # --------------------------------------------------------

    where = None


    if document_id:

        where = {

            "document_id":
                document_id

        }


    # --------------------------------------------------------
    # Vector search
    # --------------------------------------------------------

    results = collection.query(

        query_embeddings=[
            query_embedding.tolist()
        ],

        n_results=top_k,

        where=where

    )


    return results


# ============================================================
# LIST DOCUMENTS
# ============================================================

def list_documents():

    data = collection.get(
        include=["metadatas"]
    )


    documents = {}


    # --------------------------------------------------------
    # Group chunks by document
    # --------------------------------------------------------

    for metadata in data["metadatas"]:

        document_id = metadata.get(
            "document_id"
        )


        if not document_id:

            continue


        if document_id not in documents:

            documents[document_id] = {

                "document_id":
                    document_id,

                "source":
                    metadata.get("source"),

                "pages":
                    set(),

                "chunks":
                    0

            }


        documents[document_id]["chunks"] += 1


        page = metadata.get(
            "page"
        )


        if page is not None:

            documents[document_id]["pages"].add(
                page
            )


    # --------------------------------------------------------
    # Convert sets → lists
    # --------------------------------------------------------

    output = []


    for document in documents.values():

        document["pages"] = sorted(
            document["pages"]
        )


        output.append(
            document
        )


    return output