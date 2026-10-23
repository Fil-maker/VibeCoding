---
paths:
  - "docs/**"
  - "openspec/**"
  - "README.md"
  - "CHANGELOG.md"
---

# Docs

How product docs and requirements are written. Neighbours: `docs-sync.md` for which docs a code change
updates, `versioning.md` for the CHANGELOG and release notes. The index is `docs/README.md`.

## Where each fact lives

| File | Holds | Never holds |
|---|---|---|
| `docs/prd.md` | Problem, users, value, principles, business functions, user flow, stages, metrics, risks | Requirement details, libraries |
| `docs/domain.md` | Glossary, lifecycles, requirements map, explanations and examples, data kept, cancelled FR numbers | Requirement texts, implementation |
| `openspec/specs/<capability>/spec.md` | Requirements `FR-N` with SHALL/MUST and scenarios | Rationale, libraries, tables, files |
| `docs/architecture.md` | Implementation status, components, repository tree, layers, data model, API, deploy, security | Versions, commands, env vars, decision history |
| `docs/tech.md` | Stack with reasons, dev environment, env vars, techniques | Behavior, data model |
| `docs/decisions.md` + `docs/adr/` | Decisions: date, decision, alternatives, reason, who | The current state |
| `docs/plan.md` | Code tasks with «Done when» | Non-code tasks (`setup.md`), ideas |
| `docs/ideas.md` | Unplanned ideas, technical backlog | Committed work |
| `docs/tech-debt.md` | What works wrong now | Improvements |
| `docs/guide/` | How each part works and how to change it | Copies of architecture or tech facts |

One fact, one home: link to it, never copy it. Docs describe the product, not the Claude Code setup.

## Writing

- Every docs folder has a `README.md` index, one row per file; a new document gets a row there and in
  `docs/README.md`.
- Headings carry no numbers. Link by heading: `[Glossary](domain.md#glossary)`; in code and rules:
  `docs/domain.md «Glossary»`. Renaming a heading fixes every link to it in the same change.
- `domain.md`, `architecture.md`, `tech.md` start with a table of contents of `##`/`###` headings.
- `prd.md`, `domain.md`, `plan.md` carry `Version 0.N · DD.MM.YYYY` and a `Changes in 0.N: …` line per
  substantive edit, newest first; other docs carry `Updated DD.MM.YYYY`. Editions are not product versions.
- Product docs (`prd.md`, `domain.md`, specs, `plan.md`) change only with the user's approval, by the main
  session. Implementation docs are written by `doc-writer` through `/document`.

## Requirements

- `### Requirement: FR-N <name>`; a new number is max + 1 over the specs, open changes and the
  `Last FR number:` line in the `docs/domain.md` header. Numbers are never reused; a removed one goes to «Cancelled numbers».
- Text up to about 500 characters with SHALL or MUST and at least one `#### Scenario:` with WHEN/THEN.
- Behavior only. Concrete values and glossary terms. Negative cases: another user's correspondence, an
  employee versus the administrator, empty or too long input, a repeated action, deleted data.
- One capability, one spec; `docs/domain.md` «Requirements map» lists capability → FR numbers.

## Decisions

- An ADR `docs/adr/NNNN-<slug>.md` plus a row in `docs/decisions.md` — written by
  `session_facts.py write-decisions` after the user confirms, never by hand.
- Rows are only appended; a replaced decision becomes «Superseded by NNNN», never deleted.
- Who: **[human]**, **[AI → accepted]**, **[AI → to review]**.

## Never

- Never edit, rename or delete a committed note in `docs/journal/` or a published release note.
- Never put Claude Code setup into `docs/`.

Enforced by: `scripts/check_doc_links.py` and `scripts/check_doc_facts.py` (`just check`, git hooks
`doc-links`, `doc-facts`), the journal guard hook, `openspec validate --specs --strict`.
