"""Knowledge-base folder labels (fixed set for v1)."""

from __future__ import annotations

from pathlib import Path

ALLOWED_FOLDERS = (
    "personal",
    "work",
    "study",
    "other",
)

DEFAULT_FOLDER = "other"


def normalize_folder(value: str | None) -> str:
    """Return a valid folder; unknown/empty → other."""
    if not value:
        return DEFAULT_FOLDER
    folder = str(value).strip().lower()
    if folder in ALLOWED_FOLDERS:
        return folder
    return DEFAULT_FOLDER


def display_name_from_filename(filename: str | None) -> str:
    """Default display title from an upload filename."""
    if not filename or not str(filename).strip():
        return "Untitled"
    name = str(filename).strip()
    stem = Path(name).stem
    return stem.strip() or "Untitled"
