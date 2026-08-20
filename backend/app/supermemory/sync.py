"""Best-effort sync of Nerva documents into Supermemory."""

from __future__ import annotations

import logging
from typing import Any

from app.folders import normalize_folder
from app.services.file_types import mime_for_filename, source_type_for_filename
from app.supermemory import client as sm

logger = logging.getLogger("nerva.supermemory.sync")


def _metadata(
    *,
    document_id: str,
    title: str | None,
    folder: str | None,
    source_type: str = "pdf",
) -> dict[str, Any]:
    return {
        "document_id": document_id,
        "title": title or document_id,
        "folder": normalize_folder(folder),
        "source_type": source_type,
    }


def sync_file_upload(
    *,
    document_id: str,
    file_bytes: bytes,
    filename: str | None,
    source: str | None,
    folder: str | None,
    source_type: str | None = None,
) -> dict[str, Any]:
    """
    Push the raw file to Supermemory after local catalog ingest.

    Supermemory performs its own parse/OCR/index — we do not
    pre-parse content for them.
    """
    if not sm.is_configured():
        msg = "Supermemory sync skipped (SUPERMEMORY_API_KEY not set)."
        logger.info(msg)
        print(msg)
        return {"ok": False, "skipped": True, "error": None}

    title = source or filename or document_id
    resolved_type = source_type or source_type_for_filename(filename)
    meta = _metadata(
        document_id=document_id,
        title=title,
        folder=folder,
        source_type=resolved_type,
    )

    try:
        result = sm.upload_file(
            file_bytes=file_bytes,
            filename=filename or f"{document_id}.bin",
            custom_id=document_id,
            metadata=meta,
            task_type="superrag",
            content_type=mime_for_filename(filename),
        )
        print(
            f"Supermemory sync OK for document_id={document_id} "
            f"sm_id={result.get('id')} status={result.get('status')}"
        )
        return {"ok": True, "skipped": False, "result": result, "error": None}
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Supermemory sync FAILED for document_id=%s",
            document_id,
        )
        print(
            f"Supermemory sync FAILED for document_id={document_id}: {exc}"
        )
        return {
            "ok": False,
            "skipped": False,
            "result": None,
            "error": str(exc),
        }


def sync_pdf_upload(
    *,
    document_id: str,
    pdf_bytes: bytes,
    filename: str | None,
    source: str | None,
    folder: str | None,
) -> dict[str, Any]:
    """Backward-compatible alias."""
    return sync_file_upload(
        document_id=document_id,
        file_bytes=pdf_bytes,
        filename=filename or f"{document_id}.pdf",
        source=source,
        folder=folder,
        source_type="pdf",
    )


def sync_metadata_update(
    *,
    document_id: str,
    source: str | None = None,
    folder: str | None = None,
    source_type: str | None = None,
) -> dict[str, Any]:
    if not sm.is_configured():
        return {"ok": False, "skipped": True, "error": None}

    meta = _metadata(
        document_id=document_id,
        title=source or document_id,
        folder=folder,
        source_type=source_type or "file",
    )
    try:
        result = sm.update_document(document_id, metadata=meta)
        print(f"Supermemory metadata updated for {document_id}")
        return {"ok": True, "skipped": False, "result": result, "error": None}
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Supermemory metadata update FAILED for %s",
            document_id,
        )
        print(f"Supermemory metadata update FAILED for {document_id}: {exc}")
        return {
            "ok": False,
            "skipped": False,
            "result": None,
            "error": str(exc),
        }


def sync_delete(document_id: str) -> dict[str, Any]:
    if not sm.is_configured():
        return {"ok": False, "skipped": True, "error": None}

    try:
        deleted = sm.delete_document(document_id)
        print(f"Supermemory delete for {document_id}: deleted={deleted}")
        return {"ok": True, "skipped": False, "deleted": deleted, "error": None}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Supermemory delete FAILED for %s", document_id)
        print(f"Supermemory delete FAILED for {document_id}: {exc}")
        return {
            "ok": False,
            "skipped": False,
            "deleted": False,
            "error": str(exc),
        }
