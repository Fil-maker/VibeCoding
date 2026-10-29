# Architecture

Updated 29.10.2026

**Status: tasks 0.1, 0.2, 1.1 and 1.2 are built.** Task 0.1 «Application skeleton» built the backend, the SPA and the database
container. Task 0.2 «Sign-in and organization» built registration, email confirmation, sign-in and sessions,
password reset, and an organization with its members and invitations. Task 1.1 «Personal accounts» removed the
organization layer: a registrant is an individual user and the root owner of their data ([ADR 0023](adr/0023-organizations-are-removed-anyone-can-register.md)).
Task 1.2 «Mailboxes and reply chains» built the mailbox reader (read-only IMAP, in the background) and the reply chains,
in the backend and the SPA. The analysis engine is not built yet.

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
| Sign-in: registration, email confirmation, sign-in and sessions, password reset | ✅ | 0.2 |
| Personal accounts: a registrant is an individual user; organizations, invitations, members, roles and deactivation are removed | ✅ | 1.1 |
| Mailboxes and reply chains: connecting mailboxes over read-only IMAP, reading them in the background, joining emails into reply chains, the reply-chain list and page | ✅ | 1.2 |

## Components and processes

- **Backend** — a FastAPI application (Python): the HTTP API, the modules `accounts`, `auth`, `health`, `mailboxes`
  and `correspondence`, the database access, the service emails and the mailbox reading loop.
- **Mailbox reader** — a background task of the backend, started in the FastAPI lifespan when `MAILBOX_READING_ENABLED`
  is `true`. Every `MAILBOX_READ_TICK_SECONDS` it looks for due mailboxes and reads each one once: a mailbox is due
  right after connecting, on «Обновить», and `MAILBOX_READ_INTERVAL_MINUTES` after its last read attempt. A read
  opens the Inbox and Sent folders over IMAP, read-only, and stores the emails of the last `MAILBOX_READ_DEPTH_DAYS`
  days. The mailboxes are claimed from the database one at a time, and the network calls run outside any transaction.
  A request never reads a mailbox: connecting only checks the sign-in, and «Обновить» only asks for a read at the next tick.
- **SPA** — a React + TypeScript single-page app built with Vite; talks to the backend only through an
  API client generated from the backend's OpenAPI schema.
