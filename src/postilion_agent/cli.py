import json as jsonlib
from pathlib import Path
from typing import Optional

import typer

from postilion_agent.config import get_settings

app = typer.Typer(help="AI troubleshooting agent for Postilion payment-switch environments.")


@app.command()
def doctor() -> None:
    """Check that the environment is configured correctly."""
    settings = get_settings()

    def count_files(path: Path) -> int:
        return sum(1 for p in path.rglob("*") if p.is_file() and p.name != ".gitkeep")

    checks = [
        ("ANTHROPIC_API_KEY", "set" if settings.anthropic_api_key else "MISSING - add it to .env"),
        ("Reasoning model", settings.anthropic_model),
        ("Embedding model", settings.embedding_model),
        ("docs/", f"{count_files(settings.docs_dir)} file(s)" if settings.docs_dir.exists() else "MISSING"),
        ("runbooks/", f"{count_files(settings.runbooks_dir)} file(s)" if settings.runbooks_dir.exists() else "MISSING"),
        ("index/", "built" if count_files(settings.index_dir) else "not built yet (run `payments index`)"),
    ]

    width = max(len(label) for label, _ in checks)
    for label, value in checks:
        typer.echo(f"{label.ljust(width)}  {value}")


@app.command()
def index() -> None:
    """Build or incrementally update the local vector index from docs/ and runbooks/."""
    from postilion_agent.ingest.indexer import build_index

    typer.echo("Indexing corpus...")
    report = build_index()

    typer.echo(f"Added:     {len(report.added)}")
    typer.echo(f"Updated:   {len(report.updated)}")
    typer.echo(f"Removed:   {len(report.removed)}")
    typer.echo(f"Unchanged: {report.unchanged}")
    if report.skipped:
        typer.echo(f"Skipped:   {len(report.skipped)}")
        for path, reason in report.skipped:
            typer.echo(f"  - {path}: {reason}")


@app.command()
def search(
    query: str = typer.Argument(..., help="Symptom or topic to search the corpus for."),
    top_k: int = typer.Option(8, "--top-k", "-k", help="Number of chunks to return."),
    source_type: Optional[str] = typer.Option(
        None, "--type", help="Restrict to a single source type: 'doc' or 'runbook'."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of text blocks."),
) -> None:
    """Search the indexed corpus and print the most relevant chunks with citations."""
    from postilion_agent.retrieval import IndexNotBuiltError, format_hits
    from postilion_agent.retrieval import search as run_search

    if source_type and source_type not in {"doc", "runbook"}:
        typer.echo("--type must be 'doc' or 'runbook'.", err=True)
        raise typer.Exit(2)

    try:
        hits = run_search(query, top_k=top_k, source_type=source_type)
    except IndexNotBuiltError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    if not hits:
        typer.echo(
            "No relevant material found for that query. Try rephrasing, or add "
            "documentation to docs/ or runbooks/ and re-run `payments index`.",
            err=True,
        )
        raise typer.Exit(1)

    if json_output:
        payload = [
            {
                "source": hit.citation,
                "source_path": hit.source_path,
                "source_type": hit.source_type,
                "heading_path": hit.heading_path,
                "page": hit.page,
                "slide": hit.slide,
                "score": round(hit.score, 4),
                "text": hit.text,
            }
            for hit in hits
        ]
        typer.echo(jsonlib.dumps(payload, indent=2))
        return

    typer.echo(format_hits(hits))


if __name__ == "__main__":
    app()
