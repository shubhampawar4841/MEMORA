from pathlib import Path

import pymupdf

from app.chunking import chunk_text
from app.config import PDF_STORAGE_PATH
from app.embeddings.qwen import embed_texts
from app.vectorstore.chroma import add_documents, delete_document_chunks


def _pdf_dir() -> Path:
    path = Path(PDF_STORAGE_PATH)
    path.mkdir(parents=True, exist_ok=True)
    return path


def pdf_path_for(document_id: str) -> Path:
    return _pdf_dir() / f"{document_id}.pdf"


def save_pdf_bytes(document_id: str, pdf_bytes: bytes) -> Path:
    path = pdf_path_for(document_id)
    path.write_bytes(pdf_bytes)
    return path


def load_pdf_bytes(document_id: str) -> bytes | None:
    path = pdf_path_for(document_id)
    if not path.exists():
        return None
    return path.read_bytes()


def delete_stored_pdf(document_id: str) -> None:
    path = pdf_path_for(document_id)
    if path.exists():
        path.unlink()


def extract_pages(pdf_bytes: bytes):
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    pages = []

    for page_number, page in enumerate(doc, start=1):
        text = page.get_text("text", sort=True).strip()
        if text:
            pages.append({
                "text": text,
                "page": page_number,
            })

    return pages


def chunk_pages(pages, source: str):
    chunks = []
    metadata = []

    for page in pages:
        print(f"\nProcessing page {page['page']}...")
        page_chunks = chunk_text(page["text"])
        print(f"Page {page['page']} → {len(page_chunks)} chunks")

        for chunk in page_chunks:
            chunks.append(chunk)
            metadata.append({
                "source": source,
                "page": page["page"],
            })

    return chunks, metadata


def ingest_pdf(
    pdf_bytes: bytes,
    filename: str | None,
    document_id: str | None = None,
):
    """
    Full upload pipeline:

    PDF bytes → extract → chunk → embed → Chroma (+ persist PDF)
    """
    print("Opening PDF...")
    pages = extract_pages(pdf_bytes)
    print(f"Pages with text: {len(pages)}")

    if not pages:
        return {
            "error": "No text could be extracted from this PDF."
        }

    chunks, metadata = chunk_pages(pages, source=filename)
    print(f"\nTotal chunks: {len(chunks)}")

    if not chunks:
        return {
            "error": "No chunks were created."
        }

    print("\nStarting Qwen embeddings...")
    embeddings = embed_texts(chunks)
    print("Qwen embeddings completed.")

    embedding_dimension = len(embeddings[0])
    print(f"Embedding dimensions: {embedding_dimension}")

    if document_id:
        delete_document_chunks(document_id)

    print("\nSaving embeddings to ChromaDB...")
    stored = add_documents(
        chunks,
        embeddings,
        metadata,
        document_id=document_id,
    )
    save_pdf_bytes(stored["document_id"], pdf_bytes)

    print(f"Stored {stored['chunks']} chunks.")
    print(f"Document ID: {stored['document_id']}")
    print("\n========== COMPLETE ==========\n")

    return {
        "filename": filename,
        "document_id": stored["document_id"],
        "pages": len(pages),
        "chunks": stored["chunks"],
        "embedding_dimension": embedding_dimension,
    }
