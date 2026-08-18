from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

import pymupdf

from app.chunking import chunk_text
from app.embeddings import embed_texts, embed_query
from app.chroma import add_documents, search


app = FastAPI()


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
# PDF UPLOAD + CHUNKING + EMBEDDING
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
    # Recursive chunking
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
        f"Stored {stored} chunks."
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

        "pages":
            len(pages),

        "chunks":
            stored,

        "embedding_dimension":
            embedding_dimension

    }


# ============================================================
# SEARCH
# ============================================================

@app.post("/search")
async def search_pdf(
    query: str
):

    print(
        "\n========== SEARCH =========="
    )


    print(
        f"Query: {query}"
    )


    # --------------------------------------------------------
    # Embed query
    # --------------------------------------------------------

    query_embedding = embed_query(
        query
    )


    print(
        "Query embedding generated."
    )


    # --------------------------------------------------------
    # Search ChromaDB
    # --------------------------------------------------------

    results = search(

        query_embedding,

        top_k=5

    )


    # --------------------------------------------------------
    # Format results
    # --------------------------------------------------------

    output = []


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


    for i, document in enumerate(
        documents
    ):

        output.append({

            "text":
                document,

            "distance":
                distances[i],

            "metadata":
                metadatas[i]

        })


    print(
        f"Retrieved {len(output)} results."
    )


    print(
        "========== SEARCH COMPLETE ==========\n"
    )


    return {

        "query":
            query,

        "results":
            output

    }