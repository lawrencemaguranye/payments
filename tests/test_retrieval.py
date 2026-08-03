"""Retrieval tests with a stubbed embedder.

The real embedding model is a network download; these tests swap in a
deterministic bag-of-words vector so the indexer, the LanceDB store and the
ranking logic can all be exercised offline.
"""

import hashlib

import pytest

from postilion_agent.config import get_settings

DIM = 64


def _fake_vector(text: str) -> list[float]:
    counts = [0.0] * DIM
    for token in text.lower().split():
        counts[int(hashlib.sha256(token.encode()).hexdigest(), 16) % DIM] += 1.0
    norm = sum(c * c for c in counts) ** 0.5
    return [c / norm for c in counts] if norm else [0.0] * DIM


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    """A two-source corpus, indexed with the stub embedder."""
    from postilion_agent.ingest import indexer, store
    from postilion_agent import retrieval

    docs = tmp_path / "docs"
    runbooks = tmp_path / "runbooks"
    docs.mkdir()
    runbooks.mkdir()

    (docs / "manual.md").write_text(
        "# Active Active Deployment\nTwo realtime nodes process traffic concurrently.\n",
        encoding="utf-8",
    )
    (runbooks / "cutover.md").write_text(
        "# Draining\nSet node weight to zero and wait for traffic to settle.\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("DOCS_DIR", str(docs))
    monkeypatch.setenv("RUNBOOKS_DIR", str(runbooks))
    monkeypatch.setenv("INDEX_DIR", str(tmp_path / ".index"))
    get_settings.cache_clear()

    monkeypatch.setattr(store, "embedding_dim", lambda: DIM)
    monkeypatch.setattr(indexer, "embed_passages", lambda texts: [_fake_vector(t) for t in texts])
    monkeypatch.setattr(retrieval, "embed_query", _fake_vector)

    indexer.build_index()
    yield tmp_path
    get_settings.cache_clear()


def test_index_reports_both_sources(corpus):
    from postilion_agent.ingest.indexer import build_index

    # Re-running over an unchanged corpus must be a no-op, not a re-add.
    report = build_index()
    assert report.added == []
    assert report.unchanged == 2


def test_search_returns_cited_hits(corpus):
    from postilion_agent.retrieval import search

    hits = search("node weight traffic settle", top_k=5)
    assert hits
    top = hits[0]
    assert top.source_type == "runbook"
    assert "cutover.md" in top.citation
    assert "Draining" in top.citation


def test_runbook_boost_outranks_a_closer_doc(corpus, monkeypatch):
    """A runbook should win against a doc it only narrowly loses on raw similarity."""
    from postilion_agent import retrieval

    query = "active active deployment realtime nodes"

    monkeypatch.setattr(retrieval.get_settings(), "runbook_score_boost", 1.0, raising=False)
    unboosted = retrieval.search(query, top_k=5)
    assert unboosted[0].source_type == "doc", "doc should win on raw similarity"

    monkeypatch.setattr(retrieval.get_settings(), "runbook_score_boost", 50.0, raising=False)
    boosted = retrieval.search(query, top_k=5)
    assert boosted[0].source_type == "runbook", "a large boost must promote the runbook"


def test_type_filter_restricts_sources(corpus):
    from postilion_agent.retrieval import search

    hits = search("node weight traffic settle", top_k=5, source_type="doc")
    assert hits
    assert {h.source_type for h in hits} == {"doc"}


def test_empty_corpus_never_loads_the_model(tmp_path, monkeypatch):
    """Indexing nothing must not trigger the embedding-model download."""
    from postilion_agent.ingest import embed, indexer

    docs = tmp_path / "docs"
    runbooks = tmp_path / "runbooks"
    docs.mkdir()
    runbooks.mkdir()

    monkeypatch.setenv("DOCS_DIR", str(docs))
    monkeypatch.setenv("RUNBOOKS_DIR", str(runbooks))
    monkeypatch.setenv("INDEX_DIR", str(tmp_path / ".index"))
    get_settings.cache_clear()

    def explode() -> int:
        raise AssertionError("the embedding model must not be loaded for an empty corpus")

    monkeypatch.setattr(embed, "_model", explode)

    try:
        report = indexer.build_index()
        assert report.added == []
        assert report.unchanged == 0
        assert report.skipped == []
    finally:
        get_settings.cache_clear()


def test_search_without_an_index_raises(tmp_path, monkeypatch):
    from postilion_agent.retrieval import IndexNotBuiltError, search

    monkeypatch.setenv("INDEX_DIR", str(tmp_path / "empty-index"))
    get_settings.cache_clear()
    try:
        with pytest.raises(IndexNotBuiltError):
            search("anything")
    finally:
        get_settings.cache_clear()
