import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from postilion_agent.config import Settings, get_settings
from postilion_agent.ingest.chunker import chunk_sections
from postilion_agent.ingest.embed import embed_passages
from postilion_agent.ingest.parsers import UnsupportedFileType, parse_document
from postilion_agent.ingest.store import add_chunks, connect, delete_source, get_table

MANIFEST_NAME = "manifest.json"


@dataclass
class IndexReport:
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    unchanged: int = 0
    skipped: list[tuple[str, str]] = field(default_factory=list)


def _manifest_path(settings: Settings) -> Path:
    return settings.index_dir / MANIFEST_NAME


def _load_manifest(settings: Settings) -> dict:
    path = _manifest_path(settings)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_manifest(settings: Settings, manifest: dict) -> None:
    _manifest_path(settings).write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _discover(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*") if p.is_file() and p.name != ".gitkeep")


def build_index(settings: Settings | None = None) -> IndexReport:
    settings = settings or get_settings()
    settings.index_dir.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest(settings)
    table = get_table(connect())

    sources: list[tuple[Path, str, str]] = []
    for root, source_type in ((settings.docs_dir, "doc"), (settings.runbooks_dir, "runbook")):
        for path in _discover(root):
            key = f"{source_type}:{path.relative_to(root).as_posix()}"
            sources.append((path, key, source_type))

    report = IndexReport()
    seen_keys: set[str] = set()

    for path, key, source_type in sources:
        seen_keys.add(key)
        digest = _hash_file(path)
        prior = manifest.get(key)
        if prior and prior["hash"] == digest:
            report.unchanged += 1
            continue

        try:
            sections = parse_document(path)
        except UnsupportedFileType:
            report.skipped.append((str(path), "unsupported file type"))
            continue
        except Exception as exc:  # noqa: BLE001 - one bad document must not abort the whole run
            report.skipped.append((str(path), f"{type(exc).__name__}: {exc}"))
            continue

        chunks = chunk_sections(sections)
        if not chunks:
            report.skipped.append((str(path), "no extractable text"))
            continue

        vectors = embed_passages([c.text for c in chunks])
        rows = [
            {
                "chunk_id": f"{key}::{c.chunk_index}",
                "source_path": key,
                "source_type": source_type,
                "heading_path": " > ".join(c.heading_path),
                "page": c.page,
                "slide": c.slide,
                "text": c.text,
                "vector": vector,
            }
            for c, vector in zip(chunks, vectors)
        ]

        delete_source(table, key)
        add_chunks(table, rows)
        manifest[key] = {"hash": digest, "chunk_count": len(rows)}
        (report.added if prior is None else report.updated).append(str(path))

    for key in list(manifest.keys()):
        if key not in seen_keys:
            delete_source(table, key)
            del manifest[key]
            report.removed.append(key)

    _save_manifest(settings, manifest)
    return report
