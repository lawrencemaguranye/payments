"""Builds a searchable chunk index from the Postilion documentation set in docs/.

Supports .txt, .md, and .pdf. Drop documentation files into docs/ (any
subdirectory structure) and run `python -m postilion_agent.cli index`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from .config import DOCS_DIR, INDEX_DIR, INDEX_FILE

CHUNK_TARGET_CHARS = 1200
CHUNK_OVERLAP_CHARS = 150


@dataclass
class Chunk:
    id: int
    source: str
    page: int | None
    text: str


def _read_txt_or_md(path) -> list[tuple[str, int | None]]:
    return [(path.read_text(encoding="utf-8", errors="replace"), None)]


def _read_pdf(path) -> list[tuple[str, int]]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((text, i))
    return pages


READERS = {
    ".txt": _read_txt_or_md,
    ".md": _read_txt_or_md,
    ".pdf": _read_pdf,
}


def _chunk_text(text: str) -> list[str]:
    """Greedily merges paragraphs into ~CHUNK_TARGET_CHARS chunks with overlap."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if current and len(current) + len(para) + 2 > CHUNK_TARGET_CHARS:
            chunks.append(current)
            # keep a small tail of the previous chunk for context continuity
            current = current[-CHUNK_OVERLAP_CHARS:] + "\n\n" + para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        chunks.append(current)
    return chunks


def build_index() -> int:
    """Walks DOCS_DIR, chunks every supported file, and writes INDEX_FILE.

    Returns the number of chunks written.
    """
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    chunks: list[Chunk] = []
    next_id = 0
    files = sorted(p for p in DOCS_DIR.rglob("*") if p.is_file() and p.suffix.lower() in READERS)

    for path in files:
        reader = READERS[path.suffix.lower()]
        rel_source = str(path.relative_to(DOCS_DIR))
        for text, page in reader(path):
            for chunk_text in _chunk_text(text):
                chunks.append(Chunk(id=next_id, source=rel_source, page=page, text=chunk_text))
                next_id += 1

    INDEX_FILE.write_text(
        json.dumps([asdict(c) for c in chunks], indent=2),
        encoding="utf-8",
    )
    return len(chunks)
