from functools import lru_cache

from sentence_transformers import SentenceTransformer

from postilion_agent.config import get_settings


class EmbeddingModelUnavailable(RuntimeError):
    pass


@lru_cache
def _model() -> SentenceTransformer:
    name = get_settings().embedding_model
    try:
        return SentenceTransformer(name)
    except Exception as exc:  # noqa: BLE001 - surface any load failure as one actionable error
        raise EmbeddingModelUnavailable(
            f"Could not load the embedding model '{name}': {exc}\n\n"
            "It is downloaded from huggingface.co on first use and cached locally "
            "afterwards, so this usually means the machine cannot reach HuggingFace. "
            "Either run the first index on a machine that can, or set EMBEDDING_MODEL "
            "to one already in the local cache."
        ) from exc


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
