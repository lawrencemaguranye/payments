# payments
Payments is an AI troubleshooting agent for Postilion payment switch environments. Describe a symptom — a declined transaction, a config error, an interface that won't come up — and the agent searches the Postilion documentation set to identify the likely cause and walk you through a resolution, citing the source material it relied on.

Built to cut the time between "something's broken in the switch" and "here's what to check first."

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in ANTHROPIC_API_KEY
```

## Usage

1. Drop Postilion documentation (`.txt`, `.md`, or `.pdf`) anywhere under `docs/`.
2. Build the search index:

   ```bash
   python -m postilion_agent.cli index
   ```

3. Ask about a symptom:

   ```bash
   python -m postilion_agent.cli ask "transaction declined with response code 61"
   ```

   Or run it with no arguments and it'll prompt you for the symptom.

Re-run `index` whenever the contents of `docs/` change. The index is stored locally under `.index/` and is not committed.

## How it works

- **Ingestion** (`src/postilion_agent/ingest.py`) chunks each doc into overlapping ~1200-character passages and writes them to a local JSON index.
- **Retrieval** (`src/postilion_agent/retrieval.py`) uses BM25 keyword search over that index — no embeddings API, no vector DB, fully offline once indexed.
- **Diagnosis** (`src/postilion_agent/agent.py`) sends the top-matching passages plus the symptom to Claude (`claude-opus-5`), with a system prompt that requires citing the source excerpts and refusing to guess when the docs don't cover the symptom.

## Status

The `docs/` folder is currently empty — the Postilion documentation set still needs to be gathered and added before this is useful end-to-end. The CLI, ingestion, retrieval, and Claude integration are wired up and ready to go once docs are in place.
