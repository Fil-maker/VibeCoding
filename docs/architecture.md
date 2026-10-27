# Architecture

Updated 27.10.2026

**Status: tasks 0.1 and 0.2 are built.** Task 0.1 «Application skeleton» built the backend, the SPA and the database
container. Task 0.2 «Sign-in and organization» built registration, email confirmation, sign-in and sessions,
password reset, the members of an organization and invitations. The mailbox reader and the analysis engine
are not built yet.

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
| Sign-in and organization: registration, email confirmation, sign-in and sessions, password reset, members, invitations | ✅ | 0.2 |

## Components and processes

- **Backend** — a FastAPI application (Python): the HTTP API, the modules `accounts`, `auth`, `invitations`
  and `health`, the database access and the service emails.
- **SPA** — a React + TypeScript single-page app built with Vite; talks to the backend only through an
  API client generated from the backend's OpenAPI schema.
- **Database** — PostgreSQL, in Docker for development.
- **Service mail** — the backend sends three kinds of emails through SMTP: registration confirmation, password
  reset and invitation. The app never reads a mailbox. In development the emails go to the Mailpit container
  ([Deploy](#deploy)).

TBD: the mailbox reader and the analysis engine (see [ideas.md](ideas.md#analysis-engine)).

## Repository structure

The tree below is the repository as it is now. The module folder is the pattern for the modules that follow.

```
backend/                 FastAPI application (own pyproject.toml, uv.lock)
  alembic.ini            Alembic config; the URL comes from the settings
  app/
    main.py              create_app(): app factory, error handlers, Origin guard, routers, lifespan
    openapi.py           prints the OpenAPI schema as JSON
    test_openapi.py      unit test of the schema export
    platform/            shared code of all modules
      settings.py        Settings: the app's only reader of the environment and of .env
      db.py              Database, Base, get_database_session
      logging.py         configure_logging(), get_logger()
      clock.py           Clock protocol, SystemClock, get_clock (tests replace it)
      errors.py          error shape, HttpError, NotFound, register_domain_errors, register_error_handlers
      origin.py          OriginGuardMiddleware: Origin check of state-changing /api/ requests
      auth_context.py    AuthContext (user id, organization id, role) and Role
      pagination.py      Page[T]: items and next_cursor; the limits
      validation.py      RequestModel (unknown fields refused) and the Russian-worded field types
      passwords.py       Argon2id hashing and verification, in a worker thread
      tokens.py          random one-time tokens and their SHA-256 hashes
      mail.py            MailSender protocol, SmtpMailSender, FakeMailSender, get_mail_sender, build_link
      test_mail.py       unit tests of mail
      test_passwords.py  unit tests of passwords
      test_settings.py   unit tests of settings
    modules/<module>/    one folder per module: health, accounts, auth, invitations
      accounts/          organizations and their users: registration, email confirmation, members;
                         router.py, service.py, schemas.py, domain.py, repository.py, models.py, errors.py, emails.py
                         (router.py holds two routers: /api/v1/auth for registration, /api/v1/members)
      auth/              sign-in, the sign-in lock, sessions, password reset; the same files as accounts,
                         plus dependencies.py (current_user, current_admin)
      invitations/       invite, list, resend, revoke, preview, accept; the same files as accounts
      health/            GET /api/v1/health; router.py, service.py, schemas.py, repository.py
    modules/health/test_*.py  unit tests of the health module (test_router.py, test_service.py)
  migrations/            Alembic: env.py, script.py.mako, versions/ (0001_baseline.py, 0002_accounts_auth_invitations.py)
  tests/                 test support of the integration tests
    integration/         database tests through the HTTP API, one file per group of requirements
    factories.py         organizations, users, sessions and invitations, built through the public API
    members_api.py       helpers shared by the members and access-boundary tests
    invitations_api.py   helpers shared by the invitation tests
    settable_clock.py    a clock that the tests move by hand
    alembic_runner.py    runs Alembic against the test database (migration round trip)
    database_settings.py TEST_DATABASE_URL of the tests
frontend/                React + TypeScript SPA (Vite, pnpm; own package.json, pnpm-lock.yaml)
  index.html             page shell: #root and the module script of main.tsx
  vite.config.ts         React plugin, /api proxy, Vitest settings
  eslint.config.js       ESLint, typed rules; .prettierrc.json, .prettierignore, tsconfig.json
  src/
    main.tsx             entry: mounts App into #root, loads the design tokens
    App.tsx              root component: QueryClientProvider, BrowserRouter, AuthProvider and the routes
    App.*.test.tsx       page tests, one file per area (sign-in, registration, members, guards, …)
    api/
      client.ts          apiClient: openapi-fetch typed by the generated schema
      queryClient.ts     createQueryClient(): TanStack Query client
      request.ts         unwrap(): the client's result as data or an ApiError (code, status, fields)
      openapi.json       OpenAPI schema from the backend (generated)
      generated/         schema.ts, types generated from openapi.json; never edited by hand
    messages.ts          Russian UI texts that the server does not send
    urlToken.ts          readFragmentToken(): the one-time token from the URL fragment #token=
    components/          Panel, FormField, ErrorAlert, NotFoundPage, formData.ts, ui.module.css
    features/
      auth/              AuthProvider (who is signed in), guards (RequireUser, RequireAdmin, RequireGuest),
                         sign-in, registration, email confirmation, forgot and reset password pages
      home/              StartPage: the signed-in user, the members link for an administrator, sign-out
      invitations/       InvitationPage: the page of an invitation link
      members/           MembersPage, MembersSection, InvitationsSection
      health/            HealthStatus (page), useHealth (query), styles and tests
    styles/tokens.css    design tokens: colors, spacing, sizes, fonts
    test/                appHarness.tsx (renders App with fetch stubbed), membersFixtures.tsx,
                         setup.ts (Vitest setup: Testing Library cleanup, unstubbed globals)
docker/                  backend.Dockerfile (dev image); postgres/init/ runs once, on the first start of the database
docker-compose.yml       development stack: database, mail catcher, backend, SPA; see Deploy
.gitattributes           '* text=auto eol=lf': every working copy uses LF
docs/                    product docs
openspec/                requirements and changes
scripts/                 doc checkers, the check runner (run_checks.py), the API client script (api_client.py)
.claude/                 the agent harness
```

## Layers

Built so far: the platform and the modules health, accounts, auth and invitations. The layer rules are in
`.claude/rules/server-architecture.md`.

Dependencies point down: router → service → domain and repository → platform.

| Layer | File | What it does |
|---|---|---|
| Router | `router.py` | Parses the request into `schemas.py` models, takes the caller from `AuthContext`, calls one method of the module's service, which FastAPI injects; maps the module's domain errors to HTTP. A router never receives the database session |
| Service | `service.py` | The use cases as module-level functions that open the transaction (`session.begin()`), call domain logic and repositories, and enforce the access rules; a session-bound class (`AccountsService`, `AuthService`, `InvitationsService`) delegates to them; the factory `get_<module>_service` builds the class from `get_database_session` |
| Domain | `domain.py` | Pure functions: the sign-in lock rule, the invitation status, the page cursors |
| Repository | `repository.py` | Named queries; no commits, no business decisions |
| Models | `models.py` | SQLAlchemy tables of the module ([Data model](#data-model)) |
| Platform | `backend/app/platform/` | settings, db, errors, clock, mail, passwords, tokens, validation, pagination, the Origin guard, the auth context |

The health module keeps its first shape: `router.py` takes a `HealthRepository` from `get_health_repository`,
the repository is built from the session, and tests replace the factory through `dependency_overrides`. The
health module has no domain or errors file.

**Domain errors.** Each module's `errors.py` defines plain exceptions without an HTTP status (for example
`EmailTaken`, `InvalidLink`, `MemberNotFound`). Each router declares `ERROR_MAPPING: dict[type[Exception], HttpError]`,
where `HttpError(status_code, code, message)` is defined in `backend/app/platform/errors.py`. `main.py` passes each mapping
to `register_domain_errors`. A domain error may be answered by another module's mapping: the invitations
service raises `EmailTaken` from accounts, and the accounts mapping answers it. `register_error_handlers` adds
the handlers every route shares: `NotFound` (404 `not_found`), request validation (422) and framework HTTP
errors. The shape of an answer is in [Routes and API](#routes-and-api).

**Auth context.** `current_user` in `backend/app/modules/auth/dependencies.py` reads the `vc_session` cookie, resolves a live session
and returns an `AuthContext` (user id, organization id, role). It refuses a missing or dead session, and a user
who is not confirmed or not active. The role and the active flag are read from the database on every request,
so a role change or a deactivation applies to the next request. `current_admin` wraps `current_user` and raises
`NotFound` for an employee, so the administrator routes look absent to them. The routers of accounts, auth and
invitations take `AuthContext` from these two dependencies and hand it to their service, which scopes every
query by its `organization_id`. `current_user` is the one dependency that takes the session itself (through
`get_database_session`), because it resolves the caller before any router runs. The sign-out route also reads
the cookie, to end that session.

**Services and sessions.** The routers of accounts, auth and invitations never touch the database session. Each
module's `service.py` has the use cases as module-level functions and a session-bound class (`AccountsService`,
`AuthService`, `InvitationsService`) that delegates to them. The dependency factory `get_<module>_service` builds
that class from `get_database_session`, and a handler declares the service as a dependency, for example
`service: Annotated[AccountsService, Depends(get_accounts_service)]`.

**Emails after the commit.** The services send a service email only after the transaction has committed:
the registration confirmation, the password reset and the invitation (on invite and on resend). A failed send
is logged and never raised:

- registration answers `email_sent: false` and the account stays unconfirmed;
- an invitation's outcome is written in a second transaction: `delivery` becomes `sent` or `failed`, so a
  failed invitation shows as `not_sent` and can be resent;
- a password reset answers 202 whether or not the mail went out.

The mail sender is the `get_mail_sender` dependency, created on first use; the tests replace it with the fake.

**Origin guard.** `OriginGuardMiddleware` in `backend/app/platform/origin.py` runs before the routes. It refuses a
state-changing request (POST, PUT, PATCH, DELETE) to `/api/` whose `Origin` header is missing or differs from
the origin of `APP_BASE_URL` ([Security](#security)).

**Between modules.** A module uses another module through that module's `service.py` or `repository.py`. For example
`backend/app/modules/auth/dependencies.py` uses the auth service; `backend/app/modules/accounts/service.py` uses the auth service to end sessions and
issue confirmation tokens; `backend/app/modules/invitations/service.py` uses the accounts repository and service and the auth
repository and service. Three more public imports cross module lines: the accounts and invitations routers take
`current_admin` and `set_session_cookie` from `backend/app/modules/auth/dependencies.py`; the invitations router
takes the `Me` schema from `backend/app/modules/auth/schemas.py`; and the invitations service raises `EmailTaken` from
`backend/app/modules/accounts/errors.py`. No module imports another module's models or private names.

Details of the platform code and the health flow are in [Backend](guide/backend.md).

## Data model

The migration `0002` (`backend/migrations/versions/0002_accounts_auth_invitations.py`) creates six tables. The
baseline `0001` stays empty. The models are in each module's `models.py`; the declarative `Base` in
`backend/app/platform/db.py` is the metadata Alembic works from.

Conventions of the tables:

- ids are UUID; timestamps are `timestamptz`;
- child rows are deleted with their parent (`ON DELETE CASCADE`);
- only SHA-256 hashes of session, link and invitation tokens are stored, never the tokens;
- passwords are stored as Argon2id hashes.

| Table | Key columns | Relations and indexes |
|---|---|---|
| `organizations` | `id`, `name` (up to 200), `created_at` | The root: deleting an organization deletes all its rows |
| `users` | `id`, `organization_id`, `email` (up to 254, unique in the installation, stored normalized), `name` (up to 200), `password_hash`, `role` (`administrator` or `employee`), `is_active`, `confirmed_at` (empty until the email is confirmed), `created_at` | `organization_id` → `organizations` (cascade); index on `organization_id`. An unconfirmed registration of an email is replaced by deleting its organization |
| `sessions` | `id`, `organization_id`, `user_id`, `token_hash` (unique), `created_at`, `expires_at` | `user_id` → `users` and `organization_id` → `organizations` (cascade); indexes on both |
| `user_tokens` | `id`, `organization_id`, `user_id`, `purpose` (`confirm_email` or `reset_password`), `token_hash` (unique), `created_at`, `expires_at` | `user_id` → `users` and `organization_id` → `organizations` (cascade); indexes on both. A new token replaces the user's earlier tokens of the same purpose; a link is consumed by one `DELETE … RETURNING`, so it works once |
| `invitations` | `id`, `organization_id`, `email` (up to 254), `invited_by_user_id`, `token_hash` (unique), `delivery` (`pending`, `sent` or `failed`), `sent_at`, `expires_at`, `accepted_at`, `accepted_user_id`, `revoked_at`, `created_at` | `organization_id` → `organizations`, `invited_by_user_id` → `users`, `accepted_user_id` → `users` (empty until accepted); all cascade; index on `(organization_id, created_at)`. The invitation's status is derived, not stored (below) |
| `sign_in_failures` | `id`, `email` (up to 254), `occurred_at` | No organization: the email may be unknown. Index on `(email, occurred_at)` |

The invitation status shown to the administrator is derived from the row: `accepted` when `accepted_at` is set,
`revoked` when `revoked_at` is set, `expired` when `expires_at` has passed; otherwise `sent` when `delivery` is
`sent`, and `not_sent` in the other cases.

## Routes and API

The OpenAPI schema generated by FastAPI is the contract. `backend/app/openapi.py` prints it; `just api-client`
writes it to `frontend/src/api/openapi.json` and regenerates the SPA's client in `frontend/src/api/generated/`.

Who may call a route: **anyone** — no session needed; **signed in** — a live session of a confirmed, active user;
**administrator** — a signed-in administrator of the caller's organization. An employee calling an administrator
route gets 404 `not_found`, as for a missing page. A signed-out caller of a signed-in or administrator route
gets 401 `not_signed_in`. The routes below are all under `/api/v1`.

| Method and path | Who may call | Success | Domain errors (code, status) |
|---|---|---|---|
| `GET /api/v1/health` | anyone | 200, `HealthStatus` | none |
| `POST /api/v1/auth/registrations` | anyone | 201, `RegistrationResult` | `email_taken` 409 |
| `POST /api/v1/auth/email-confirmations` | anyone, with the link token | 200, `Me`; sets `vc_session` | `invalid_link` 400 |
| `POST /api/v1/auth/sessions` | anyone | 200, `Me`; sets `vc_session` | `invalid_credentials` 401, `email_not_confirmed` 403, `account_disabled` 403, `sign_in_locked` 429 |
| `DELETE /api/v1/auth/sessions/current` | signed in | 204; deletes `vc_session` | `not_signed_in` 401 |
| `GET /api/v1/auth/me` | signed in | 200, `Me` | `not_signed_in` 401 |
| `POST /api/v1/auth/password-resets` | anyone | 202, no body | none; the same answer for every email |
| `POST /api/v1/auth/password-resets/complete` | anyone, with the link token | 204 | `invalid_link` 400 |
| `GET /api/v1/members` | administrator | 200, `Page[Member]` | `invalid_cursor` 400 |
| `POST /api/v1/members/{member_id}/deactivate` | administrator | 200, `Member` | `not_found` 404, `cannot_deactivate_self` 409, `last_administrator` 409 |
| `POST /api/v1/members/{member_id}/reactivate` | administrator | 200, `Member` | `not_found` 404 |
| `PUT /api/v1/members/{member_id}/role` | administrator | 200, `Member` | `not_found` 404, `member_inactive` 409, `last_administrator` 409 |
| `GET /api/v1/invitations` | administrator | 200, `Page[Invitation]` | `invalid_cursor` 400 |
| `POST /api/v1/invitations` | administrator | 201, `Invitation` | `email_taken` 409, `invitation_exists` 409 |
| `POST /api/v1/invitations/preview` | anyone, with the link token | 200, `InvitationPreview` | `invalid_invitation` 400 |
| `POST /api/v1/invitations/accept` | anyone, with the link token | 200, `Me`; sets `vc_session` | `invalid_invitation` 400, `email_taken` 409 |
| `POST /api/v1/invitations/{invitation_id}/resend` | administrator | 200, `Invitation` | `not_found` 404, `invitation_not_open` 409 |
| `POST /api/v1/invitations/{invitation_id}/revoke` | administrator | 200, `Invitation`; an invitation that is not open is returned unchanged | `not_found` 404 |

Registration lives in the accounts router under `/api/v1/auth`, next to the auth routes. The members routes
are the administrator's member list and changes.

Every state-changing request also answers 403 `forbidden_origin` when its `Origin` is missing or foreign, and
a body with an unknown field, or an invalid one, answers 422 `validation_failed`.

Schemas of the responses: `Me` is `user_id`, `name`, `email`, `role`, `organization` (`id`, `name`); `Member` is
`id`, `name`, `email`, `role`, `is_active`; `Invitation` is `id`, `email`, `sent_at`, `expires_at`, `status`
(`sent`, `not_sent`, `accepted`, `revoked` or `expired`); `InvitationPreview` is `organization_name`, `email`;
`RegistrationResult` is `email`, `email_sent`. `role` is `administrator` or `employee`.

**Error shape.** A handled error answers `{"error": {"code": "…", "message": "…"}}`, where `message` is the Russian
text of the error. A validation error adds `fields`: `{"error": {"code": "validation_failed", "message": "Проверьте поля формы", "fields": {"<field>": "<Russian message>"}}}`.
A framework HTTP error other than 404 keeps FastAPI's `{"detail": …}` shape; a 404 answers `not_found`.

**Pagination.** The list routes take `limit` (default 50, from 1 to 100) and an opaque `cursor` (up to 200
characters). An answer is `{"items": [...], "next_cursor": "…" | null}`; `next_cursor` is `null` on the last
page. Members are ordered by name, then id; invitations are ordered newest first, then by id. A cursor that the
API did not issue answers 400 `invalid_cursor`.

**SPA routes.** The browser routes of `frontend/src/App.tsx` (`BrowserRouter`):

| Path | Page | Who sees it |
|---|---|---|
| `/register` | «Регистрация» | a signed-out visitor |
| `/sign-in` | «Вход» | a signed-out visitor |
| `/forgot-password` | «Восстановление пароля» | a signed-out visitor |
| `/confirm-email` | «Подтверждение email» | anyone, with the link |
| `/reset-password` | «Новый пароль» | anyone, with the link |
| `/invitation` | «Приглашение» | anyone, with the link |
| `/health` | «Состояние сервиса» (page heading) | anyone |
| `/` | «VibeCoding» (start page) | a signed-in user |
| `/members` | «Участники» | an administrator; an employee sees «Страница не найдена» |
| `*` | «Страница не найдена» | anyone |

A signed-out visitor who opens a signed-in page goes to `/sign-in?next=…` and returns after signing in. A
signed-in user who opens a guest page goes to `next` (a path of this site) or to `/`. The link tokens are read
from the URL fragment `#token=`. The invitation page sends its token twice: to `POST /api/v1/invitations/preview` when
it loads, and to `POST /api/v1/invitations/accept` when the person submits the form. The password reset form sends
its token in the body of `POST /api/v1/auth/password-resets/complete` on each submit.

## Deploy

Not deployed. Local development only. `docker-compose.yml` runs four services:

- `db` — PostgreSQL 18; the host port comes from `POSTGRES_PORT` ([Environment variables](tech.md#environment-variables)).
- `mailpit` — the dev mail catcher, the Mailpit image pinned to v1.29 in `docker-compose.yml`. SMTP listens on port 1025 inside the compose network
  and is not published to the host; the web UI is on host port 8025.
- `backend` — built from `docker/backend.Dockerfile` (Python 3.12 with uv). Its command runs `uv sync --frozen
  --no-install-project`, then `alembic upgrade head`, then uvicorn with `--reload` on port 8000. The `uv sync`
  comes first because the named venv volume is filled from the image only once, so a dependency added later
  would never reach the container without it. The image bakes the locked dependencies.
- `frontend` — the `node:24` image; runs the Vite dev server on port 5173.

The `backend` service sets these environment variables itself: `DATABASE_URL` (built from the Postgres
variables, pointing at the `db` service), `WATCHFILES_FORCE_POLLING`, `SMTP_HOST=mailpit`,
`APP_BASE_URL=http://localhost:5173` (the links in the emails point at the SPA on the host) and `MAIL_FROM`,
taken from `.env`. The repo-root `.env` is not mounted into the container, so the other settings take their
defaults there. The list of all variables is in [Environment variables](tech.md#environment-variables).

`just dev` starts all the services; `just db` starts only the database. The database volume is initialized once:
`docker/postgres/init/01-create-test-database.sql` creates the test database `vibecoding_test` when the volume
is first created, and the integration tests use it.

## Security

What is built:

- **Passwords.** Argon2id hashes (argon2-cffi, default parameters), computed in a worker thread. A password is
  10 to 128 characters. When a sign-in succeeds with a hash whose parameters are out of date, the hash is
  recomputed. An unknown email is checked against a dummy hash, so the answer takes as long as for a known one.
  The dependency is recorded in [ADR 0013](adr/0013-new-dependencies-argon2-cffi-for-password.md).
- **Tokens.** Session cookies and link tokens are random URL-safe values of 32 bytes. Only their SHA-256 hashes
  are stored. A password-reset or confirmation link works once; an invitation link works until it is accepted,
  revoked, expired or replaced by a resend.
- **Links in the URL fragment.** The emailed links carry the token after `#token=`. The fragment is not sent to
  the server, so the token stays out of server logs and of the `Referer` header.
- **Sessions.** The browser holds a random token in the `vc_session` cookie: `HttpOnly`, `SameSite=Lax`, `Path=/`,
  with a lifetime of the session lifetime. `Secure` follows the setting `SESSION_COOKIE_SECURE`, which is off by
  default for local HTTP ([Environment variables](tech.md#environment-variables)). Sessions are rows of PostgreSQL
  ([ADR 0012](adr/0012-sessions-are-stored-server-side-in.md)); each request resolves the cookie. Signing out ends
  that browser's session only. Deactivating a member and completing a password reset delete all of the user's
  sessions at once.
- **Origin check.** A POST, PUT, PATCH or DELETE request to `/api/` must carry an `Origin` header equal to the
  origin of `APP_BASE_URL`. A request without the header, or with another origin, answers 403 `forbidden_origin`.
- **Sign-in lock.** Failed sign-ins are recorded per email, normalized, in `sign_in_failures`, including emails
  that are not registered. When 5 failures happen within 15 minutes, sign-in for that email is refused for 15
  minutes from the last of them, answering 429 `sign_in_locked`. A refused attempt is not recorded, so the lock
  does not extend itself. A successful sign-in and a completed password reset clear the failures. The numbers are
  defaults set by the settings `SIGN_IN_MAX_FAILURES`, `SIGN_IN_FAILURE_WINDOW_MINUTES` and `SIGN_IN_LOCK_MINUTES`
  ([ADR 0014](adr/0014-defaults-invitation-7-days-email-confirmation.md)).
- **No account probing.** A wrong password and an unknown email both answer `invalid_credentials`. The answer to a
  password-reset request is 202 whether or not the email is registered, and only a confirmed user gets the mail.
  A registration of a confirmed user's email answers `email_taken` 409, and a new registrant must confirm the
  email before they can sign in ([ADR 0009](adr/0009-the-registrant-s-email-is-confirmed.md)).
- **Organization filter.** Every query of the administrator's member and invitation routes filters by the
  `organization_id` of the caller's `AuthContext`, never by a value from the request. The only exceptions are
  the anonymous link lookups: the invitation behind a link is found by the token hash alone
  (`get_by_token_hash` in `backend/app/modules/invitations/repository.py`), and the user of an email is found
  across the installation (`find_by_email` in `backend/app/modules/accounts/repository.py`), because an email
  belongs to one user of the installation ([ADR 0008](adr/0008-one-email-belongs-to-one-user.md)). The request bodies refuse unknown fields, so `organization_id`
  cannot be sent. A record of another organization, or an administrator route for an employee, answers 404
  `not_found`, the same as a missing record.
- **Last administrator.** Deactivating or demoting an administrator locks the organization row (`SELECT … FOR
  UPDATE`) before counting the active administrators. The last active administrator cannot be deactivated or
  demoted; an administrator cannot deactivate their own account ([ADR 0010](adr/0010-in-this-task-the-administrator-lists.md),
  [ADR 0019](adr/0019-when-the-only-administrator-deactivates-themselves.md)).
- **One email, one organization.** An email belongs to one user in one organization across the installation
  ([ADR 0008](adr/0008-one-email-belongs-to-one-user.md)).

Not built yet: the mailbox reader, with its read-only access to mailboxes, and the consent gate that must pass
before email text goes to a third-party service. See [Components and processes](#components-and-processes).
