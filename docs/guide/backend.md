# Backend

Updated 23.10.2026

**Code:** `backend/app/main.py`, `backend/app/openapi.py`, `backend/app/platform/`, `backend/app/modules/`,
`backend/migrations/`, `backend/alembic.ini`, `backend/tests/integration/`, `backend/pyproject.toml`,
`docker/backend.Dockerfile`.

**Requirements:** none. Task 0.1 is a technical change without specs ([ADR 0004](../adr/0004-task-0-1-runs-as-a.md)).

**Design:** [Components and processes](../architecture.md#components-and-processes),
[Repository structure](../architecture.md#repository-structure), [Layers](../architecture.md#layers),
[Data model](../architecture.md#data-model), [Stack](../tech.md#stack).

**Related:** [Frontend](frontend.md).

## App entry

`create_app(settings: Settings | None = None) -> FastAPI` in `backend/app/main.py` builds the app:

- configures logging at INFO level;
- takes the settings the caller passes, or reads them from the environment through `load_settings()`;
  a missing required value fails at startup;
- creates one `Database` for this app from `database_url`; the engine is created on first use, not at import;
- stores the `Database` in `app.state.database`; the app's lifespan disposes the connection pool on shutdown;
- titles the app `VibeCoding` and includes the module routers.

In `just dev` the `backend` service of `docker-compose.yml` runs `alembic upgrade head`, then
`uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000`. Uvicorn calls the factory
itself, so the settings come from the environment.

## OpenAPI export

`backend/app/openapi.py` prints the schema of the app as JSON to stdout:

```
uv run --directory backend python -m app.openapi
```

The schema does not depend on the database, so the module builds the app with a placeholder URL
(`SCHEMA_ONLY_URL`); no connection is opened. `just api-client` runs `scripts/api_client.py generate`,
which writes the schema to `frontend/src/api/openapi.json` and generates the client types into
`frontend/src/api/generated/schema.ts`.
`backend/app/test_openapi.py` checks that the schema lists `/api/v1/health`.

## Modules layout

- Each business module is a package `backend/app/modules/<module>/`; `backend/app/modules/__init__.py` is empty.
- A module's `router.py` is its HTTP entry. Its `repository.py` builds the repository from the database session.
- The session reaches a module through the FastAPI dependency `get_database_session` in `backend/app/platform/db.py`.
  Routers never touch the session.
- Platform code (settings, database, logging, clock) lives in `backend/app/platform/`; see
  [Platform layer](#platform-layer).
- Unit tests sit next to the code as `test_*.py` in `backend/app/`; `just test` runs them.

The layers and their rules are in [Layers](../architecture.md#layers).

## Platform layer

`backend/app/platform/` holds the code every module shares. Modules import it; it imports no module.

### Settings

- `backend/app/platform/settings.py` defines `Settings`, a pydantic-settings class. It has one field,
  `database_url`, read from the environment variable `DATABASE_URL`. The field is required.
- `Settings` also reads `.env` at the repository root (`REPO_ENV_FILE`). Other keys in `.env`, such as
  `POSTGRES_USER`, are ignored (`extra="ignore"`).
- A missing `database_url` raises `ValidationError` when `Settings` is built, so the app fails at startup.
- `Settings` is the only place in the app that reads the environment. `main.py` calls it through
  `load_settings()`; `create_app(settings)` takes an explicit `Settings` when the caller passes one (the
  tests and the OpenAPI export do). `backend/migrations/env.py` also reads the URL through `load_settings()`.
- The integration tests are the exception: `backend/tests/integration/conftest.py` reads `TEST_DATABASE_URL`
  through its own class, and the app's `Settings` gets that value as `database_url`.
- The variables are listed in [tech.md](../tech.md#environment-variables).

### Database

- `Base` in `backend/app/platform/db.py` is the declarative base of all models; its metadata has a naming
  convention for constraints. Alembic works from `Base.metadata`.
- `Database(url)` owns one engine. The engine is created on first access to `Database.engine`, never at import.
- `Database.session()` opens an `AsyncSession` from an `async_sessionmaker` with `expire_on_commit=False`.
  The session does not begin a transaction on its own; the service decides when a transaction starts.
- `Database.dispose()` closes the connection pool. It does nothing when the engine was never created.
- `get_database_session(request)` is the FastAPI dependency that gives a module its session. It reads
  `request.app.state.database`, yields one session, and closes it when the request ends.
- A module reaches the database only through that dependency, in its `repository.py`. A router never
  takes the session; see [Health module](#health-module).

### Clock

- `Clock` in `backend/app/platform/clock.py` is a protocol with one method, `now()`, which returns a
  timezone-aware UTC `datetime`.
- `SystemClock` is the real implementation: `datetime.now(UTC)`.
- No module uses the clock yet. The health module does not need the time.

### Logging

- `configure_logging(level=logging.INFO)` in `backend/app/platform/logging.py` sets the root logger's format to
  `%(asctime)s %(levelname)s %(name)s %(message)s`. `create_app()` calls it on each build; the second and later
  calls change nothing, because `logging.basicConfig` is a no-op once the root logger has handlers.
- A module logs through `get_logger(__name__)`, which returns `logging.getLogger(name)`.
- Do not log secrets, email text or personal data.

## Health module

`GET /api/v1/health` reports whether the service runs and whether the database answers. The module is
`backend/app/modules/health/`; it is the pattern for the modules that follow. The response shape is in
[Routes and API](../architecture.md#routes-and-api).

### Request flow

- `router.py` declares the route with `response_model=HealthStatus` and status 200. It takes a
  `HealthRepository` from `Depends(get_health_repository)` and calls `get_health_status(repository)`.
- `service.py` holds the use case `get_health_status`. It pings the repository and builds the `HealthStatus`.
- `repository.py` defines the `HealthRepository` protocol with `ping()`. `SqlHealthRepository` runs
  `SELECT 1` on the session. `get_health_repository` builds it from `get_database_session`.
- `schemas.py` defines `HealthStatus`: `status` is always `"ok"`; `database` is `"ok"` or `"unavailable"`.

### Ping timeout

- `PING_TIMEOUT_SECONDS = 2.0` in `service.py` bounds the ping. The service wraps `repository.ping()` in
  `asyncio.timeout`. The parameter `timeout_seconds` lets a test pass a shorter value.

### Unavailable instead of an error

- When the ping raises any exception, or times out, the service logs `database ping failed` with the traceback
  (`LOG.exception`) and reports `database: "unavailable"`.
- The route still answers HTTP 200 with `{"status": "ok", "database": "unavailable"}`. The endpoint never
  answers with an error because the database is down; the SPA shows the state.

### Tests

- `backend/app/modules/health/test_service.py` tests the service with a fake repository that returns, raises,
  or hangs; the hang case uses a timeout of 0.05 seconds.
- `backend/app/modules/health/test_router.py` tests the route without a database. `build_app()` creates the app
  with `create_app()` and a placeholder URL, then sets `app.dependency_overrides[get_health_repository]` to a
  generator that yields a fake repository. Tests override `get_health_repository` this way, not the session.
- `backend/tests/integration/test_health.py` tests the route against the real test database, and against an
  unreachable one (`127.0.0.1:1`) to check the `unavailable` answer.

## Migrations

- Alembic is configured by `backend/alembic.ini`; the scripts live in `backend/migrations/`.
- `backend/migrations/env.py` takes the database URL from `load_settings()`, not from `alembic.ini`, and runs
  through an async engine. Its `target_metadata` is the declarative `Base` of `backend/app/platform/db.py`.
- On Windows, psycopg's async mode needs the selector event loop, so `env.py` runs the migrations in an
  `asyncio.Runner` with `SelectorEventLoop`.
- New revisions use `backend/migrations/script.py.mako` as the template.
- The only revision, `0001` (`backend/migrations/versions/0001_baseline.py`), is empty: it creates and drops
  nothing. The first module that owns tables adds its models and its own revision.
- `backend/migrations/versions/` is excluded from ruff and pyright strict, because Alembic generates those files.

Apply the migrations to the dev database: `uv run --directory backend alembic upgrade head`
(`DATABASE_URL` comes from `.env`). The `backend` service does the same on every start.

## Integration tests

- `backend/tests/integration/` runs against the real PostgreSQL behind `TEST_DATABASE_URL`.
  `just test-db` runs them and starts the database container when needed; `just test-all` runs them with the unit tests.
- `backend/tests/integration/conftest.py` reads `TEST_DATABASE_URL` through its own small settings class.
  The app's `Settings` gets only the test URL as `database_url`, so the tests never read the dev `DATABASE_URL`.
- The database container creates the test database on its first start, from
  `docker/postgres/init/01-create-test-database.sql`.
- The `app` fixture builds the app with `create_app()` on the test database. The `client` fixture runs the app's
  lifespan and sends requests through `httpx.AsyncClient` with `ASGITransport`, so no network port opens.
- `pytest_asyncio_loop_factories` in `conftest.py` selects the selector event loop, because psycopg's async
  mode cannot run on the Windows default Proactor loop.
- Pytest settings are in `backend/pyproject.toml`: `asyncio_mode = "auto"` and `testpaths = ["app", "tests"]`.
- `backend/tests/integration/test_health.py` holds the integration tests of `GET /api/v1/health`.
