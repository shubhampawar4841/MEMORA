"""Supported knowledge-base upload formats."""

from __future__ import annotations

from pathlib import Path

# Local text extraction + Supermemory file sync.
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".json",
    ".html",
    ".htm",
    ".log",
    ".rtf",
    ".docx",
    ".doc",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
}

MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".html": "text/html",
    ".htm": "text/html",
    ".log": "text/plain",
    ".rtf": "application/rtf",
    ".docx": (
        "application/vnd.openxmlformats-officedocument"
        ".wordprocessingml.document"
    ),
    ".doc": "application/msword",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

SOURCE_TYPE_BY_EXT = {
    ".pdf": "pdf",
    ".txt": "text",
    ".md": "markdown",
    ".markdown": "markdown",
    ".csv": "csv",
    ".json": "json",
    ".html": "html",
    ".htm": "html",
    ".log": "text",
    ".rtf": "rtf",
    ".docx": "docx",
    ".doc": "doc",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".gif": "image",
}


def file_extension(filename: str | None) -> str:
    if not filename:
        return ""
    return Path(filename).suffix.lower()


def is_allowed_filename(filename: str | None) -> bool:
    ext = file_extension(filename)
    return ext in ALLOWED_EXTENSIONS


def mime_for_filename(filename: str | None) -> str:
    ext = file_extension(filename)
    return MIME_BY_EXT.get(ext, "application/octet-stream")


def source_type_for_filename(filename: str | None) -> str:
    ext = file_extension(filename)
    return SOURCE_TYPE_BY_EXT.get(ext, "file")


def accept_attribute() -> str:
    """HTML file input accept= value."""
    parts = sorted(ALLOWED_EXTENSIONS)
    return ",".join(parts)
