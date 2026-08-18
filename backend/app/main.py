from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.services.generation import generate_answer
from app.services.ingestion import ingest_pdf
from app.services.retrieval import (
    build_ask_context,
    retrieve_for_ask,
    retrieve_for_search,
)
from app.vectorstore.chroma import list_documents


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Nerva RAG API running"
    }


@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    print("\n========== PDF UPLOAD ==========")
    print(f"File: {file.filename}")

    contents = await file.read()
    print(f"PDF size: {len(contents) / 1024:.2f} KB")

    return ingest_pdf(contents, file.filename)


@app.get("/documents")
def documents():
    print("\n========== DOCUMENTS ==========")
    docs = list_documents()
    print(f"Found {len(docs)} documents.")
    return {"documents": docs}


@app.post("/search")
async def search_pdf(query: str, document_id: str | None = None):
    print("\n========== SEARCH ==========")
    print(f"Query: {query}")

    if document_id:
        print(f"Document ID: {document_id}")
    else:
        print("Searching across all documents.")

    results = retrieve_for_search(query, document_id)

    print(f"Final results: {len(results)}")
    print("========== SEARCH COMPLETE ==========\n")

    return {
        "query": query,
        "document_id": document_id,
        "results": results,
    }


@app.post("/ask")
async def ask(query: str, document_id: str | None = None):
    print("\n========== ASK ==========")
    print(f"Question: {query}")

    if document_id:
        print(f"Document ID: {document_id}")
    else:
        print("Searching across all documents.")

    ranked = retrieve_for_ask(query, document_id)

    if not ranked:
        return {
            "query": query,
            "document_id": document_id,
            "answer": (
                "I don't have enough information "
                "in the provided documents."
            ),
            "sources": [],
        }

    print(f"Reranked to {len(ranked)} chunks.")

    context, sources = build_ask_context(ranked)
    print("Context prepared.")

    print("Sending context to Groq...")
    answer = generate_answer(query, context)
    print("Answer generated.")
    print("========== ASK COMPLETE ==========\n")

    return {
        "query": query,
        "document_id": document_id,
        "answer": answer,
        "sources": sources,
    }