- **Database** — PostgreSQL, in Docker for development.
- **Service mail** — the backend sends two kinds of emails through SMTP: registration confirmation and password
  reset. The mailbox reader is separate from it and only reads. In development the emails go to the Mailpit container
  ([Deploy](#deploy)).

TBD: the analysis engine (see [ideas.md](ideas.md#analysis-engine)).

## Repository structure

The tree below is the repository as it is now. The module folder is the pattern for the modules that follow.

```
backend/                 FastAPI application (own pyproject.toml, uv.lock)
  alembic.ini            Alembic config; the URL comes from the settings
  app/
    main.py              create_app(): app factory, error handlers, Origin guard, routers, lifespan (starts the mailbox reading loop)
    openapi.py           prints the OpenAPI schema as JSON
    test_openapi.py      unit test of the schema export
    platform/            shared code of all modules
      settings.py        Settings: the app's only reader of the environment and of .env
      db.py              Database, Base, get_database_session
      logging.py         configure_logging(), get_logger()
      clock.py           Clock protocol, SystemClock, get_clock (tests replace it)
      errors.py          error shape, HttpError, NotFound, register_domain_errors, register_error_handlers
      origin.py          OriginGuardMiddleware: Origin check of state-changing /api/ requests
      auth_context.py    AuthContext: the user id of the signed-in caller
      validation.py      RequestModel (unknown fields refused) and the Russian-worded field types
      passwords.py       Argon2id hashing and verification, in a worker thread
      tokens.py          random one-time tokens and their SHA-256 hashes
      mail.py            MailSender protocol, SmtpMailSender, FakeMailSender, get_mail_sender, build_link
      mail_reader.py     MailReader protocol, ImapMailReader (read-only IMAP), FakeMailReader, get_mail_reader
      imap_folders.py    IMAP LIST parsing, folder names in modified UTF-7, the choice of the Sent folder
      secret_box.py      SecretBox: Fernet encryption of the mailbox app passwords, get_secret_box
      pagination.py      Page[T] and the keyset cursor: encode_cursor, decode_cursor
      test_mail.py       unit tests of mail
      test_mail_reader.py unit tests of the mail reader and the fake
      test_passwords.py  unit tests of passwords
      test_secret_box.py unit tests of the secret box
      test_settings.py   unit tests of settings
    modules/<module>/    one folder per module: health, accounts, auth, mailboxes, correspondence
      accounts/          registration of a user and the users table; router.py (the registration route),
                         service.py, schemas.py, repository.py, models.py, errors.py, emails.py
      auth/              sign-in, the sign-in lock, sessions, email confirmation, password reset;
                         router.py, service.py, schemas.py, domain.py (the lock rule), repository.py, models.py,
                         errors.py, emails.py, dependencies.py (current_user)
      health/            GET /api/v1/health; router.py, service.py, schemas.py, repository.py
      mailboxes/         connecting, listing, refreshing and disconnecting mailboxes, and the background reading run;
                         router.py, service.py, schemas.py, domain.py (the reason of a failed read), repository.py,
                         models.py, errors.py
      correspondence/    emails stored once per user with their copies in folders, reply chains: joining, the list and
                         the page of a chain; router.py, service.py, schemas.py, domain.py (parsing, the email key,
                         the merge choice, HTML to text), repository.py, models.py, errors.py
    modules/health/test_*.py  unit tests of the health module (test_router.py, test_service.py)
  migrations/            Alembic: env.py, script.py.mako, versions/ (0001_baseline.py, 0002_accounts_auth_invitations.py,
                         0003_personal_accounts.py, 0004_mailboxes_and_reply_chains.py)
  tests/                 test support of the integration tests
    integration/         database tests through the HTTP API, one file per group of requirements
    factories.py         users built through the public API: unconfirmed and confirmed users, signed-in clients
    mail_factory.py      raw test emails built with the standard library, the way a mail server hands them over
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
    App.*.test.tsx       page tests, one file per area (sign-in, registration, password reset, guards, start page,
                         mailboxes, chains)
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
      auth/              AuthProvider (who is signed in), guards (RequireUser, RequireGuest),
                         sign-in, registration, email confirmation, forgot and reset password pages
      home/              StartPage: the signed-in user's name, links to the mailboxes and the chains, and sign-out
      health/            HealthStatus (page), useHealth (query), styles and tests
      mailboxes/         MailboxesPage: the connected mailboxes with their reading status, refresh and disconnect,
                         and the connect form
      correspondence/    ChainsPage (the list of reply chains, a page at a time), ChainPage (one chain, emails as plain
                         text), ChainPage.module.css, format.ts (dates, email counts, addresses)
    styles/tokens.css    design tokens: colors, spacing, sizes, fonts
    test/                appHarness.tsx (renders App with fetch stubbed),
                         setup.ts (Vitest setup: Testing Library cleanup, unstubbed globals)
docker/                  backend.Dockerfile (dev image); postgres/init/ runs once, on the first start of the database;
                         greenmail/demo/ holds the 40 prepared demo emails (.eml) and manifest.json, which say where each one goes
docker-compose.yml       development stack: database, mail catcher, demo mail server, backend, SPA; see Deploy
.gitattributes           '* text=auto eol=lf': every working copy uses LF
docs/                    product docs
openspec/                requirements and changes
scripts/                 doc checkers, the check runner (run_checks.py), the API client script (api_client.py), the demo
                         mail tool (demo_mail.py: load, status, add-new on the GreenMail demo mailboxes; `just demo-mail`)
.claude/                 the agent harness
```

## Layers

Built so far: the platform and the modules health, accounts, auth, mailboxes and correspondence. The layer rules are in
`.claude/rules/server-architecture.md`.

Dependencies point down: router → service → domain and repository → platform.

| Layer | File | What it does |
|---|---|---|
| Router | `router.py` | Parses the request into `schemas.py` models, takes the caller from `AuthContext` where a route needs one, calls one method of the module's service, which FastAPI injects; maps the module's domain errors to HTTP. A router never receives the database session |
| Service | `service.py` | The use cases as module-level functions that open the transaction (`session.begin()`), call domain logic and repositories, and enforce the access rules; a session-bound class (`AccountsService`, `AuthService`) delegates to them; the factory `get_<module>_service` builds the class from `get_database_session` |
| Domain | `domain.py` | Pure functions: the sign-in lock rule (`backend/app/modules/auth/domain.py`), the reason of a failed read (`backend/app/modules/mailboxes/domain.py`), parsing a raw email, the email key and the merge choice (`backend/app/modules/correspondence/domain.py`) |
| Repository | `repository.py` | Named queries; no commits, no business decisions |
| Models | `models.py` | SQLAlchemy tables of the module ([Data model](#data-model)) |
| Platform | `backend/app/platform/` | settings, db, errors, clock, mail, passwords, tokens, validation, the Origin guard, the auth context, the mail reader, the secret box, pagination |

The health module keeps its first shape: `router.py` takes a `HealthRepository` from `get_health_repository`,
the repository is built from the session, and tests replace the factory through `dependency_overrides`. The
health module has no domain or errors file.

**Domain errors.** Each module's `errors.py` defines plain exceptions without an HTTP status (for example
`EmailTaken`, `InvalidLink`, `SignInLocked`). Each router declares `ERROR_MAPPING: dict[type[Exception], HttpError]`,
where `HttpError(status_code, code, message)` is defined in `backend/app/platform/errors.py`. `main.py` passes each mapping
to `register_domain_errors`. `register_error_handlers` adds the handlers every route shares: `NotFound` (404 `not_found`),
request validation (422) and framework HTTP errors, so any path that no route serves also answers 404 `not_found`.
The shape of an answer is in [Routes and API](#routes-and-api).

**Auth context.** `current_user` in `backend/app/modules/auth/dependencies.py` reads the `vc_session` cookie, resolves a live
session and returns an `AuthContext`, which holds the user id only. It refuses a missing or dead session, and a user who
is not confirmed; the confirmation is read from the database on every request. The sign-out and profile routes of the
auth router take the context from `current_user`, and the profile query filters by its `user_id`. `current_user` is the
one router dependency that takes the session itself (through `get_database_session`), because it resolves the caller
before any router runs; the service factories take the session too. The sign-out route also reads the cookie, to end that session.

**Services and sessions.** The routers of accounts and auth never take the database session. Each module's `service.py`
has the use cases as module-level functions and a session-bound class (`AccountsService`, `AuthService`) that delegates to
them. The dependency factory `get_<module>_service` builds that class from `get_database_session`, and a handler declares
the service as a dependency, for example `service: Annotated[AccountsService, Depends(get_accounts_service)]`.

**Emails after the commit.** The services send a service email only after the transaction has committed: the registration
confirmation (on registration) and the password reset (on request). A failed send is logged and never raised:

- registration answers `email_sent: false` and the account stays unconfirmed;
- a password reset answers 202 whether or not the mail went out.

The mail sender is the `get_mail_sender` dependency, created on first use; the tests replace it with the fake.

**Origin guard.** `OriginGuardMiddleware` in `backend/app/platform/origin.py` runs before the routes. It refuses a
state-changing request (POST, PUT, PATCH, DELETE) to `/api/` whose `Origin` header is missing or differs from
the origin of `APP_BASE_URL` ([Security](#security)).

**Between modules.** A module uses another module through that module's `service.py` or `repository.py`. Such uses
exist: `backend/app/modules/accounts/service.py` uses `issue_confirmation_token` from the auth service to issue the
confirmation link, and `backend/app/modules/auth/service.py` uses the accounts repository (`find_by_id`, `find_by_email`,
`mark_confirmed`, `set_password_hash`) and its `UserRecord`. The auth dependencies use the auth service of their own module.
The mailboxes service calls `store_raw_messages` in `backend/app/modules/correspondence/service.py` for each batch it
reads, and the correspondence service uses `list_logins_for_owner` from the mailboxes repository and `find_by_id` from the
accounts repository. No module imports another module's models or private names.

Details of the platform code and the health flow are in [Backend](guide/backend.md).

## Data model

Migration `0002` (`backend/migrations/versions/0002_accounts_auth_invitations.py`) created six tables. Migration `0003`
(`backend/migrations/versions/0003_personal_accounts.py`) drops `invitations` and `organizations`, the `organization_id`
columns of `users`, `sessions` and `user_tokens`, and the `users.role` and `users.is_active` columns
([ADR 0035](adr/0035-migration-keeps-every-existing-user-as.md), [ADR 0041](adr/0041-migration-0003-drops-users-role-users.md)).
Four tables remain after `0003`. Migration `0004` (`backend/migrations/versions/0004_mailboxes_and_reply_chains.py`) adds
five tables for the modules `mailboxes` and `correspondence`, listed below. The baseline `0001` stays empty. The models are in
each module's `models.py`; the declarative `Base` in `backend/app/platform/db.py` is the metadata Alembic works from.

The downgrade to `0002` recreates one organization per user, named after the user's name, makes every user an active
administrator, gives each session and token the organization of its user, and recreates `invitations` empty.

Conventions of the tables:

- ids are UUID; timestamps are `timestamptz`;
- child rows are deleted with their parent (`ON DELETE CASCADE`); a user's sessions and tokens go with the user;
- only SHA-256 hashes of session and link tokens are stored, never the tokens;
- passwords are stored as Argon2id hashes.

| Table | Key columns | Relations and indexes |
|---|---|---|
| `users` | `id`, `email` (up to 254, unique in the installation, stored normalized), `name` (up to 200), `password_hash`, `confirmed_at` (empty until the email is confirmed), `created_at` | No relations: a user is the root owner of their own data. An unconfirmed registration of an email is replaced by deleting that user |
| `sessions` | `id`, `user_id`, `token_hash` (unique), `created_at`, `expires_at` | `user_id` → `users` (cascade); index on `user_id` |
| `user_tokens` | `id`, `user_id`, `purpose` (`confirm_email` or `reset_password`), `token_hash` (unique), `created_at`, `expires_at` | `user_id` → `users` (cascade); index on `user_id`. A new token replaces the user's earlier tokens of the same purpose; a link is consumed by one `DELETE … RETURNING`, so it works once |
| `sign_in_failures` | `id`, `email` (up to 254), `occurred_at` | No user: the email may be unknown. Index on `(email, occurred_at)` |
| `mailboxes` | `id`, `user_id`, `server` (up to 253, lower-cased), `port`, `login` (up to 254), `password_encrypted` (Fernet ciphertext; null after a disconnect), `status` (`pending`, `reading`, `read` or `failed`), `error_code` (`sign_in_failed`, `unreachable` or `read_failed`), `read_requested_at`, `last_attempt_at`, `last_read_at`, `connected_at`, `disconnected_at`, `created_at` | `user_id` → `users` (cascade); unique `(user_id, server, login)`. A disconnected mailbox keeps its row, and a connect of the same server and login reuses it |
| `mailbox_folders` | `id`, `mailbox_id`, `kind` (`inbox` or `sent`), `name` (`INBOX` or `Sent`), `uidvalidity`, `last_uid` | `mailbox_id` → `mailboxes` (cascade); unique `(mailbox_id, kind)`. `last_uid` is how far the folder has been read |
| `reply_chains` | `id`, `user_id`, `latest_email_at`, `created_at` | `user_id` → `users` (cascade); index `(user_id, latest_email_at DESC, id)` for the list |
| `emails` | `id`, `user_id`, `chain_id`, `key` (up to 998: the normalized `Message-ID`, else `no-id:<mailbox>:<folder>:<uidvalidity>:<uid>`), `message_id`, `in_reply_to`, `references` (array), `subject`, `from_address` (up to 320), `from_name`, `to_addresses` and `cc_addresses` (JSON lists), `sent_at`, `text`, `attachment_names` (array), `created_at` | `user_id` → `users` and `chain_id` → `reply_chains` (both cascade); unique `(user_id, key)`; indexes on `(chain_id, sent_at, id)`, on `references` (GIN) and on `(user_id, in_reply_to)`. An email is stored once per user, whichever mailboxes hold it |
| `email_copies` | `id`, `email_id`, `mailbox_id`, `folder_id`, `uid` (the IMAP UID) | `email_id` → `emails`, `mailbox_id` → `mailboxes` and `folder_id` → `mailbox_folders` (all cascade); unique `(folder_id, uid)`; indexes on `email_id` and `mailbox_id` |

Disconnecting a mailbox sets its `password_encrypted` to null and keeps its folders, copies, emails and reply chains
([ADR 0048](adr/0048-disconnecting-a-mailbox-deletes-its-password.md)). Deleting a user deletes all of these rows.

## Routes and API

The OpenAPI schema generated by FastAPI is the contract. `backend/app/openapi.py` prints it; `just api-client`
writes it to `frontend/src/api/openapi.json` and regenerates the SPA's client in `frontend/src/api/generated/`.

Who may call a route: **anyone** — no session needed; **signed in** — a live session of a confirmed user. A signed-out
caller of a signed-in route gets 401 `not_signed_in`. The routes below are all under `/api/v1`.

| Method and path | Who may call | Success | Domain errors (code, status) |
|---|---|---|---|
| `GET /api/v1/health` | anyone | 200, `HealthStatus` | none |
| `POST /api/v1/auth/registrations` | anyone | 201, `RegistrationResult` | `email_taken` 409 |
| `POST /api/v1/auth/email-confirmations` | anyone, with the link token | 200, `Me`; sets `vc_session` | `invalid_link` 400 |
| `POST /api/v1/auth/sessions` | anyone | 200, `Me`; sets `vc_session` | `invalid_credentials` 401, `email_not_confirmed` 403, `sign_in_locked` 429 |
| `DELETE /api/v1/auth/sessions/current` | signed in | 204; deletes `vc_session` | `not_signed_in` 401 |
| `GET /api/v1/auth/me` | signed in | 200, `Me` | `not_signed_in` 401 |
| `POST /api/v1/auth/password-resets` | anyone | 202, no body | none; the same answer for every email |
| `POST /api/v1/auth/password-resets/complete` | anyone, with the link token | 204 | `invalid_link` 400 |
| `GET /api/v1/mailboxes` | signed in | 200, `list[Mailbox]` (connected mailboxes, at most 100, not paginated) | none |
| `POST /api/v1/mailboxes` | signed in | 201, `Mailbox`; checks the sign-in before saving | `mailbox_exists` 409, `mailbox_sign_in_failed` 422, `mailbox_unreachable` 422 |
| `POST /api/v1/mailboxes/{mailbox_id}/refresh` | signed in | 202, `Mailbox`; asks for a read at the next tick | `not_found` 404 |
| `DELETE /api/v1/mailboxes/{mailbox_id}` | signed in | 204; deletes the password, the emails stay | `not_found` 404 |
| `GET /api/v1/reply-chains` | signed in | 200, `Page[ReplyChainSummary]`; `limit` 1 to 100 (default 50), `cursor`; the latest chain first | `invalid_cursor` 400 |
| `GET /api/v1/reply-chains/{chain_id}` | signed in | 200, `ReplyChain`; its emails oldest first, at most 500 | `not_found` 404 |

Registration is `POST /api/v1/auth/registrations`, next to the other auth routes of the same prefix. Its body is `name`,
`email` and `password` ([ADR 0037](adr/0037-registration-asks-for-name-email-and.md)); any other field, such as
`organization_name`, answers 422 `validation_failed`. There are no organization, invitation or member routes: a request to
`/api/v1/members` or `/api/v1/invitations` answers 404 `not_found`, as any unknown path does.

Every state-changing request also answers 403 `forbidden_origin` when its `Origin` is missing or foreign, and
a body with an unknown field, or an invalid one, answers 422 `validation_failed`.

Schemas of the responses: `Me` is `user_id`, `name`, `email`; `RegistrationResult` is `email`, `email_sent`.

**Error shape.** A handled error answers `{"error": {"code": "…", "message": "…"}}`, where `message` is the Russian
text of the error. A validation error adds `fields`: `{"error": {"code": "validation_failed", "message": "Проверьте поля формы", "fields": {"<field>": "<Russian message>"}}}`.
A framework HTTP error other than 404 keeps FastAPI's `{"detail": …}` shape; a 404 answers `not_found`.

**SPA routes.** The browser routes of `frontend/src/App.tsx` (`BrowserRouter`):

| Path | Page | Who sees it |
|---|---|---|
| `/register` | «Регистрация», with the fields «Имя», «Email», «Пароль» | a signed-out visitor |
| `/sign-in` | «Вход» | a signed-out visitor |
| `/forgot-password` | «Восстановление пароля» | a signed-out visitor |
| `/confirm-email` | «Подтверждение email» | anyone, with the link |
| `/reset-password` | «Новый пароль» | anyone, with the link |
| `/health` | «Состояние сервиса» (page heading) | anyone |
| `/` | «VibeCoding» (start page): the signed-in user's name and «Выйти» | a signed-in user |
| `/mailboxes` | the form «Подключить ящик» and the list of the user's mailboxes, with their status and «Обновить» and «Отключить» | a signed-in user |
| `/chains` | the list of the user's reply chains | a signed-in user |
| `/chains/:id` | one reply chain with its emails | a signed-in user |
| `*` | «Страница не найдена» | anyone; `/members` and `/invitation` fall here too |

A signed-out visitor who opens a signed-in page goes to `/sign-in?next=…` and returns after signing in. A
signed-in user who opens a guest page goes to `next` (a path of this site) or to `/`. The link tokens are read
from the URL fragment `#token=`. The password reset form sends its token in the body of
`POST /api/v1/auth/password-resets/complete` on each submit.

## Deploy

Not deployed. Local development only. `docker-compose.yml` runs five services:

- `db` — PostgreSQL 18; the host port comes from `POSTGRES_PORT` ([Environment variables](tech.md#environment-variables)).
- `mailpit` — the dev mail catcher, the Mailpit image pinned to v1.29 in `docker-compose.yml`. SMTP listens on port 1025 inside the compose network
  and is not published to the host; the web UI is on host port 8025.
- `greenmail` — the demo mail server for the mailboxes, GreenMail 2.1.8; IMAP is published on host port 3143 and holds the
  demo users of `just demo-mail` ([Mail reading](guide/mail-reading.md#demo-mailboxes), [ADR 0049](adr/0049-demo-mailboxes-run-on-greenmail-in.md)).
- `backend` — built from `docker/backend.Dockerfile` (Python 3.12 with uv). Its command runs `uv sync --frozen
  --no-install-project`, then `alembic upgrade head`, then uvicorn with `--reload` on port 8000. The `uv sync`
  comes first because the named venv volume is filled from the image only once, so a dependency added later
  would never reach the container without it. The image bakes the locked dependencies.
- `frontend` — the `node:24` image; runs the Vite dev server on port 5173.

The `backend` service sets these environment variables itself: `DATABASE_URL` (built from the Postgres
variables, pointing at the `db` service), `WATCHFILES_FORCE_POLLING`, `SMTP_HOST=mailpit`,
`APP_BASE_URL=http://localhost:5173` (the links in the emails point at the SPA on the host), `IMAP_INSECURE_HOSTS=greenmail`
(the demo server is read without TLS), and `MAIL_FROM` and `MAILBOX_ENCRYPTION_KEY`, taken from `.env`. The repo-root `.env`
is not mounted into the container, so the other settings take their defaults there. The list of all variables is in [Environment variables](tech.md#environment-variables).

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
  are stored. A password-reset or confirmation link works once.
- **Links in the URL fragment.** The emailed links carry the token after `#token=`. The fragment is not sent to
  the server, so the token stays out of server logs and of the `Referer` header.
- **Sessions.** The browser holds a random token in the `vc_session` cookie: `HttpOnly`, `SameSite=Lax`, `Path=/`,
  with a lifetime of the session lifetime. `Secure` follows the setting `SESSION_COOKIE_SECURE`, which is off by
  default for local HTTP ([Environment variables](tech.md#environment-variables)). Sessions are rows of PostgreSQL
  ([ADR 0012](adr/0012-sessions-are-stored-server-side-in.md)); each request resolves the cookie. Signing out ends
  that browser's session only. Completing a password reset deletes all of the user's sessions at once.
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
- **No active flag.** An account has no `is_active` flag and no route can disable one: a user is refused only for an
  unconfirmed email or for a dead session ([ADR 0036](adr/0036-the-is-active-flag-and-deactivation.md)).
- **Owner filter.** A query that acts for the signed-in user takes its `user_id` from the `AuthContext` of the request,
  never from a value in the request; the profile read (`get_me` in `backend/app/modules/auth/service.py`) is such a query.
  The other lookups are not owner-scoped by design: `find_by_email` (`backend/app/modules/accounts/repository.py`) finds
  the user of an email across the installation, because sign-in, registration and password reset start before anyone is
  signed in; sessions and link tokens are found by their token hash. The request bodies refuse unknown fields, so a
  `user_id` sent by the client answers 422 `validation_failed`.
- **One email, one user.** An email belongs to one user across the installation
  ([ADR 0008](adr/0008-one-email-belongs-to-one-user.md)).
- **Mailbox passwords.** An app password is stored only as a Fernet ciphertext (`mailboxes.password_encrypted`), with the key
  `MAILBOX_ENCRYPTION_KEY` (`backend/app/platform/secret_box.py`). The plaintext lives in memory during a sign-in or a read.
  No answer carries it. A failed read of one mailbox logs a warning with the exception's class name only; a failure outside
  that per-mailbox handling (claiming a mailbox, the database) is logged by the reading loop with `LOG.exception`, so its
  traceback reaches the log. Disconnecting sets the
  ciphertext to null. Losing or changing the key makes every connected mailbox ask for a new app password.
- **Read-only mail access.** The reader signs in, selects each folder read-only, searches and fetches with `BODY.PEEK`; it
  sends no command that writes to the server, and a unit test allows only the commands it uses
  (`ALLOWED` and `test_fr25_a_read_sends_only_read_only_commands` in `backend/app/platform/test_mail_reader.py`).
  No mailbox is changed, so the emails stay unread in the mailbox.
- **TLS for mail.** Every IMAP connection uses TLS with the default certificate checks, except hosts listed in
  `IMAP_INSECURE_HOSTS`; the compose file lists only the demo server `greenmail`.
- **Owner filter for mailboxes and chains.** The queries over mailboxes and reply chains take their `user_id` from the
  `AuthContext`: `list_connected_for_owner`, `get_connected_by_id_for_owner` and `get_by_server_and_login_for_owner` in
  `backend/app/modules/mailboxes/repository.py`, and the `_for_owner` queries of `backend/app/modules/correspondence/repository.py`.
  Another user's mailbox or chain answers 404 `not_found`. Four calls are not owner-filtered: `claim_next_due_mailbox`,
  which the background run calls across all users (its docstring says so), and three that take the id of a mailbox or an
  email their caller already holds, as their docstrings say: `ensure_folders` and `update_folder_progress` for the mailbox
  the run has just claimed, and `add_copy_if_absent` for the email just stored (`add_copy_if_absent` is in
  `backend/app/modules/correspondence/repository.py`).
- **HTML as text.** The server keeps an email as text. An HTML part is converted only when the email has no `text/plain` part
  (`_body_text` in `backend/app/modules/correspondence/domain.py`), and the conversion drops `script`, `style` and `head`.
  The SPA shows the text with `white-space: pre-wrap` and never sets HTML.

Not built yet: the consent gate that must pass before email text goes to a third-party service. The analysis engine is not
chosen ([Components and processes](#components-and-processes)).
