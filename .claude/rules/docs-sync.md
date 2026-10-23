---
paths:
  - "backend/**"
  - "frontend/src/**"
  - "frontend/package.json"
  - "scripts/**"
  - "justfile"
  - "docker-compose.yml"
  - ".pre-commit-config.yaml"
  - ".env.example"
  - "pyproject.toml"
---

# Docs sync

A code change is finished only when the docs describe it. Neighbours: `docs.md` for how docs are
written, `config.md` for env vars and tools.

## Who updates what

- Implementation docs (`docs/architecture.md`, `docs/tech.md`, `docs/guide/`, docstrings, READMEs) —
  `doc-writer` through `/document`, from the fact sheet and the code.
- Product docs (`docs/prd.md`, `docs/domain.md`, specs, `docs/plan.md`) — the main session, only with the
  user's approval.
- Decisions — `session_facts.py write-decisions` after the user confirms.

## You changed → Update

| You changed | Update |
|---|---|
| A model or a migration | `docs/architecture.md` «Data model» |
| A route or endpoint | `docs/architecture.md` «Routes and API» |
| A module's use case | its `docs/guide/` article and the docstrings |
| An env var | `.env.example`, `docs/tech.md` «Environment variables» |
| A dependency | `docs/tech.md` «Stack» |
| A `just` recipe, script or git hook | `docs/tech.md` «Dev environment and checks», `CLAUDE.md` «Commands» |
| `docker-compose.yml`, a Dockerfile | `docs/architecture.md` «Deploy» |
| A plan task landed | `docs/architecture.md` «Implementation status» 🛠 → ✅ |
| A choice between alternatives | the decision draft → ADR |
| A new or renamed file | `docs/architecture.md` «Repository structure» and the guide article header |

The same table is `EXPECTED_DOCS` in `.claude/skills/document/scripts/doc_plan.py`; change both together.

## Never

- Never leave a renamed heading with broken links to it.
- Never describe planned behavior as built.

Enforced by: `doc_plan.py` and the commit preflight report untouched docs; `scripts/check_doc_links.py`,
`scripts/check_doc_facts.py` in `just check` and the git hooks.
