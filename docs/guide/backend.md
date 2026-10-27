# Backend

Updated 27.10.2026

**Code:** `backend/app/main.py`, `backend/app/openapi.py`, `backend/app/platform/`, `backend/app/modules/`,
`backend/migrations/`, `backend/alembic.ini`, `backend/tests/`, `backend/pyproject.toml`,
`docker/backend.Dockerfile`.

**Requirements:** the modules `accounts`, `auth` and `invitations` build FR-1 … FR-20 of task 0.2; they are described
in [Auth and accounts](auth.md). The health module has no requirement. The map of capabilities is in
[Requirements map](../domain.md#requirements-map).

**Design:** [Components and processes](../architecture.md#components-and-processes),
[Repository structure](../architecture.md#repository-structure), [Layers](../architecture.md#layers),
[Data model](../architecture.md#data-model), [Stack](../tech.md#stack).

**Related:** [Auth and accounts](auth.md), [Frontend](frontend.md).

## App entry

`create_app(settings: Settings | None = None) -> FastAPI` in `backend/app/main.py` builds the app:

- configures logging at INFO level;
- takes the settings the caller passes, or reads them from the environment through `load_settings()`;
  a missing required value fails at startup. The settings are listed in [Environment variables](../tech.md#environment-variables);
- creates one `Database` for this app from `database_url`; the engine is created on first use, not at import;
- stores the `Database` and the settings in `app.state`; `app.state.mail_sender` starts as `None`, and the
  `get_mail_sender` dependency creates the SMTP sender on first use;
- titles the app `VibeCoding`, registers the shared error handlers (`register_error_handlers`) and the domain error
  mapping of each module (`register_domain_errors`), adds the `OriginGuardMiddleware` with `APP_BASE_URL`, and
  includes the routers: health, accounts (its `router` and its `members_router`), auth and invitations;
- its lifespan disposes the connection pool on shutdown.

In `just dev` the `backend` service of `docker-compose.yml` runs `uv sync`, then `alembic upgrade head`, then
`uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000`. Uvicorn calls the factory
itself, so the settings come from the environment. The order and its reason are in
[Deploy](../architecture.md#deploy).

## OpenAPI export

`backend/app/openapi.py` prints the schema of the app as JSON to stdout:

```
uv run --directory backend python -m app.openapi
```

The schema does not depend on the database, so the module builds the app with placeholder settings
(`SCHEMA_ONLY_URL`, `SCHEMA_ONLY_BASE_URL`, `SCHEMA_ONLY_MAIL_FROM`, `SCHEMA_ONLY_SMTP_HOST`); no connection is opened.
`just api-client` runs `uv run --no-project python scripts/api_client.py . generate`,
which writes the schema to `frontend/src/api/openapi.json` and generates the client types into
`frontend/src/api/generated/schema.ts`.
`backend/app/test_openapi.py` checks that the schema lists `/api/v1/health`.

## Modules layout

- Each business module is a package `backend/app/modules/<module>/`; the package `__init__.py` files are empty, and
  `backend/app/modules/__init__.py` is empty too.
- The modules of task 0.2 are `accounts`, `auth` and `invitations`; `health` is the smallest one. They are described
  in [Auth and accounts](auth.md#modules-and-their-files).
- The layers are `router.py` → `service.py` → `domain.py` and `repository.py` → platform, as in
  [Layers](../architecture.md#layers). `models.py` holds the tables, `errors.py` the domain errors, `schemas.py` the
  request and response models, and `emails.py` the texts of service emails.
- A router holds no session and runs no query. Each router of accounts, auth and invitations takes a session-bound
  service class (`AccountsService`, `AuthService`, `InvitationsService`) from its dependency factory
  `get_<module>_service`, which takes the session from `get_database_session`. The `health` module keeps the
  repository shape: its router takes a `HealthRepository` from `Depends(get_health_repository)`
  ([Health module](#health-module)). `current_user` in `backend/app/modules/auth/dependencies.py` is a dependency,
  not a router, and takes the session itself.
- Domain errors are plain classes in `errors.py`. Each router declares `ERROR_MAPPING`, and `main.py` registers it;
  the answers are in [Errors over HTTP](auth.md#errors-over-http).
- Platform code (settings, database, logging, clock, mail, passwords and others) lives in `backend/app/platform/`; see
  [Platform layer](#platform-layer).
- Unit tests sit next to the code as `test_*.py` in `backend/app/`; `just test` runs them.

### Adding a module

1. Create `backend/app/modules/<module>/` with the files above. Add `models.py` only when the module owns tables.
   In `service.py`, add the use cases and a session-bound service class with its `get_<module>_service` factory; the
   router takes that class, never the session.
2. For tables, import the models in `backend/migrations/env.py` (the metadata is registered through that import),
   and add a revision in `backend/migrations/versions/`, from `backend/migrations/script.py.mako`.
3. Declare the domain errors and the module's `ERROR_MAPPING` in its `router.py`; in `main.py`, call
   `register_domain_errors` for the mapping and include the router.
4. Take the caller with the dependencies of `backend/app/modules/auth/dependencies.py` (`current_user`, `current_admin`), and follow the
   steps of [Adding an administrator-only route](auth.md#adding-an-administrator-only-route).
5. Test the route through HTTP in `backend/tests/integration/`, and update the route and data model in
   [Architecture](../architecture.md) and this guide.

## Platform layer

`backend/app/platform/` holds the code every module shares. Modules import it; it imports no module.

### Settings

- `backend/app/platform/settings.py` defines `Settings`, a pydantic-settings class. It holds the database URL, the
  links and mail settings, the session and link lifetimes, and the sign-in lock. The required fields raise
  `ValidationError` when `Settings` is built, so the app fails at startup. The variables and their defaults are in
  [Environment variables](../tech.md#environment-variables).
- `Settings` also reads `.env` at the repository root (`REPO_ENV_FILE`). Other keys in `.env`, such as
  `POSTGRES_USER`, are ignored (`extra="ignore"`).
- `Settings` is the only place in the app that reads the environment. `main.py` calls it through `load_settings()`;
  `create_app(settings)` takes an explicit `Settings` when the caller passes one. `get_settings` gives a router the
  settings the app was built with. `backend/migrations/env.py` also reads the URL through `load_settings()`.
- The integration tests are the exception for the database: `backend/tests/integration/conftest.py` reads
  `TEST_DATABASE_URL` through `TestDatabaseSettings` in `backend/tests/database_settings.py`, and `settings_for()` in `backend/tests/factories.py` builds the app's
  `Settings` with that URL and fixed mail values.

### Database

- `Base` in `backend/app/platform/db.py` is the declarative base of all models; its metadata has a naming
  convention for constraints. Alembic works from `Base.metadata`.
- `Database(url)` owns one engine. The engine is created on first access to `Database.engine`, never at import.
- `Database.session()` opens an `AsyncSession` from an `async_sessionmaker` with `expire_on_commit=False`.
  The session does not begin a transaction on its own; the service decides when a transaction starts.
- `Database.dispose()` closes the connection pool. It does nothing when the engine was never created.
- `get_database_session(request)` is the FastAPI dependency that gives a module its session. It reads
  `request.app.state.database`, yields one session, and closes it when the request ends.
- The session reaches the repositories through the service: a module's service class holds the session and
  delegates to the module-level use case function, which opens the transaction with `async with session.begin()`
  and passes the session to the repository functions. A repository function takes the `AsyncSession` as an
  argument and does not commit.

### Clock

- `Clock` in `backend/app/platform/clock.py` is a protocol with one method, `now()`, which returns a
  timezone-aware UTC `datetime`.
- `SystemClock` is the real implementation: `datetime.now(UTC)`.
- `get_clock` is the FastAPI dependency; it is cached, so one clock serves the process. The services of accounts,
  auth and invitations take the time from the clock they are given, and tests replace the dependency. The fakes are
  in [Emails and time in tests](auth.md#emails-and-time-in-tests).

### Other shared platform files

- `auth_context.py` (`AuthContext`, `Role`), `tokens.py`, `passwords.py`, `mail.py`, `origin.py`, `errors.py`,
  `validation.py` and `pagination.py` are described in [Modules and their files](auth.md#modules-and-their-files).

### Logging

- `configure_logging(level=logging.INFO)` in `backend/app/platform/logging.py` sets the root logger's format to
  `%(asctime)s %(levelname)s %(name)s %(message)s`. `create_app()` calls it on each build; the second and later
  calls change nothing, because `logging.basicConfig` is a no-op once the root logger has handlers.
- A module logs through `get_logger(__name__)`, which returns `logging.getLogger(name)`.
- Do not log secrets, email text or personal data.

## Health module

`GET /api/v1/health` reports whether the service runs and whether the database answers. The module is
`backend/app/modules/health/`. It has no domain or errors file. The response shape is in
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
  through an async engine. Its `target_metadata` is the declarative `Base` of `backend/app/platform/db.py`. It imports
  the models of each module, so their tables are on the metadata.
- On Windows, psycopg's async mode needs the selector event loop, so `env.py` runs the migrations in an
  `asyncio.Runner` with `SelectorEventLoop`.
- New revisions use `backend/migrations/script.py.mako` as the template.
- The revision `0001` (`backend/migrations/versions/0001_baseline.py`) is the empty baseline: it creates and drops
  nothing.
- The revision `0002` (`backend/migrations/versions/0002_accounts_auth_invitations.py`) creates the tables of the
  modules accounts, auth and invitations. Their columns and rules are in [Data model](../architecture.md#data-model).
- `backend/migrations/versions/` is excluded from ruff and pyright strict, because Alembic generates those files.

Apply the migrations to the dev database: `uv run --directory backend alembic upgrade head`
(`DATABASE_URL` comes from `.env`). The `backend` service does the same on every start.

## Integration tests

- `backend/tests/integration/` runs against the real PostgreSQL behind `TEST_DATABASE_URL`.
  `just test-db` runs them and starts the database container when needed; `just test-all` runs them with the unit tests.
- `backend/tests/integration/conftest.py` reads `TEST_DATABASE_URL` through `TestDatabaseSettings` in
  `backend/tests/database_settings.py`, a small settings class of its own.
  The app's `Settings` gets only the test URL as `database_url`, so the tests never read the dev `DATABASE_URL`.
- `test_database_url` empties every table of the test database before a test; `migrated_database_url` upgrades it
  to the head revision once per session.
- The database container creates the test database on its first start, from
  `docker/postgres/init/01-create-test-database.sql`.
- The `app` fixture builds the app with `create_app()` on the test database, and overrides `get_mail_sender` (the
  `mail` fake) and `get_clock` (the `clock` that the test moves). The `factories` fixture runs the app's lifespan.
  Requests go through `httpx.AsyncClient` with `ASGITransport`, so no network port opens. The fixtures and helpers
  are described in [Emails and time in tests](auth.md#emails-and-time-in-tests).
- `pytest_asyncio_loop_factories` in `conftest.py` selects the selector event loop, because psycopg's async
  mode cannot run on the Windows default Proactor loop.
- Pytest settings are in `backend/pyproject.toml`: `asyncio_mode = "auto"` and `testpaths = ["app", "tests"]`.
- The integration tests sit in `backend/tests/integration/` by requirement group: `test_registration.py`,
  `test_sign_in.py`, `test_password_reset.py`, `test_invitations_*.py`, `test_members.py`, `test_member_roles.py`,
  `test_access_boundary.py`, `test_platform_http.py`, `test_migrations.py` and `test_health.py`.
