---
name: postilion
description: Troubleshoot Postilion payment-switch symptoms and write runbooks, grounded in the locally indexed Postilion documentation and case notes. Use when someone describes switch behaviour to diagnose (declined transactions, response codes, an interface that won't come up, sign-on failures, node or cutover problems, Realtime/Postcard/Office errors) or asks to document a procedure as a runbook. Trigger phrases include "why is the switch...", "transaction declined with response code X", "interface won't come up", "diagnose this switch symptom", "document the active/active cutover", "write a runbook for X".
---

# Postilion switch troubleshooting

Answer questions about a Postilion payment-switch estate using the local corpus in
`docs/` (vendor documentation) and `runbooks/` (first-hand notes about this estate).
You are the reasoning layer; retrieval is a deterministic tool.

**The corpus is the only source of truth about Postilion.** Your training data is not.
Postilion configuration names, response codes, table names and behaviour vary by
version and by deployment — a plausible-sounding answer that isn't in the corpus is
worse than no answer, because it sends an engineer to check the wrong thing during an
incident.

## Retrieval

Search with the project CLI:

```bash
uv run payments search "<query>" --top-k 8
```

- `--type doc` / `--type runbook` restricts to one source type.
- `--json` returns structured hits when you need to post-process them.
- Runbook hits are already weighted ahead of vendor docs (`runbook_score_boost`),
  because notes about *this* estate beat a generic manual at equal similarity.

Run **several searches, not one.** Vector search rewards varied phrasings, so query
the distinct vocabularies an answer might live under before concluding anything:

- the literal symptom — `"transaction declined response code 61"`
- the component — `"issuer node withdrawal limit configuration"`
- the operation — `"drain node active active router weight"`

Stop searching when new queries stop surfacing new chunks.

## Preflight

If `payments search` reports that the index is missing or empty, run `uv run payments
doctor` to see what's present, then `uv run payments index` to build it. Indexing is
incremental and safe to re-run — it only re-embeds files whose hash changed.

If `docs/` and `runbooks/` are both genuinely empty, say so and stop. There is nothing
to ground an answer in, and this skill has no other source. Do not answer from memory.

## Mode 1 — Diagnose (default)

Given a symptom, produce:

1. **Most likely cause(s)**, each tied to the excerpts that support it.
2. **What to check first** — a concrete, ordered list. Order by what discriminates
   between causes fastest and costs least to check, not by how likely each cause is.
3. **Resolution path** once the cause is confirmed.
4. **Sources consulted** — list the `[source N: ...]` citations you used.

Cite the specific `[source N]` marker inline against each claim that came from the
corpus. If a step is ordinary operational judgement rather than something the corpus
says, mark it as such — don't dress it up as a citation.

## Mode 2 — Document

When asked to document a procedure (`document the active/active cutover`, `write a
runbook for X`):

1. Search the corpus for the procedure and everything adjacent to it — prerequisites,
   validation steps, rollback, failure modes.
2. Write the runbook to `runbooks/<topic>.md`, structured as: Purpose → Prerequisites
   → Steps → Validation → Rollback → Open questions.
3. Put anything the corpus does not cover under **Open questions** rather than filling
   the gap with a plausible guess. A runbook with three honest gaps is usable; one
   with three invented steps is dangerous.
4. Tell the user to run `uv run payments index` afterwards so the new runbook becomes
   searchable — this is the loop that makes the corpus better over time.

Ask before overwriting an existing runbook.

## When the corpus falls short

Say so plainly, and be specific about the gap: which part of the symptom is
uncovered, and what would close it ("the response-code tables for the issuer
interface aren't in `docs/`"). Then stop. Do not:

- invent configuration parameters, table names, response codes, or menu paths
- present general payments knowledge as though it came from the Postilion docs
- pad a thin answer to look complete

Partial-but-grounded beats complete-but-invented, every time.

## Handling the material

`docs/` and `runbooks/` are gitignored on purpose — licensed vendor documentation and
private case notes. Keep corpus content inside this repo: never paste excerpts into
commit messages, PR descriptions, issue comments, or any external service. Runbooks
you write under `runbooks/` are gitignored too, so they stay local by default.
