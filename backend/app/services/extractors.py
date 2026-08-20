"""
Lightweight local text helpers for Chroma only.

Supermemory receives the raw uploaded file and does its own
parse/OCR/index — we do NOT build a custom document parser for SM.
"""

from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser

import pymupdf

from app.services.file_types import file_extension


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self._skip = True

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"}:
            self._skip = False
        if tag in {"p", "div", "br", "li", "h1", "h2", "h3", "tr"}:
            self._parts.append("\n")

    def handle_data(self, data):
        if not self._skip and data:
            self._parts.append(data)

    def text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "".join(self._parts)).strip()


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _pages_from_text(text: str) -> list[dict]:
    text = (text or "").strip()
    if not text:
        return []
    return [{"text": text, "page": 1}]


def extract_pages(data: bytes, filename: str | None) -> list[dict]:
    """
    Best-effort local text for Chroma.

    Returns [] when we should rely on Supermemory's built-in ingestion
    instead of a custom parser (images, office docs, etc.).
    """
    ext = file_extension(filename)

    if ext == ".pdf":
        doc = pymupdf.open(stream=data, filetype="pdf")
        pages = []
        for page_number, page in enumerate(doc, start=1):
            text = page.get_text("text", sort=True).strip()
            if text:
                pages.append({"text": text, "page": page_number})
        return pages

    if ext in {".txt", ".md", ".markdown", ".log", ".rtf", ".csv"}:
        return _pages_from_text(_decode_text(data))

    if ext == ".json":
        raw = _decode_text(data)
        try:
            pretty = json.dumps(json.loads(raw), indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            pretty = raw
        return _pages_from_text(pretty)

    if ext in {".html", ".htm"}:
        raw = _decode_text(data)
        parser = _HTMLTextExtractor()
        parser.feed(raw)
        text = parser.text() or html.unescape(re.sub(r"<[^>]+>", " ", raw))
        return _pages_from_text(text)

    # DOCX / DOC / images / other: no local parser — Supermemory handles these.
    return []
