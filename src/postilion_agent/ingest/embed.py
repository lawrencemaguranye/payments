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


def embedding_dim() -> int:
    return _model().get_sentence_embedding_dimension()
