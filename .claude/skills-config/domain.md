# Domain docs

How Matt Pocock's skills consume this repo's domain documentation. Single-context repo.

## Before exploring, read these

- **`docs/domain.md` «Glossary»**: the project's glossary. It takes the place of `CONTEXT.md`.
- **`docs/adr/`**: ADRs that touch the area you work in; the index is `docs/decisions.md`.

## Never create `CONTEXT.md` or `CONTEXT-MAP.md`

A skill that would create or update `CONTEXT.md` (`domain-modeling`, `grill-with-docs`) proposes the term
for `docs/domain.md` «Glossary» instead and writes it only after the user approves: it is a product doc.
One fact, one home.

## Decisions

Never write an ADR by hand. Record a decision the moment the user makes it:
`uv run --no-project python .claude/skills/document/scripts/session_facts.py . decide --what "…" --why "…" --who human`;
`/document` turns confirmed decisions into ADRs.

## Use the glossary's vocabulary

When your output names a domain concept (a task title, a refactor proposal, a hypothesis, a test name),
use the term as defined in `docs/domain.md` «Glossary». Don't drift to synonyms. A concept missing from the
glossary is a signal: either you invent language the project doesn't use, or there is a real gap to raise
with the user.

## Flag ADR conflicts

If your output contradicts an existing ADR, say so explicitly rather than silently overriding:

> _Contradicts ADR-0003 (PostgreSQL), but worth reopening because…_
