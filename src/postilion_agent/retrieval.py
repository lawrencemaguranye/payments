"""Vector search over the chunk index built by `payments index`."""

from dataclasses import dataclass

from postilion_agent.config import Settings, get_settings
from postilion_agent.ingest.embed import embed_query
from postilion_agent.ingest.store import connect, get_table, table_exists

# Boosting reorders results, so the boost has to be applied to a wider slice than
# the caller asked for - otherwise a runbook ranked just outside top_k by raw
# score can never be promoted into it.
OVERFETCH_FACTOR = 4


class IndexNotBuiltError(RuntimeError):
    pass


@dataclass
class SearchHit:
    chunk_id: str
    source_path: str
    source_type: str
    heading_path: str
    page: int | None
    slide: int | None
    text: str
    score: float

    @property
    def citation(self) -> str:
        """Human-readable location, e.g. `runbook:cutover.md — Rollback > Step 3 — p.4`."""
        parts = [self.source_path]
        if self.heading_path:
            parts.append(self.heading_path)
        if self.page is not None:
            parts.append(f"p.{self.page}")
        if self.slide is not None:
            parts.append(f"slide {self.slide}")
        return " — ".join(parts)


def search(
    query: str,
    top_k: int = 8,
    source_type: str | None = None,
    settings: Settings | None = None,
) -> list[SearchHit]:
    """Return the chunks most relevant to `query`, runbooks weighted ahead of docs.

    Runbooks are first-hand notes about this estate, so a runbook hit is worth more
    than a vendor-manual hit of the same raw similarity. `runbook_score_boost`
    controls how much more.
    """
    settings = settings or get_settings()

    db = connect()
    if not table_exists(db):
        raise IndexNotBuiltError(
            "No index found. Add material to docs/ or runbooks/ and run `payments index` first."
        )

    table = get_table(db)
    if table.count_rows() == 0:
        raise IndexNotBuiltError(
            "The index is empty - no supported documents were found under docs/ or "
            "runbooks/. Add material and re-run `payments index`."
        )

    builder = table.search(embed_query(query)).metric("cosine")
    if source_type:
        safe = source_type.replace("'", "''")
        builder = builder.where(f"source_type = '{safe}'")

    rows = builder.limit(max(top_k * OVERFETCH_FACTOR, top_k)).to_list()

    hits = []
    for row in rows:
        # LanceDB reports cosine *distance*; flip it so larger means more relevant.
        score = 1.0 - float(row["_distance"])
        if row["source_type"] == "runbook":
            score *= settings.runbook_score_boost
        hits.append(
            SearchHit(
                chunk_id=row["chunk_id"],
                source_path=row["source_path"],
                source_type=row["source_type"],
                heading_path=row["heading_path"],
                page=row["page"],
                slide=row["slide"],
                text=row["text"],
                score=score,
            )
        )

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k]


def format_hits(hits: list[SearchHit]) -> str:
    """Render hits as `[source N: location]` blocks for a reader to cite back."""
    blocks = []
    for i, hit in enumerate(hits, start=1):
        blocks.append(f"[source {i}: {hit.citation}]\n{hit.text}")
    return "\n\n---\n\n".join(blocks)
