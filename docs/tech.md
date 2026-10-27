# Tech

Updated 27.10.2026

## Contents

- [Stack](#stack)
- [Dev environment and checks](#dev-environment-and-checks)
- [Environment variables](#environment-variables)
- [Techniques](#techniques)

## Stack

Versions are pinned in the manifests and lock files: `backend/pyproject.toml` and `backend/uv.lock`,
`frontend/package.json` and `frontend/pnpm-lock.yaml`, and the image tags in `docker-compose.yml` and
`docker/backend.Dockerfile`.

| Component | Version | Why |
|---|---|---|
| Python + FastAPI | Python 3.12 (`>=3.12,<3.13`), FastAPI `>=0.161,<0.162` | Backend; typed, async, OpenAPI out of the box — [ADR 0001](adr/0001-fastapi-backend.md) |
| uv `0.9.3` (pinned in `docker/backend.Dockerfile`; the host `uv --version` is also 0.9.3) | — | Python packages and environments |
| uvicorn | `>=0.54,<0.55` | Serves the app in `just dev` (reload, port 8000) |
| pydantic-settings | `>=2.16,<3` | Typed `Settings` read from the environment (`backend/app/platform/settings.py`) |
| pytest | `>=9.1,<10` | Python tests (`just test`, `just test-db`) |
| pytest-asyncio | `>=1.4,<2` | Async tests; `asyncio_mode = "auto"` in `backend/pyproject.toml` |
| httpx | `>=0.28,<0.29` | In-process HTTP client of the integration tests (`ASGITransport`) |
| ruff | 0.17 | Python lint and format |
| pyright (strict) | 1.1 | Python type checking |
| SQLAlchemy `>=2.1,<2.2` + Alembic `>=1.20,<1.21` | — | Database access and migrations — [ADR 0001](adr/0001-fastapi-backend.md) |
| psycopg 3 `>=3.3,<3.4` (`psycopg[binary]`) | — | PostgreSQL driver of the async app and Alembic — [ADR 0006](adr/0006-postgresql-driver-psycopg-3-for-the.md) |
| argon2-cffi `>=25,<26` (locked `25.1.0`) | — | Password hashing with Argon2id (`backend/app/platform/passwords.py`) — [ADR 0013](adr/0013-new-dependencies-argon2-cffi-for-password.md) |
| aiosmtplib `>=5,<6` (locked `5.1.3`) | — | Async SMTP client of service emails, with a timeout (`backend/app/platform/mail.py`) — [ADR 0013](adr/0013-new-dependencies-argon2-cffi-for-password.md) |
| React `19.3.1` (`react`, `react-dom`), `@types/react` `19.3.0`, `@types/react-dom` `19.3.0` | — | SPA UI — [ADR 0002](adr/0002-react-spa.md) |
| react-router `7.18.4` (declarative mode) | — | SPA routes, `BrowserRouter` in `frontend/src/App.tsx` — [ADR 0015](adr/0015-spa-routing-with-react-router-7.md) |
| TypeScript `6.0.3` | — | Types, `tsc --noEmit`; pinned below the latest major: typescript-eslint `8.72.0` requires `<6.1.0` |
| Vite `8.3.5`, `@vitejs/plugin-react` `6.1.2` | — | Dev server and build of the SPA, `/api` proxy (`frontend/vite.config.ts`) — [ADR 0002](adr/0002-react-spa.md) |
| `@types/node` `26.6.5` | — | Node types of `frontend/vite.config.ts` |
| Node.js 24 (`node:24` image) | — | Runs the Vite dev server in `just dev` (`docker-compose.yml`) |
| pnpm `12.15.0` (`packageManager` in `frontend/package.json`) | — | Node packages, lockfile `frontend/pnpm-lock.yaml` — [ADR 0002](adr/0002-react-spa.md) |
| `openapi-typescript` `7.13.0` | — | Types of the API client, generated from the backend schema — [ADR 0005](adr/0005-frontend-api-client-types-from-openapi.md) |
| `openapi-fetch` `0.17.0` | — | Typed calls through the client (`frontend/src/api/client.ts`) — [ADR 0005](adr/0005-frontend-api-client-types-from-openapi.md) |
| `@tanstack/react-query` `5.104.5` | — | Server data and its cache (`frontend/src/api/queryClient.ts`) — [ADR 0005](adr/0005-frontend-api-client-types-from-openapi.md) |
| Vitest `5.0.5`, jsdom `30.1.3`, `@testing-library/react` `16.3.3`, `@testing-library/jest-dom` `7.0.1` | — | Frontend unit tests (`just test`) — [ADR 0002](adr/0002-react-spa.md) |
| ESLint `9.39.5` (`@eslint/js`, `typescript-eslint` `8.72.0`, `eslint-plugin-react` `7.37.5`, `eslint-plugin-react-hooks` `7.1.1`, `globals` `17.13.0`) | — | Frontend lint (`just check`); pinned below the latest major: `eslint-plugin-react` `7.37.5` crashes on ESLint 10 — [ADR 0002](adr/0002-react-spa.md) |
| Prettier `3.9.10` | — | Frontend format (`frontend/.prettierrc.json`) — [ADR 0002](adr/0002-react-spa.md) |
| PostgreSQL 18 (`postgres:18` image in `docker-compose.yml`) | — | Database — [ADR 0003](adr/0003-postgresql.md) |
| Mailpit `v1.29` (`axllent/mailpit` image in `docker-compose.yml`) | — | Dev mail catcher: receives the service emails of the dev stack, web UI on port 8025 — [ADR 0013](adr/0013-new-dependencies-argon2-cffi-for-password.md) |
| just | 1.59 | Command entry point (works on Windows) |
| prek | 0.5 | Git hooks (pre-commit compatible) |
| OpenSpec | 1.14.3 | Requirements and change deltas |

## Dev environment and checks

Requires: git, uv, just, prek, node with pnpm, Docker, openspec (`npm install -g @fission-ai/openspec`).

| Command | What it does |
|---|---|
| `just setup` | Installs the tooling and the git hooks |
| `just dev` | Starts the dev stack in Docker: database, Mailpit mail catcher, backend with reload (port 8000), SPA dev server (port 5173); Ctrl+C stops it |
| `just db` | Starts the database only, detached, and waits until it is healthy |
| `just check` | Read-only: every check to the end; fails on warnings. Harness: `ruff check` and `ruff format --check`, pyright, doc links and facts, OpenSpec validation, the hygiene hooks. Backend (when `backend/pyproject.toml` exists): `ruff check`, `ruff format --check`, pyright. Frontend (when `frontend/package.json` exists): ESLint, tsc, Prettier check (`format:check`), and `frontend-api-client` (the committed API client is fresh) |
| `just format` | Autofixes formatting and lint |
| `just test` | Unit tests: backend (`pytest app`) and frontend (Vitest) |
| `just test-db` | Database tests in `backend/tests/integration/`; starts the database container when needed |
| `just test-all` | Unit and database tests |
| `just api-client` | Regenerates the SPA's API client from the backend's OpenAPI schema |

Frontend unit tests are not part of `just check`; `just check` stays static.

In the dev stack the service emails (registration confirmation, invitations, password reset) go to the Mailpit
container; open its web UI at http://localhost:8025 to read them. Mailpit's SMTP port (1025) is reachable only inside the
compose network, so the mail flow works through `just dev`, not through a backend started on the host.

The backend container runs `uv sync --frozen --no-install-project` before the migrations and the server start. The
`backend-venv` volume is filled from the image only once, so without this step a dependency added to
`backend/pyproject.toml` would not reach the container until the volume is removed.

Git hooks (prek, `.pre-commit-config.yaml`; `just setup` installs them): the builtin file hygiene hooks
(large files, YAML, TOML, merge conflicts, end of file and trailing whitespace; the last two skip the generated
migrations and API client); ruff check and ruff format and pyright for the harness Python in `scripts/` and `.claude/`; the doc links
and doc facts checks; the journal guard; the backend ruff check, ruff format and pyright hooks; the frontend ESLint (with
`--max-warnings 0`), Prettier and tsc hooks; and a Conventional Commits check of the commit message.

## Environment variables

Secrets live only in `.env` (gitignored); `.env.example` is the template.

| Name | Meaning | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL URL of the dev database, read by `Settings` (`backend/app/platform/settings.py`), required; the `backend` service of `docker-compose.yml` sets its own value, with the host `db` | see `.env.example` |
| `TEST_DATABASE_URL` | PostgreSQL URL of the test database; read by `TestDatabaseSettings` in `backend/tests/database_settings.py`, which `backend/tests/integration/conftest.py` instantiates; not by `Settings` | see `.env.example` |
| `POSTGRES_USER` | User of the Docker database; `docker-compose.yml` also names the database after it | `vibecoding` in `.env.example` |
| `POSTGRES_PASSWORD` | Password of the Docker database | set in `.env` |
| `POSTGRES_PORT` | Host port of the PostgreSQL container (`docker-compose.yml`); when it changes, change the port in `DATABASE_URL` and `TEST_DATABASE_URL` too | `5432` |
| `VITE_PROXY_TARGET` | Address the Vite dev server proxies `/api` to (`frontend/vite.config.ts`); `docker-compose.yml` sets `http://backend:8000` | `http://localhost:8000` |
| `CHOKIDAR_USEPOLLING` | Turns on polling of file changes in the Vite dev server (`server.watch.usePolling` in `frontend/vite.config.ts`); `docker-compose.yml` sets `true` for the `frontend` service, because file events do not cross the Windows bind mount | unset: no polling |
| `WATCHFILES_FORCE_POLLING` | Makes the reload watcher of uvicorn (watchfiles) poll for file changes; `docker-compose.yml` sets `true` for the `backend` service, for the same reason. The backend code does not read it | unset: no polling |
| `APP_BASE_URL` | Base URL of the SPA: the origin of the links in emails, and the only `Origin` that state-changing requests may carry (`backend/app/platform/origin.py`); required. `docker-compose.yml` sets `http://localhost:5173` for the `backend` service | required |
| `MAIL_FROM` | Sender address of the service emails; required. `docker-compose.yml` passes it to the `backend` service from `.env` | required |
| `SMTP_HOST` | SMTP server of the service emails (`backend/app/platform/mail.py`); required. `docker-compose.yml` sets `mailpit` for the `backend` service | required |
| `SMTP_PORT` | SMTP port of the service emails | `1025` |
| `SMTP_USERNAME` | SMTP login; unset: no login | unset |
| `SMTP_PASSWORD` | SMTP password, used with `SMTP_USERNAME`; keep it in `.env` | unset |
| `SMTP_STARTTLS` | Upgrades the SMTP connection with STARTTLS | `false` |
| `SESSION_COOKIE_SECURE` | `Secure` flag of the session cookie `vc_session` (`backend/app/modules/auth/dependencies.py`); `false` over http in dev, `true` behind https | `false` |
| `SESSION_LIFETIME_DAYS` | Lifetime of a session after sign-in, in days | `14` |
| `CONFIRMATION_LINK_HOURS` | Lifetime of the email confirmation link, in hours | `24` |
| `PASSWORD_RESET_LINK_MINUTES` | Lifetime of the password reset link, in minutes | `60` |
| `INVITATION_LIFETIME_DAYS` | Lifetime of an invitation, in days | `7` |
| `SIGN_IN_MAX_FAILURES` | Failed sign-ins for one email that lock sign-in for that email | `5` |
| `SIGN_IN_FAILURE_WINDOW_MINUTES` | Window in which the failed sign-ins are counted, in minutes | `15` |
| `SIGN_IN_LOCK_MINUTES` | How long sign-in for that email stays locked, in minutes | `15` |

The defaults of the lifetimes and of the sign-in lock are set in [ADR 0014](adr/0014-defaults-invitation-7-days-email-confirmation.md).

## Techniques

- **Selector event loop on Windows.** psycopg's async mode cannot run on the Windows default Proactor loop.
  `backend/migrations/env.py` and `backend/tests/integration/conftest.py` use the selector loop — [ADR 0006](adr/0006-postgresql-driver-psycopg-3-for-the.md).
- **LF in every working copy.** `.gitattributes` sets `* text=auto eol=lf`, so files are checked out with LF on Windows
  too — [ADR 0020](adr/0020-add-gitattributes-with-text-auto-eol.md).
- **Cyrillic letters in ruff.** `allowed-confusables` in `backend/pyproject.toml` (`[tool.ruff.lint]`) lists the Cyrillic
  letters, so Russian UI texts and spec quotes pass the look-alike check without per-line `noqa` —
  [ADR 0017](adr/0017-ruff-allows-cyrillic-confusable-letters-allowed.md).
