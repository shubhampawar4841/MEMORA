from app.config import LOCAL_RAG_ENABLED
from app.folders import normalize_folder
from app.services.ingestion import (
    delete_stored_file,
    ingest_file,
    load_file_bytes,
)
from app.supermemory.sync import sync_delete, sync_metadata_update
from app.vectorstore.chroma import (
    delete_document_chunks,
    document_exists,
    list_documents,
    update_document_metadata,
)


def list_document_records():
    if not LOCAL_RAG_ENABLED:
        from app.supermemory.catalog import list_document_records as sm_list

        return sm_list()
    return list_documents()


def delete_document(document_id: str):
    if not LOCAL_RAG_ENABLED:
        sm = sync_delete(document_id)
        deleted = bool(sm.get("ok") or sm.get("deleted"))
        return {
            "document_id": document_id,
            "deleted": deleted,
            "chunks_removed": 0,
            "supermemory": sm,
        }

    removed = delete_document_chunks(document_id)
    delete_stored_file(document_id)
    sm = sync_delete(document_id)
    return {
        "document_id": document_id,
        "deleted": removed > 0,
        "chunks_removed": removed,
        "supermemory": sm,
    }


def rename_document(
    document_id: str,
    source: str | None = None,
    folder: str | None = None,
):
    clean_source = source.strip() if isinstance(source, str) else None
    if clean_source == "":
        clean_source = None

    clean_folder = None
    if folder is not None:
        clean_folder = normalize_folder(folder)

    if clean_source is None and clean_folder is None:
        return None

    if not LOCAL_RAG_ENABLED:
        sm = sync_metadata_update(
            document_id=document_id,
            source=clean_source or document_id,
            folder=clean_folder or "other",
        )
        if not sm.get("ok"):
            return None
        return {
            "document_id": document_id,
            "source": clean_source,
            "folder": clean_folder or "other",
        }

    result = update_document_metadata(
        document_id,
        source=clean_source,
        folder=clean_folder,
    )
    if result is None:
        return None

    sync_metadata_update(
        document_id=document_id,
        source=result.get("source"),
        folder=result.get("folder"),
    )
    return result


def reindex_document(document_id: str):
    if not LOCAL_RAG_ENABLED:
        return {
            "document_id": document_id,
            "filename": None,
            "pages": 0,
            "chunks": 0,
            "embedding_dimension": 0,
            "error": (
                "Re-index is unavailable while LOCAL_RAG_ENABLED=false "
                "(documents are stored only in Supermemory)."
            ),
            "folder": None,
        }

    folder = None
    stored = load_file_bytes(document_id)
    if stored is None:
        return None

    file_bytes, stored_name = stored

    if not document_exists(document_id):
        filename = stored_name
        source = stored_name
    else:
        docs = list_documents()
        match = next(
            (d for d in docs if d["document_id"] == document_id),
            None,
        )
        filename = stored_name
        source = match["source"] if match else stored_name
        folder = match.get("folder") if match else None

    result = ingest_file(
        file_bytes,
        filename,
        document_id=document_id,
        folder=folder,
        source=source,
    )
    if result.get("error"):
        return {
            "document_id": document_id,
            "filename": filename,
            "pages": 0,
            "chunks": 0,
            "embedding_dimension": 0,
            "error": result["error"],
            "folder": folder,
        }

    return {
        "document_id": result["document_id"],
        "filename": result.get("source") or result["filename"],
        "pages": result["pages"],
        "chunks": result["chunks"],
        "embedding_dimension": result["embedding_dimension"],
        "error": None,
        "folder": result.get("folder"),
        "supermemory": result.get("supermemory"),
    }
