from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

import pymupdf

from app.chunking import chunk_text
from app.embeddings import embed_texts, embed_query
from app.reranker import rerank
from app.generation import generate_answer
from app.config import (
    ASK_RERANK_TOP_K,
    CORS_ORIGINS,
    RERANK_SCORE_MARGIN,
    SEARCH_RERANK_TOP_K,
    VECTOR_TOP_K,
)

from app.chroma import (
    add_documents,
    search,
    list_documents
)


app = FastAPI()


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def home():

    return {
        "message": "Nerva RAG API running"
    }


# ============================================================
# UPLOAD PDF
#
# PDF
#   ↓
# Text extraction
#   ↓
# Chunking
#   ↓
# Embeddings
#   ↓
# ChromaDB
# ============================================================

@app.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...)
):

    print("\n========== PDF UPLOAD ==========")

    print(
        f"File: {file.filename}"
    )


    # --------------------------------------------------------
    # Read PDF
    # --------------------------------------------------------

    contents = await file.read()

    print(
        f"PDF size: {len(contents) / 1024:.2f} KB"
    )


    # --------------------------------------------------------
    # Open PDF
    # --------------------------------------------------------

    print("Opening PDF...")

    doc = pymupdf.open(
        stream=contents,
        filetype="pdf"
    )


    # --------------------------------------------------------
    # Extract pages
    # --------------------------------------------------------

    pages = []

    for page_number, page in enumerate(
        doc,
        start=1
    ):

        text = page.get_text(
            "text",
            sort=True
        ).strip()

        if text:

            pages.append({
                "text": text,
                "page": page_number
            })


    print(
        f"Pages with text: {len(pages)}"
    )


    if not pages:

        return {
            "error":
                "No text could be extracted from this PDF."
        }


    # --------------------------------------------------------
    # Chunking
    # --------------------------------------------------------

    chunks = []
    metadata = []


    for page in pages:

        print(
            f"\nProcessing page {page['page']}..."
        )


        page_chunks = chunk_text(
            page["text"]
        )


        print(
            f"Page {page['page']} → "
            f"{len(page_chunks)} chunks"
        )


        for chunk in page_chunks:

            chunks.append(
                chunk
            )


            metadata.append({

                "source":
                    file.filename,

                "page":
                    page["page"]

            })


    print(
        f"\nTotal chunks: {len(chunks)}"
    )


    if not chunks:

        return {
            "error":
                "No chunks were created."
        }


    # --------------------------------------------------------
    # Generate embeddings
    # --------------------------------------------------------

    print(
        "\nStarting Qwen embeddings..."
    )


    embeddings = embed_texts(
        chunks
    )


    print(
        "Qwen embeddings completed."
    )


    embedding_dimension = len(
        embeddings[0]
    )


    print(
        f"Embedding dimensions: "
        f"{embedding_dimension}"
    )


    # --------------------------------------------------------
    # Store in ChromaDB
    # --------------------------------------------------------

    print(
        "\nSaving embeddings to ChromaDB..."
    )


    stored = add_documents(

        chunks,

        embeddings,

        metadata

    )


    print(
        f"Stored {stored['chunks']} chunks."
    )


    print(
        f"Document ID: "
        f"{stored['document_id']}"
    )


    print(
        "\n========== COMPLETE ==========\n"
    )


    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {

        "filename":
            file.filename,

        "document_id":
            stored["document_id"],

        "pages":
            len(pages),

        "chunks":
            stored["chunks"],

        "embedding_dimension":
            embedding_dimension

    }


# ============================================================
# LIST DOCUMENTS
# ============================================================

@app.get("/documents")
def documents():

    print(
        "\n========== DOCUMENTS =========="
    )


    documents = list_documents()


    print(
        f"Found {len(documents)} documents."
    )


    return {

        "documents":
            documents

    }


# ============================================================
# SEARCH
#
# Chroma
#   ↓
# Top 10
#   ↓
# Reranker
#   ↓
# Top 5
#
# This endpoint is useful for debugging retrieval.
# ============================================================

