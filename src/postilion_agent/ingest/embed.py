from functools import lru_cache

from sentence_transformers import SentenceTransformer

from postilion_agent.config import get_settings


@lru_cache
def _model() -> SentenceTransformer:
    return SentenceTransformer(get_settings().embedding_model)


def embed_passages(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = _model().encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    """Embed a search query.

    BGE retrieval models are trained with an instruction prefix on the query side
    only; passages are embedded bare. Omitting it measurably degrades recall, so
    apply it when the configured model is a BGE one and leave other models alone.
    """
    if "bge" in get_settings().embedding_model.lower():
        text = f"Represent this sentence for searching relevant passages: {text}"
    vector = _model().encode([text], normalize_embeddings=True, show_progress_bar=False)
    return vector[0].tolist()


def embedding_dim() -> int:
    return _model().get_sentence_embedding_dimension()
