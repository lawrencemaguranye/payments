from dataclasses import dataclass


@dataclass
class Section:
    """A logically coherent block of source text under a heading (or page/slide)."""

    heading_path: list[str]
    text: str
    page: int | None = None
    slide: int | None = None


@dataclass
class Chunk:
    text: str
    heading_path: list[str]
    chunk_index: int
    page: int | None = None
    slide: int | None = None

    @property
    def citation_label(self) -> str:
        parts = []
        if self.heading_path:
            parts.append(" > ".join(self.heading_path))
        if self.page is not None:
            parts.append(f"p.{self.page}")
        if self.slide is not None:
            parts.append(f"slide {self.slide}")
        return " — ".join(parts) if parts else f"chunk {self.chunk_index}"


def chunk_sections(sections: list[Section], chunk_size: int = 1000, overlap: int = 150) -> list[Chunk]:
    """Split each section's text into overlapping chunks, never crossing a heading boundary."""
    chunks: list[Chunk] = []
    for section in sections:
        text = section.text.strip()
        if not text:
            continue
        for piece in _split_text(text, chunk_size, overlap):
            chunks.append(
                Chunk(
                    text=piece,
                    heading_path=section.heading_path,
                    chunk_index=len(chunks),
                    page=section.page,
                    slide=section.slide,
                )
            )
    return chunks


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    pieces = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        pieces.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return pieces
