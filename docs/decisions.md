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
| 23.10.2026 | [0008](adr/0008-one-email-belongs-to-one-user.md) | One email belongs to one user in exactly one organization; email is unique across the installation | [human] | Accepted |
| 23.10.2026 | [0009](adr/0009-the-registrant-s-email-is-confirmed.md) | The registrant's email is confirmed by a link before they can sign in | [human] | Accepted |
| 23.10.2026 | [0010](adr/0010-in-this-task-the-administrator-lists.md) | In this task the administrator lists members, deactivates an employee (data and history kept, sign-in closed) and appoints or removes administrators; the last active administrator cannot be removed or deactivated | [human] | Accepted |
| 23.10.2026 | [0011](adr/0011-sign-in-with-yandex-id-is.md) | Sign-in with Yandex ID is dropped, not deferred | [human] | Accepted |
| 23.10.2026 | [0012](adr/0012-sessions-are-stored-server-side-in.md) | Sessions are stored server-side in PostgreSQL; the browser holds a random token in an HttpOnly, SameSite=Lax cookie; CSRF guarded by an Origin check | [human] | Accepted |
| 23.10.2026 | [0013](adr/0013-new-dependencies-argon2-cffi-for-password.md) | New dependencies: argon2-cffi for password hashing (Argon2id), aiosmtplib for SMTP, Mailpit as a dev mail catcher service in docker-compose; sign-in attempt limits stored in PostgreSQL, no Redis | [human] | Accepted |
| 23.10.2026 | [0014](adr/0014-defaults-invitation-7-days-email-confirmation.md) | Defaults: invitation 7 days, email confirmation link 24 hours, password reset link 1 hour, session 14 days, password 10-128 characters, 5 failed sign-ins per email in 15 minutes lock sign-in for that email for 15 minutes; all configurable by settings | [human] | Accepted |
| 23.10.2026 | [0015](adr/0015-spa-routing-with-react-router-7.md) | SPA routing with react-router 7 in declarative mode | [human] | Accepted |
| 23.10.2026 | [0016](adr/0016-change-0-2-tests-sit-at.md) | Change 0-2 tests sit at four seams only: the HTTP API /api/v1 (integration, real PostgreSQL, get_mail_sender and get_clock overridden), public platform functions (unit), the 0002 migration chain, SPA components (Vitest, generated client faked at the network boundary); services, repositories and private helpers are tested only through HTTP | [human] | Accepted |
| 24.10.2026 | [0017](adr/0017-ruff-allows-cyrillic-confusable-letters-allowed.md) | Ruff allows Cyrillic confusable letters (allowed-confusables in backend/pyproject.toml) instead of per-line noqa RUF001 | [human] | Accepted |
| 27.10.2026 | [0018](adr/0018-fr-16-two-administrators-remove-each.md) | FR-16 «Two administrators remove each other at once»: the refused change answers «В организации должен остаться хотя бы один активный администратор», or «Не найдено» when the other change already took its author's administrator role; one active administrator always remains | [human] | Accepted |
| 27.10.2026 | [0019](adr/0019-when-the-only-administrator-deactivates-themselves.md) | When the only administrator deactivates themselves, «Нельзя отключить свою учётную запись» (cannot_deactivate_self) wins over last_administrator | [human] | Accepted |
| 27.10.2026 | [0020](adr/0020-add-gitattributes-with-text-auto-eol.md) | Add .gitattributes with '* text=auto eol=lf' and normalize working copies to LF | [human] | Accepted |
| 27.10.2026 | [0021](adr/0021-routers-of-accounts-auth-and-invitations.md) | Routers of accounts, auth and invitations take a session-bound service class (AccountsService, AuthService, InvitationsService) from get_<module>_service instead of the database session | [human] | Accepted |
| 27.10.2026 | [0022](adr/0022-fix-the-harness-parse-only-the.md) | Fix the harness: parse only the pytest short summary in sandbox_tests.py, write every harness text file with newline='\n'; the deleted-test refusal of tdd_sandbox close stays, and a name-matching split allowance is recorded in .claude/harness.md «Deferred» | [human] | Accepted |