@app.post("/search")
async def search_pdf(

    query: str,

    document_id: str | None = None

):

    print(
        "\n========== SEARCH =========="
    )


    print(
        f"Query: {query}"
    )


    if document_id:

        print(
            f"Document ID: {document_id}"
        )

    else:

        print(
            "Searching across all documents."
        )


    # --------------------------------------------------------
    # Generate query embedding
    # --------------------------------------------------------

    query_embedding = embed_query(
        query
    )


    print(
        "Query embedding generated."
    )


    # --------------------------------------------------------
    # Initial vector retrieval
    # --------------------------------------------------------

    results = search(

        query_embedding,

        top_k=VECTOR_TOP_K,

        document_id=document_id

    )


    documents = results.get(
        "documents",
        [[]]
    )[0]


    distances = results.get(
        "distances",
        [[]]
    )[0]


    metadatas = results.get(
        "metadatas",
        [[]]
    )[0]


    print(
        f"Vector search returned "
        f"{len(documents)} candidates."
    )


    if not documents:

        return {

            "query":
                query,

            "document_id":
                document_id,

            "results":
                []

        }


    # --------------------------------------------------------
    # Rerank
    # --------------------------------------------------------

    ranked = rerank(

        query,

        documents,

        top_k=SEARCH_RERANK_TOP_K,

        score_margin=RERANK_SCORE_MARGIN

    )


    print(
        f"Reranked to "
        f"{len(ranked)} results."
    )


    # --------------------------------------------------------
    # Build lookup
    # --------------------------------------------------------

    document_lookup = {}


    for i, document in enumerate(
        documents
    ):

        document_lookup[document] = {

            "distance":
                distances[i],

            "metadata":
                metadatas[i]

        }


    # --------------------------------------------------------
    # Final results
    # --------------------------------------------------------

    output = []


    for document, rerank_score in ranked:

        original = document_lookup.get(
            document
        )


        if not original:
            continue


        output.append({

            "text":
                document,

            "distance":
                original["distance"],

            "rerank_score":
                float(rerank_score),

            "metadata":
                original["metadata"]

        })


    print(
        f"Final results: "
        f"{len(output)}"
    )


    print(
        "========== SEARCH COMPLETE ==========\n"
    )


    return {

        "query":
            query,

        "document_id":
            document_id,

        "results":
            output

    }


# ============================================================
# ASK
#
# Complete RAG pipeline:
#
# Query
#   ↓
# Query Embedding
#   ↓
# Chroma Top 10
#   ↓
# Reranker
#   ↓
# Top 3
#   ↓
# Context
#   ↓
# Groq
#   ↓
# Answer
# ============================================================

@app.post("/ask")
async def ask(

    query: str,

    document_id: str | None = None

):

    print(
        "\n========== ASK =========="
    )


    print(
        f"Question: {query}"
    )


    if document_id:

        print(
            f"Document ID: {document_id}"
        )

    else:

        print(
            "Searching across all documents."
        )


    # --------------------------------------------------------
    # Query embedding
    # --------------------------------------------------------

    query_embedding = embed_query(
        query
    )


    print(
        "Query embedding generated."
    )


    # --------------------------------------------------------
    # Vector retrieval
    # --------------------------------------------------------

    results = search(

        query_embedding,

        top_k=VECTOR_TOP_K,

        document_id=document_id

    )


    documents = results.get(
        "documents",
        [[]]
    )[0]


    distances = results.get(
        "distances",
        [[]]
    )[0]


    metadatas = results.get(
        "metadatas",
        [[]]
    )[0]


    print(
        f"Retrieved "
        f"{len(documents)} candidates."
    )


    if not documents:

        return {

            "query":
                query,

            "document_id":
                document_id,

            "answer":
                "I don't have enough information "
                "in the provided documents.",

            "sources":
                []

        }


    # --------------------------------------------------------
    # Reranking
    # --------------------------------------------------------

    ranked = rerank(

        query,

        documents,

        top_k=ASK_RERANK_TOP_K,

        score_margin=RERANK_SCORE_MARGIN

    )


    print(
        f"Reranked to "
        f"{len(ranked)} chunks."
    )


    # --------------------------------------------------------
    # Build lookup
    # --------------------------------------------------------

    document_lookup = {}


    for i, document in enumerate(
        documents
    ):

        document_lookup[document] = {

            "distance":
                distances[i],

            "metadata":
                metadatas[i]

        }


    # --------------------------------------------------------
    # Build context
    # --------------------------------------------------------

    context_parts = []

    sources = []


    for document, rerank_score in ranked:

        original = document_lookup.get(
            document
        )


        if not original:
            continue


        metadata = original["metadata"]


        context_parts.append(
            document
        )


        sources.append({

            "source":
                metadata.get("source"),

            "page":
                metadata.get("page"),

            "chunk_index":
                metadata.get("chunk_index"),

            "distance":
                float(
                    original["distance"]
                ),

            "rerank_score":
                float(
                    rerank_score
                )

        })


    context = "\n\n---\n\n".join(
        context_parts
    )


    print(
        "Context prepared."
    )


    # --------------------------------------------------------
    # Generate answer with Groq
    # --------------------------------------------------------

    print(
        "Sending context to Groq..."
    )


    answer = generate_answer(

        query,

        context

    )


    print(
        "Answer generated."
    )


    print(
        "========== ASK COMPLETE ==========\n"
    )


    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {

        "query":
            query,

        "document_id":
            document_id,

        "answer":
            answer,

        "sources":
            sources

    }