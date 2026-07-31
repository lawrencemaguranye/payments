"""BM25 keyword search over the chunk index built by ingest.py."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache

from rank_bm25 import BM25Okapi

from .config import INDEX_FILE

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass
class SearchResult:
    source: str
    page: int | None
    text: str
    score: float


class IndexNotBuiltError(RuntimeError):
    pass


class IndexEmptyError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _load_corpus() -> list[dict]:
    if not INDEX_FILE.exists():
        raise IndexNotBuiltError(
            f"No index found at {INDEX_FILE}. Add Postilion docs to docs/ and run "
            "`python -m postilion_agent.cli index` first."
        )
    chunks = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    if not chunks:
        raise IndexEmptyError(
            "The index is empty — no supported documents (.txt/.md/.pdf) were found "
            "under docs/. Add Postilion documentation and re-run "
            "`python -m postilion_agent.cli index`."
        )
    return chunks


@lru_cache(maxsize=1)
def _load_bm25() -> tuple[BM25Okapi, list[dict], list[set[str]]]:
    chunks = _load_corpus()
    tokenized = [_tokenize(c["text"]) for c in chunks]
    token_sets = [set(t) for t in tokenized]
    return BM25Okapi(tokenized), chunks, token_sets


def search(query: str, top_k: int) -> list[SearchResult]:
    bm25, chunks, token_sets = _load_bm25()
    query_tokens = set(_tokenize(query))
    scores = bm25.get_scores(_tokenize(query))
    # BM25 IDF can go negative for terms common across a small corpus (trivial
    # with few documents), so rank by score rather than filtering on score > 0.
    # Instead, drop chunks that share no token with the query at all.
    candidates = [i for i in range(len(chunks)) if query_tokens & token_sets[i]]
    ranked = sorted(candidates, key=lambda i: scores[i], reverse=True)[:top_k]
    return [
        SearchResult(
            source=chunks[i]["source"],
            page=chunks[i]["page"],
            text=chunks[i]["text"],
            score=float(scores[i]),
        )
        for i in ranked
    ]
