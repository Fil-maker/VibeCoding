---
paths:
  - "backend/app/**/models.py"
  - "backend/migrations/**"
  - "backend/alembic.ini"
---

# Database

Schema and migrations of PostgreSQL. Neighbours: `data-access.md` for queries, `docs-sync.md` for the
data model doc. Facts: `docs/architecture.md` «Data model».

## Rules

- `models.py` files are the source of the schema; `docs/architecture.md` «Data model» documents them.
- A schema change: edit the models, `alembic revision --autogenerate -m "<what>"`, read the generated
  migration and fix it by hand where needed, commit it with the models. After it, autogenerate must
  report no changes.
- Ids: UUID primary keys named `id`; foreign keys `<entity>_id`; tables plural snake_case.
- Timestamps `timestamptz`, set from the injected clock, never `now()` defaults in Python code paths.
- Closed sets stored as strings, validated by a `StrEnum` in code; no PostgreSQL enums.
- Every table with user data carries `organization_id`; correspondence carries its mailbox and owner.
- Deletes cascade from the organization and the mailbox; emails read from a mailbox are kept as the
  interaction history until their mailbox or organization is deleted.
- An assessment row records the analysis model and its version, and links to its evidence rows.
- JSON columns get a pydantic schema in code.

## Never

- Never edit a migration that has run anywhere; write a new one.
- Never apply schema changes outside Alembic.
- Never drop a column with data in the same migration that stops writing it.

Enforced by: the migration check in `/finish` (autogenerate reports no changes), review.
