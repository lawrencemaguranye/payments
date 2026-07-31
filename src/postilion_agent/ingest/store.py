import lancedb
import pyarrow as pa

from postilion_agent.config import get_settings
from postilion_agent.ingest.embed import embedding_dim

TABLE_NAME = "chunks"


def _schema(dim: int) -> pa.Schema:
    return pa.schema(
        [
            pa.field("chunk_id", pa.string()),
            pa.field("source_path", pa.string()),
            pa.field("source_type", pa.string()),
            pa.field("heading_path", pa.string()),
            pa.field("page", pa.int64()),
            pa.field("slide", pa.int64()),
            pa.field("text", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), dim)),
        ]
    )


def connect() -> lancedb.DBConnection:
    return lancedb.connect(str(get_settings().index_dir / "lancedb"))


def get_table(db: lancedb.DBConnection | None = None) -> lancedb.table.Table:
    db = db or connect()
    if TABLE_NAME in db.table_names():
        return db.open_table(TABLE_NAME)
    return db.create_table(TABLE_NAME, schema=_schema(embedding_dim()))


def delete_source(table: lancedb.table.Table, source_path: str) -> None:
    safe_path = source_path.replace("'", "''")
    table.delete(f"source_path = '{safe_path}'")


def add_chunks(table: lancedb.table.Table, rows: list[dict]) -> None:
    if rows:
        table.add(rows)
