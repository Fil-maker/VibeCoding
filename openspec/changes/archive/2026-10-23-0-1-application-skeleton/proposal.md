# Proposal

## Why

Plan task 0.1 «Application skeleton» (FR: none). Nothing runs yet: every later task needs a backend, an
SPA and a database that start with one command, pass the strict checks and have test suites to extend.
A health status page proves the whole chain (SPA → generated client → API → database) end to end.

## What Changes

- A FastAPI backend in `backend/` with the platform layer (settings, database, logging, clock) and one
  module `health` serving `GET /api/v1/health`.
- Alembic set up with an empty baseline migration.
- A React + TypeScript SPA in `frontend/` (Vite, pnpm) with one page showing the service status in
  Russian, read through a client generated from the backend's OpenAPI schema.
- `docker-compose.yml` running PostgreSQL, the backend with reload and the Vite dev server; a test
  database next to the dev one.
- `just dev`, `just db`, `just test-db`, `just api-client`; `just setup`, `just check`, `just format` and
  `/test` extended with the backend and frontend; prek hooks for both.
- Backend unit and integration tests and a frontend component test for the health status.
- `.claude/launch.json` for the preview server.

## Capabilities

### New Capabilities

None: the change is technical (`skip_specs: true`). The health status is a service check, not product
behavior.

### Modified Capabilities

None.

## Impact

- New code: `backend/`, `frontend/`, `docker-compose.yml`, `docker/`.
- Changed tooling: `justfile`, `.pre-commit-config.yaml`, `scripts/run_checks.py`,
  `.claude/skills/test/scripts/run_tests.py` (only if its suite commands need adjusting), `.env.example`.
- New runtime dependencies (backend): fastapi, uvicorn, pydantic-settings, SQLAlchemy, psycopg, Alembic;
  (frontend): react, react-dom, @tanstack/react-query, openapi-fetch. Dev: pytest, httpx, openapi-typescript,
  Vitest, Testing Library, ESLint, Prettier.
- Invariants touched: none. No mailbox, no analysis, no user data.

Out of scope: authentication and organizations, mail reading, analysis, a design system, deployment.
Nothing deferred to `docs/ideas.md`.
