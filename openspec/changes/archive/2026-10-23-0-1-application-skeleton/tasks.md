# Tasks

Technical change (`skip_specs`): no scenarios, so no TDD sandbox; `code-writer` writes the tests with the
code (test-first where the behavior is clear). Docs are updated at `/finish` through `/document`.

## 1. Backend

- [x] 1.1 Create `backend/` (own `pyproject.toml`, Python 3.12, uv lock, ruff and pyright strict config, pytest config) with the dependencies of design «Backend layout» — check - `uv sync --directory backend` succeeds and `uv run --directory backend ruff check .` and `pyright` are clean
- [x] 1.2 Platform layer: `settings.py`, `db.py`, `logging.py`, `clock.py` per design — check - a unit test shows `Settings` reads `DATABASE_URL` and fails loudly when it is missing
- [x] 1.3 Module `health` and `create_app()` serving `GET /api/v1/health` per design «Interface» — check - unit tests with a fake repository cover `database: "ok"` and `"unavailable"` (ping raises or times out)
- [x] 1.4 Alembic with async `env.py` and an empty baseline revision — check - `alembic upgrade head` and `alembic check` succeed against the test database
- [x] 1.5 `backend/app/openapi.py` printing the schema — check - the output is valid JSON with the path `/api/v1/health`
- [x] 1.6 Integration test of `GET /api/v1/health` against `TEST_DATABASE_URL` — check - `run_tests.py . db` passes with the database up and exits 2 with a plain message when Docker is down

## 2. Frontend

- [x] 2.1 Create `frontend/` with Vite, React, TypeScript strict, ESLint, Prettier, Vitest, pnpm lock and the scripts of design «Frontend layout and tooling» — check - `pnpm --dir frontend lint`, `typecheck`, `format:check`, `build` pass
- [x] 2.2 `just api-client`: schema export and `openapi-typescript` generation; `client.ts` with `openapi-fetch`; TanStack Query provider — check - the generated `schema.ts` contains `/api/v1/health` and the typecheck passes
- [x] 2.3 `HealthStatus` page with the exact Russian texts of design «Interface» and styling tokens — check - Vitest tests cover loading, both database states and «Сервер не отвечает»

## 3. Compose and commands

- [x] 3.1 `docker-compose.yml`, `docker/backend.Dockerfile`, the test-database init script, compose env in `.env.example` (`POSTGRES_PORT`) — check - `docker compose config` is valid and `docker compose up -d db` gets healthy
- [x] 3.2 `justfile`: `dev`, `db`, `test-db`, `api-client`; `setup` installs the backend and frontend; `format` covers both — check - `just --list` shows them and each runs under PowerShell
- [x] 3.3 `scripts/run_checks.py` gains the client freshness check; prek gets backend and frontend hooks — check - `just check` runs every check to the end and passes; `prek run --all-files` passes
- [x] 3.4 `.claude/launch.json` with the preview of the composed SPA — check - the preview opens the page

## 4. Verification

- [x] 4.1 `just check` passes — check - all PASS
- [x] 4.2 `/test` with `all` passes — check - backend unit, backend database and frontend suites report counts, none NOT PRESENT
- [x] 4.3 Manual flow: `flow-checker` opens the preview, sees «Состояние сервиса», «Сервер: работает», «База данных: доступна»; after `docker compose stop db` sees «База данных: недоступна» — check - its PASS report

## 5. Done when

- [x] 5.1 `just dev` starts the database, the backend and the SPA — check - manual run, all three containers up
- [x] 5.2 The SPA page shows the backend's health status, in Russian, read through the generated API client — check - 4.3 and the component tests
- [x] 5.3 `just check` and `just test-all` pass with the backend and frontend checks included — check - 4.1 and 4.2

## Workflow follow-up

- `/finish 0.1`: invariant review, `openspec archive 0-1-application-skeleton --yes --skip-specs`, `/document` (architecture «Implementation status» ✅, «Repository structure», «Routes and API», «Deploy»; tech «Stack» versions, «Dev environment and checks», «Environment variables»; first `docs/guide/` articles), `/journal`, `/commit` with `build:`.
