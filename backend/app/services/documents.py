from app.services.ingestion import (
    delete_stored_pdf,
    ingest_pdf,
    load_pdf_bytes,
)
from app.vectorstore.chroma import (
    delete_document_chunks,
    document_exists,
    list_documents,
    rename_document_source,
)


def list_document_records():
    return list_documents()


def delete_document(document_id: str):
    removed = delete_document_chunks(document_id)
    delete_stored_pdf(document_id)
    return {
        "document_id": document_id,
        "deleted": removed > 0,
        "chunks_removed": removed,
    }


def rename_document(document_id: str, source: str):
    ok = rename_document_source(document_id, source.strip())
    if not ok:
        return None
    return {
        "document_id": document_id,
        "source": source.strip(),
    }


def reindex_document(document_id: str):
    if not document_exists(document_id):
        # Still allow reindex if PDF exists on disk from older state
        pdf_bytes = load_pdf_bytes(document_id)
        if pdf_bytes is None:
            return None
        filename = f"{document_id}.pdf"
    else:
        docs = list_documents()
        match = next(
            (d for d in docs if d["document_id"] == document_id),
            None,
        )
        filename = match["source"] if match else f"{document_id}.pdf"
        pdf_bytes = load_pdf_bytes(document_id)
        if pdf_bytes is None:
            return None

    result = ingest_pdf(
        pdf_bytes,
        filename,
        document_id=document_id,
    )
    if result.get("error"):
        return {
            "document_id": document_id,
            "filename": filename,
            "pages": 0,
            "chunks": 0,
            "embedding_dimension": 0,
            "error": result["error"],
        }

    return {
        "document_id": result["document_id"],
        "filename": result["filename"],
        "pages": result["pages"],
        "chunks": result["chunks"],
        "embedding_dimension": result["embedding_dimension"],
        "error": None,
    }
