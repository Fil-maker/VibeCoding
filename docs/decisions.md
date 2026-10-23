# Decisions

Updated 23.10.2026

The index of product and technical decisions. Each decision is an ADR file in [adr/](adr/README.md) with
its context, alternatives and reason. Rows are only appended; a replaced decision is marked
«Superseded by …», never deleted. ADRs are written by the decision draft script after the user confirms
them.

## Product decisions

| Date | ADR | Decision | Who | Status |
|---|---|---|---|---|

## Technical decisions

| Date | ADR | Decision | Who | Status |
|---|---|---|---|---|
| 23.10.2026 | [0001](adr/0001-fastapi-backend.md) | Backend in Python with FastAPI | [human] | Accepted |
| 23.10.2026 | [0002](adr/0002-react-spa.md) | UI as a React + TypeScript SPA talking to the FastAPI API | [human] | Accepted |
| 23.10.2026 | [0003](adr/0003-postgresql.md) | PostgreSQL in Docker as the database | [human] | Accepted |
| 23.10.2026 | [0004](adr/0004-task-0-1-runs-as-a.md) | Task 0.1 runs as a technical change without specs (skip_specs) | [human] | Accepted |
| 23.10.2026 | [0005](adr/0005-frontend-api-client-types-from-openapi.md) | Frontend API client: types from openapi-typescript, calls through openapi-fetch, server data through TanStack Query | [human] | Accepted |
| 23.10.2026 | [0006](adr/0006-postgresql-driver-psycopg-3-for-the.md) | PostgreSQL driver: psycopg 3 for the async app and Alembic | [human] | Accepted |
| 23.10.2026 | [0007](adr/0007-just-dev-runs-everything-in-docker.md) | just dev runs everything in docker compose: database, backend with reload, Vite dev server | [human] | Accepted |
