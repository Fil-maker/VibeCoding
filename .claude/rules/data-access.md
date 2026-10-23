---
paths:
  - "backend/app/**/repository.py"
  - "backend/app/**/service.py"
  - "backend/app/platform/db.py"
  - "backend/tests/integration/**"
---

# Data access

Who queries the database and how. Neighbours: `server-architecture.md` for layers, `database.md` for
schema and migrations. Facts: `docs/architecture.md` «Data model», «Security».

## Rules

- Only `repository.py` builds queries; services call repositories; routers never touch the session.
- One use case, one transaction, opened by the service (`async with session.begin()`).
- Owner first: every query over correspondence, assessments or counterparties filters by the owner
  scope — the employee's own mailboxes, or the whole organization for its administrator. The scope comes
  from the auth context, never from the request body or query string.
- Another organization's data is unreachable: every query also filters by `organization_id`.
- SQLAlchemy expressions or bound parameters only; never build SQL from strings.
- Bounded reads: every list query has a limit and a stable order; pagination by keyset.
- No network call inside an open transaction (mail fetch, analysis engine); use an outbox table for work
  that must follow a commit.
- Races through unique constraints or row locks (`with_for_update`), not an application check alone.
- One engine and pool per process, from `backend/app/platform/db.py`.
- Databases: dev = `DATABASE_URL`, tests = `TEST_DATABASE_URL` (the TDD sandbox adds a suffix);
  the laptop never touches a production database.
- Schema changes only through Alembic (`backend/migrations/`).

## Never

- Never return an entity to a caller who is outside its owner scope; answer «not found».
- Never log query parameters that contain email text or addresses.

Enforced by: integration tests for another user's data, review (`invariant-reviewer`).
