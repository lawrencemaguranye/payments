from pathlib import Path

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


if __name__ == "__main__":
    app()
