from pathlib import Path
import uuid

from app.config import LOCAL_RAG_ENABLED, PDF_STORAGE_PATH
from app.folders import (
    DEFAULT_FOLDER,
    display_name_from_filename,
    normalize_folder,
)
from app.services.file_types import (
    file_extension,
    is_allowed_filename,
    source_type_for_filename,
)


def _storage_dir() -> Path:
    path = Path(PDF_STORAGE_PATH)
    path.mkdir(parents=True, exist_ok=True)
    return path


def stored_file_path(document_id: str, filename: str | None = None) -> Path:
    ext = file_extension(filename) or ".bin"
    return _storage_dir() / f"{document_id}{ext}"


def pdf_path_for(document_id: str) -> Path:
    """Backward-compatible alias (legacy PDF-only storage)."""
    return _storage_dir() / f"{document_id}.pdf"


def find_stored_file(document_id: str) -> Path | None:
    matches = sorted(_storage_dir().glob(f"{document_id}.*"))
    matches = [p for p in matches if p.suffix.lower() != ".json"]
    if matches:
        return matches[0]
    legacy = pdf_path_for(document_id)
    return legacy if legacy.exists() else None


def save_file_bytes(
    document_id: str,
    file_bytes: bytes,
    filename: str | None,
) -> Path:
    path = stored_file_path(document_id, filename)
    for old in _storage_dir().glob(f"{document_id}.*"):
        if old != path and old.suffix.lower() != ".json":
            old.unlink(missing_ok=True)
    path.write_bytes(file_bytes)
    return path


def save_pdf_bytes(document_id: str, pdf_bytes: bytes) -> Path:
    return save_file_bytes(document_id, pdf_bytes, f"{document_id}.pdf")


def load_file_bytes(document_id: str) -> tuple[bytes, str] | None:
    path = find_stored_file(document_id)
    if path is None:
        return None
    return path.read_bytes(), path.name


def load_pdf_bytes(document_id: str) -> bytes | None:
    found = load_file_bytes(document_id)
    return None if found is None else found[0]


def delete_stored_file(document_id: str) -> None:
    for path in _storage_dir().glob(f"{document_id}.*"):
        path.unlink(missing_ok=True)


def delete_stored_pdf(document_id: str) -> None:
    delete_stored_file(document_id)


def chunk_pages(pages, source: str, folder: str = DEFAULT_FOLDER):
    from app.chunking import chunk_text

    chunks = []
    metadata = []
    folder = normalize_folder(folder)

    for page in pages:
        print(f"\nProcessing page {page['page']}...")
        page_chunks = chunk_text(page["text"])
        print(f"Page {page['page']} -> {len(page_chunks)} chunks")

        for chunk in page_chunks:
            chunks.append(chunk)
            metadata.append({
                "source": source,
                "page": page["page"],
                "folder": folder,
            })

    return chunks, metadata


def _ingest_supermemory_only(
    file_bytes: bytes,
    filename: str | None,
    *,
    folder: str | None,
    source: str | None,
    document_id: str | None = None,
):
    """Upload → Supermemory only (no Chroma, no local file persist)."""
    from app.supermemory.client import is_configured as sm_configured
    from app.supermemory.sync import sync_file_upload

    if not sm_configured():
        return {
            "error": (
                "LOCAL_RAG_ENABLED=false requires SUPERMEMORY_API_KEY. "
                "Set the key, or enable local RAG."
            )
        }

    display_source = (source or "").strip() or display_name_from_filename(
        filename
    )
    doc_folder = normalize_folder(folder)
    source_type = source_type_for_filename(filename)
    doc_id = document_id or str(uuid.uuid4())

    print(f"Document ID: {doc_id}")
    print("Uploading raw file to Supermemory (primary store)...")

    sm_sync = sync_file_upload(
        document_id=doc_id,
        file_bytes=file_bytes,
        filename=filename,
        source=display_source,
        folder=doc_folder,
        source_type=source_type,
    )

    if not sm_sync.get("ok"):
        return {
            "error": (
                sm_sync.get("error")
                or "Supermemory upload failed."
            ),
            "document_id": doc_id,
            "supermemory": sm_sync,
        }

    print("\n========== COMPLETE (Supermemory-only) ==========\n")

    return {
        "filename": filename,
        "document_id": doc_id,
        "pages": 1,
        "chunks": 0,
        "embedding_dimension": 0,
        "folder": doc_folder,
        "source": display_source,
        "content_type": source_type,
        "supermemory": sm_sync,
        "storage": "supermemory",
    }


