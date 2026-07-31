from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"

    embedding_model: str = "BAAI/bge-base-en-v1.5"

    docs_dir: Path = Path("docs")
    runbooks_dir: Path = Path("runbooks")
    index_dir: Path = Path(".index")

    runbook_score_boost: float = 1.5


@lru_cache
def get_settings() -> Settings:
    return Settings()
