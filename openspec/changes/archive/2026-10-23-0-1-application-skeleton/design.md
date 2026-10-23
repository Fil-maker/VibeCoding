# Design

## Context

Empty repository with the agent harness only. Stack and layout are fixed by ADRs 0001–0003,
`docs/architecture.md` «Repository structure» (planned) and `.claude/rules/server-architecture.md`.
The developer machine runs Windows 11 with Docker Desktop; `just` recipes run under PowerShell.

## Goals / Non-Goals

**Goals:**
- One command (`just dev`) starts database, backend and SPA; code edits reload without restarts.
- Every check of the strict bar runs on the new code from day one (`just check`, prek hooks).
- Test suites exist at each layer the later tasks will extend: backend unit, backend integration
  (PostgreSQL), frontend component.

**Non-Goals:**
- Production images, deploy, TLS, authentication, any product module.

## Decisions

### Everything runs in docker compose
`docker-compose.yml` services: `db` (`postgres:18`, healthcheck `pg_isready`, port 5432, volume, an init
script `docker/postgres/init/01-create-test-database.sql` creating the test database), `backend` (dev
image `docker/backend.Dockerfile`: python 3.12 slim + uv; bind mount `backend/`; the virtualenv in a
named volume; command `alembic upgrade head` then `uvicorn app.main:create_app --factory --reload --host
0.0.0.0 --port 8000`; `DATABASE_URL` overridden to host `db`; `WATCHFILES_FORCE_POLLING=true` because
file events do not cross the Windows bind mount), `frontend` (`node:24` + corepack pnpm; bind mount
`frontend/`, `node_modules` in a named volume; `vite --host 0.0.0.0`, polling watcher; proxy `/api` to
`http://backend:8000`). `depends_on` with `condition: service_healthy` for the database.
Alternatives: a Python launcher running uvicorn and Vite locally (recommended); three separate recipes.
Chosen by the user.

Local virtualenv and `node_modules` still exist (`just setup`) for the IDE, lint, type checks and tests,
which run on the host against the composed database (`localhost:5432`).

### Backend layout
`backend/app/main.py` holds `create_app()`; `backend/app/platform/` holds `settings.py`
(pydantic-settings, the only reader of env), `db.py` (lazy async engine and session factory, psycopg 3),
`logging.py`, `clock.py`; `backend/app/modules/health/` holds `router.py`, `schemas.py`, `service.py`,
`repository.py` (the `SELECT 1` ping). The ping has a 2 s timeout; a failure answers
`database: "unavailable"` and is logged, never raised to the client.
Driver psycopg 3 for both the app and Alembic. Alternative: asyncpg. Chosen by the user.

### Migrations
Alembic in `backend/migrations/` with an async `env.py` reading the URL from `Settings`; one empty
baseline revision so that `alembic check` and `upgrade head` work from the first task.

### API client
`just api-client` exports the schema (`uv run --directory backend python -m app.openapi`) to
`frontend/src/api/openapi.json` and generates types with `openapi-typescript` into
`frontend/src/api/generated/schema.ts`; `frontend/src/api/client.ts` creates the `openapi-fetch` client;
server data goes through TanStack Query. `just check` regenerates into a temporary file and fails when the
committed client differs. Alternatives: @hey-api/openapi-ts, Orval. Chosen by the user.

### Frontend layout and tooling
Vite + React + TypeScript; `frontend/src/main.tsx`, `frontend/src/App.tsx`,
`frontend/src/features/health/HealthStatus.tsx`; styling tokens in `frontend/src/styles/tokens.css`.
`tsc --strict` with `noUncheckedIndexedAccess`; ESLint flat config (typescript-eslint strict type-checked,
react-hooks, `react/no-danger`, `max-lines` 500); Prettier; Vitest with jsdom and Testing Library.
Scripts: `dev`, `build`, `lint`, `typecheck`, `format`, `format:check`, `test`.

### Checks and tests wiring
`scripts/run_checks.py` already runs the backend and frontend checks once their manifests exist; it gains
the client freshness check. prek gets backend ruff and pyright hooks and frontend ESLint, Prettier and
tsc hooks. Backend tests: `pytest` with `pytest-asyncio`; integration tests use `TEST_DATABASE_URL`.

### Interface

- `GET /api/v1/health` → `200` with `HealthStatus`:
  `{"status": "ok", "database": "ok" | "unavailable"}`. No other status codes; no authentication.
- `backend/app/main.py`: `create_app(settings: Settings | None = None) -> FastAPI`.
- `backend/app/platform/settings.py`: `Settings` with `database_url: str` (env `DATABASE_URL`).
- `backend/app/modules/health/schemas.py`: `HealthStatus` (pydantic), `DatabaseState = Literal["ok",
  "unavailable"]`.
- `backend/app/modules/health/service.py`: `async def get_health_status(...) -> HealthStatus`.
- Frontend: `HealthStatus` component (named export) in `frontend/src/features/health/HealthStatus.tsx`.
- UI texts (Russian, exact):
  - heading «Состояние сервиса»;
  - while loading «Проверяем…»;
  - backend answered: «Сервер: работает» and «База данных: доступна» or «База данных: недоступна»;
  - backend did not answer: «Сервер не отвечает».
- Recipes: `just dev`, `just db` (database only, detached), `just test-db` (database tests),
  `just api-client`.

## Risks / Trade-offs

- [File watching over Windows bind mounts is slow or silent] → polling watchers in both containers.
- [Host and container dependency sets drift] → both install from the same lock files (`uv.lock`,
  `pnpm-lock.yaml`); the container volumes are rebuilt by `docker compose up --build`.
- [Port 5432 already taken on the machine] → the host port comes from `.env` (`POSTGRES_PORT`, default
  5432).
- [Generated client goes stale] → the freshness check in `just check`.

## Migration Plan

No data exists. Rollback: delete the branch; `docker compose down -v` removes the volumes.
