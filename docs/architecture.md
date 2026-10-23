# Architecture

Updated 23.10.2026

**Status: the skeleton exists.** Task 0.1 «Application skeleton» built the backend, the SPA and the database
container; the mailbox reader and the analysis engine are not built yet.

## Contents

- [Implementation status](#implementation-status)
- [Components and processes](#components-and-processes)
- [Repository structure](#repository-structure)
- [Layers](#layers)
- [Data model](#data-model)
- [Routes and API](#routes-and-api)
- [Deploy](#deploy)
- [Security](#security)

## Implementation status

| Part | Status | Task |
|---|---|---|
| Application skeleton: backend, SPA, database | ✅ | 0.1 |

## Components and processes

- **Backend** — a FastAPI application (Python): the HTTP API, the analysis, the database access.
- **SPA** — a React + TypeScript single-page app built with Vite; talks to the backend only through an
  API client generated from the backend's OpenAPI schema.
- **Database** — PostgreSQL, in Docker for development.

TBD: the mailbox reader and the analysis engine (see [ideas.md](ideas.md#analysis-engine)).

## Repository structure

The tree below is the repository as it is now. The module folder is the pattern for the modules that follow.

```
backend/                 FastAPI application (own pyproject.toml, uv.lock)
  alembic.ini            Alembic config; the URL comes from the settings
  app/
    main.py              create_app(): app factory, routers, lifespan
    openapi.py           prints the OpenAPI schema as JSON
    platform/            settings, db (engine, session), logging, clock
    modules/<module>/    one folder per module; health is the first
  migrations/            Alembic: env.py, script.py.mako, versions/
  tests/integration/     database tests against TEST_DATABASE_URL
frontend/                React + TypeScript SPA (Vite, pnpm; own package.json, pnpm-lock.yaml)
  index.html             page shell: #root and the module script of main.tsx
  vite.config.ts         React plugin, /api proxy, Vitest settings
  eslint.config.js       ESLint, typed rules; .prettierrc.json, .prettierignore, tsconfig.json
  src/
    main.tsx             entry: mounts App into #root, loads the design tokens
    App.tsx              root component: QueryClientProvider and the health page
    api/
      client.ts          apiClient: openapi-fetch typed by the generated schema
      queryClient.ts     createQueryClient(): TanStack Query client
      openapi.json       OpenAPI schema from the backend (generated)
      generated/         schema.ts, types generated from openapi.json; never edited by hand
    features/health/     HealthStatus (page), useHealth (query), styles and tests
    styles/tokens.css    design tokens: colors, spacing, sizes, fonts
    test/setup.ts        Vitest setup: Testing Library cleanup, unstubbed globals
docker/                  backend.Dockerfile (dev image); postgres/init/ runs once, on the first start of the database
docker-compose.yml       development stack: database, backend, SPA; see Deploy
docs/                    product docs
openspec/                requirements and changes
scripts/                 doc checkers, the check runner (run_checks.py), the API client script (api_client.py)
.claude/                 the agent harness
```

## Layers

Built so far: the health module and the platform. The layer rules are in `.claude/rules/server-architecture.md`.

The health module is the pattern for the rest:

| Layer | File | What it does now |
|---|---|---|
| Router | `backend/app/modules/health/router.py` | `GET /api/v1/health`; takes a `HealthRepository` from a dependency and calls the service |
| Service | `backend/app/modules/health/service.py` | `get_health_status`: pings with a 2-second timeout, reports a failure as `unavailable` |
| Schemas | `backend/app/modules/health/schemas.py` | `HealthStatus`, the response model |
| Repository | `backend/app/modules/health/repository.py` | `HealthRepository` protocol; `SqlHealthRepository` runs `SELECT 1` |
| Platform | `backend/app/platform/` | settings, `Database` and the `get_database_session` dependency, logging, clock |

Dependencies point down: router → service → repository → platform. The session never reaches a router.
The session reaches a module through the FastAPI dependency `get_database_session` in
`backend/app/platform/db.py`. The module's `repository.py` builds its repository from that session, for
example `get_health_repository`; the router receives the repository, not the session. Tests replace
`get_health_repository` with a fake through `dependency_overrides`.

The health module has no domain, models or errors file yet; a module adds them when it needs them.
Details of the platform code and the health flow are in [Backend](guide/backend.md).

## Data model

No tables yet. The only Alembic revision is `0001` (`backend/migrations/versions/0001_baseline.py`), an
empty baseline that creates and drops nothing. The first module that owns tables adds its models and its
own revision. The declarative `Base` in `backend/app/platform/db.py` is the metadata Alembic works from.

## Routes and API

The OpenAPI schema generated by FastAPI is the contract. `backend/app/openapi.py` prints it; `just api-client`
writes it to `frontend/src/api/openapi.json` and regenerates the SPA's client in `frontend/src/api/generated/`.

| Method and path | Module | Response |
|---|---|---|
| `GET /api/v1/health` | health | 200, `HealthStatus` |

`HealthStatus` is `{"status": "ok", "database": "ok" | "unavailable"}`:

- `status` is always `"ok"`: the service answers.
- `database` is `"ok"` when `SELECT 1` answers within 2 seconds, and `"unavailable"` when the ping raises or times out.
  The route answers 200 in both cases; it declares no error responses.

The SPA's page «Состояние сервиса» reads this route through the generated client.

`.claude/rules/api-contract.md` governs the contract.

## Deploy

Not deployed. Local development only. `docker-compose.yml` runs three services:

- `db` — PostgreSQL 18; the host port comes from `POSTGRES_PORT` ([Environment variables](tech.md#environment-variables)).
- `backend` — built from `docker/backend.Dockerfile` (Python 3.12 with uv); runs `alembic upgrade head`, then
  uvicorn with `--reload` on port 8000.
- `frontend` — the `node:24` image; runs the Vite dev server on port 5173.

`just dev` starts all three; `just db` starts only the database. The database volume is initialized once:
`docker/postgres/init/01-create-test-database.sql` creates the test database `vibecoding_test` when the volume
is first created, and the integration tests use it.

## Security

- An employee reads only their own correspondence; the administrator reads all correspondence of their
  organization. The owner filter is applied in every query.
- The mailbox is accessed read-only.
- Email text is sent to a third-party service only after the administrator's consent.
