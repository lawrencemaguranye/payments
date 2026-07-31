"""Calls Claude to diagnose a Postilion symptom using retrieved doc chunks."""

from __future__ import annotations

import os

import anthropic

from .config import CLAUDE_MODEL, TOP_K
from .retrieval import SearchResult, search

SYSTEM_PROMPT = """\
You are a troubleshooting expert for Postilion payment switch environments.

You will be given a symptom described by an engineer (a declined transaction, a \
config error, an interface that won't come up, etc.) along with excerpts pulled \
from the Postilion documentation set. Your job:

1. Identify the most likely cause(s) of the symptom, grounded in the provided \
   excerpts.
2. Give a concrete, ordered list of things to check first.
3. Give a resolution path once the cause is confirmed.
4. Cite the source excerpt(s) you relied on for each claim, using the [source] \
   markers given with each excerpt.

Only use the provided excerpts as your source of truth about Postilion — do not \
invent configuration names, error codes, or behavior that isn't grounded in them. \
If the excerpts don't cover the symptom, say so plainly and describe what \
information or documentation would be needed instead of guessing.
"""


def _format_context(results: list[SearchResult]) -> str:
    blocks = []
    for i, r in enumerate(results, start=1):
        loc = f"{r.source}" + (f", page {r.page}" if r.page else "")
        blocks.append(f"[source {i}: {loc}]\n{r.text}")
    return "\n\n---\n\n".join(blocks)


def diagnose(symptom: str) -> None:
    """Retrieves relevant doc chunks and streams Claude's diagnosis to stdout."""
    if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        raise RuntimeError(
            "No Anthropic credentials found. Set ANTHROPIC_API_KEY (see .env.example) "
            "before running `ask`."
        )

    results = search(symptom, top_k=TOP_K)
    if not results:
        print(
            "No relevant material found in the indexed Postilion docs for that "
            "symptom. Try rephrasing, or add more documentation to docs/ and "
            "re-run `python -m postilion_agent.cli index`.\n"
        )
        return

    context = _format_context(results)
    client = anthropic.Anthropic()

    user_message = f"Symptom:\n{symptom}\n\nRelevant documentation excerpts:\n\n{context}"

    with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        stream.get_final_message()

    print("\n\nSources consulted:")
    for i, r in enumerate(results, start=1):
        loc = f"{r.source}" + (f", page {r.page}" if r.page else "")
        print(f"  [{i}] {loc}")
