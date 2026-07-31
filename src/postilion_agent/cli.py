"""CLI entry point: `python -m postilion_agent.cli <index|ask> [...]`."""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from .config import DOCS_DIR
from .ingest import build_index
from .retrieval import IndexEmptyError, IndexNotBuiltError


def _cmd_index(_args: argparse.Namespace) -> int:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    count = build_index()
    if count == 0:
        print(
            f"No supported documents (.txt/.md/.pdf) found under {DOCS_DIR}. "
            "Add Postilion documentation there and re-run this command."
        )
        return 1
    print(f"Indexed {count} chunks from {DOCS_DIR}.")
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    from .agent import diagnose

    symptom = " ".join(args.symptom).strip()
    if not symptom:
        symptom = input("Describe the symptom: ").strip()
    if not symptom:
        print("No symptom provided.", file=sys.stderr)
        return 1

    try:
        diagnose(symptom)
    except (IndexNotBuiltError, IndexEmptyError) as e:
        print(str(e), file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="postilion-agent",
        description="AI troubleshooting agent for Postilion payment switch environments.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="(Re)build the doc index from docs/.")
    index_parser.set_defaults(func=_cmd_index)

    ask_parser = subparsers.add_parser("ask", help="Describe a symptom and get a diagnosis.")
    ask_parser.add_argument("symptom", nargs="*", help="The symptom, e.g. 'transaction declined with response code 61'")
    ask_parser.set_defaults(func=_cmd_ask)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
