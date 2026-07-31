"""Paths and shared configuration for the Postilion troubleshooting agent."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = PROJECT_ROOT / "docs"
INDEX_DIR = PROJECT_ROOT / ".index"
INDEX_FILE = INDEX_DIR / "chunks.json"

CLAUDE_MODEL = "claude-opus-5"
TOP_K = 8
