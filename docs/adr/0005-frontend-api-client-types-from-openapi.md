# Frontend API client: types from openapi-typescript, calls through openapi-fetch, server data through TanStack Query

Id: 0005 · Date: 23.10.2026 · Kind: technical · Status: Accepted · Who: [human]

## Context
Task: 0.1.
- Change 0-1-application-skeleton approved on 2026-10-23; new env var POSTGRES_PORT (default 5432) planned
- Task 0.1 built the application skeleton: FastAPI backend (backend/), React + TypeScript SPA (frontend/), PostgreSQL 18 in Docker; the SPA page «Состояние сервиса» shows «Сервер: работает» and «База данных: доступна / недоступна» from GET /api/v1/health through the generated API client
- just dev runs docker compose up --build: db (postgres:18), backend (alembic upgrade head, then uvicorn with reload, port 8000) and frontend (Vite dev server on node:24, port 5173); just db starts only the database detached and waits until healthy; just test-db runs the database tests; just api-client regenerates the SPA's API client
- scripts/api_client.py has two commands: generate (writes frontend/src/api/openapi.json and frontend/src/api/generated/schema.ts from the backend's OpenAPI schema) and check (read-only; fails when the committed client is stale); check runs in just check as frontend-api-client
- Version pins below the latest majors: TypeScript 6.0.3 because typescript-eslint 8.72 requires <6.1.0; ESLint 9.39.5 because eslint-plugin-react 7.37.5 crashes on ESLint 10
- VITE_PROXY_TARGET: the Vite dev server proxies /api to it; docker compose sets http://backend:8000, the fallback is http://localhost:8000; POSTGRES_PORT is the host port of the PostgreSQL container, default 5432
- TEST_DATABASE_URL is read by a small settings class in backend/tests/integration/conftest.py, not by app Settings; Settings keeps only database_url; docker/postgres/init/01-create-test-database.sql creates the test database on first start of the container
- On Windows psycopg async needs a selector event loop; backend/migrations/env.py and the integration conftest set it
- The DB session reaches a module through the FastAPI dependency get_database_session in backend/app/platform/db.py; a module's repository.py builds its repository from it (health: get_health_repository), so routers never touch the session
- Frontend unit tests (Vitest) run in just test and /test, not in just check, which stays static
- Known issue: the frontend container downloads pnpm through corepack on every start, and Docker's embedded DNS on this machine intermittently fails (EAI_AGAIN for registry.npmjs.org), so the first just dev may need a retry

## Decision
Frontend API client: types from openapi-typescript, calls through openapi-fetch, server data through TanStack Query

## Alternatives
@hey-api/openapi-ts; Orval

## Reason
accepted the recommendation