def _ingest_with_local(
    file_bytes: bytes,
    filename: str | None,
    document_id: str | None = None,
    *,
    folder: str | None = None,
    source: str | None = None,
):
    """Legacy dual-write path: local Chroma + optional Supermemory sync."""
    from app.embeddings.qwen import embed_texts
    from app.services.extractors import extract_pages
    from app.vectorstore.chroma import add_documents, delete_document_chunks

    display_source = (source or "").strip() or display_name_from_filename(
        filename
    )
    doc_folder = normalize_folder(folder)
    source_type = source_type_for_filename(filename)

    print("Local text extract (best-effort for Chroma)...")
    try:
        pages = extract_pages(file_bytes, filename)
    except Exception as exc:  # noqa: BLE001
        print(f"Local extract failed ({exc}); continuing with stub/SM.")
        pages = []

    print(f"Local pages with text: {len(pages)}")

    from app.supermemory.client import is_configured as sm_configured

    if not pages:
        if sm_configured():
            pages = [{
                "text": (
                    f"[Document: {display_source}]\n"
                    f"File: {filename or 'upload'}\n"
                    "Indexed for catalog locally. "
                    "Full content is parsed and searchable via Supermemory."
                ),
                "page": 1,
            }]
        else:
            return {
                "error": (
                    "No local text could be extracted from this file, and "
                    "SUPERMEMORY_API_KEY is not set."
                )
            }

    chunks, metadata = chunk_pages(
        pages,
        source=display_source,
        folder=doc_folder,
    )
    for row in metadata:
        row["content_type"] = source_type

    print(f"\nTotal local chunks: {len(chunks)}")
    if not chunks:
        return {"error": "No chunks were created."}

    print("\nStarting Qwen embeddings...")
    embeddings = embed_texts(chunks)
    print("Qwen embeddings completed.")
    embedding_dimension = len(embeddings[0])

    if document_id:
        delete_document_chunks(document_id)

    print("\nSaving embeddings to ChromaDB...")
    stored = add_documents(
        chunks,
        embeddings,
        metadata,
        document_id=document_id,
    )
    save_file_bytes(stored["document_id"], file_bytes, filename)

    from app.supermemory.sync import sync_file_upload

    print("Uploading raw file to Supermemory...")
    sm_sync = sync_file_upload(
        document_id=stored["document_id"],
        file_bytes=file_bytes,
        filename=filename,
        source=display_source,
        folder=doc_folder,
        source_type=source_type,
    )

    print("\n========== COMPLETE ==========\n")

    return {
        "filename": filename,
        "document_id": stored["document_id"],
        "pages": len(pages),
        "chunks": stored["chunks"],
        "embedding_dimension": embedding_dimension,
        "folder": doc_folder,
        "source": display_source,
        "content_type": source_type,
        "supermemory": sm_sync,
        "storage": "local+supermemory",
    }


def ingest_file(
    file_bytes: bytes,
    filename: str | None,
    document_id: str | None = None,
    *,
    folder: str | None = None,
    source: str | None = None,
):
    """
    Knowledge upload.

    When LOCAL_RAG_ENABLED=false (default):
      file → Supermemory only (no Chroma, no disk, no Qwen)

    When LOCAL_RAG_ENABLED=true:
      file → Chroma + disk + optional Supermemory sync
    """
    print("\n========== DOCUMENT INGEST ==========")
    print(f"File: {filename}")
    print(f"LOCAL_RAG_ENABLED={LOCAL_RAG_ENABLED}")

    if not is_allowed_filename(filename):
        return {
            "error": (
                f"Unsupported file type: {file_extension(filename) or 'unknown'}. "
                "Supported: PDF, TXT, MD, CSV, JSON, HTML, DOCX, DOC, "
                "PNG, JPG, WEBP, GIF, RTF, LOG."
            )
        }

    if not LOCAL_RAG_ENABLED:
        return _ingest_supermemory_only(
            file_bytes,
            filename,
            folder=folder,
            source=source,
            document_id=document_id,
        )

    return _ingest_with_local(
        file_bytes,
        filename,
        document_id=document_id,
        folder=folder,
        source=source,
    )


def ingest_pdf(
    pdf_bytes: bytes,
    filename: str | None,
    document_id: str | None = None,
    *,
    folder: str | None = None,
    source: str | None = None,
):
    """Backward-compatible PDF entry point."""
    name = filename or "document.pdf"
    if not str(name).lower().endswith(".pdf"):
        name = f"{name}.pdf"
    return ingest_file(
        pdf_bytes,
        name,
        document_id=document_id,
        folder=folder,
        source=source,
    )
