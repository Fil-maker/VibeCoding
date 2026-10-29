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
| 28.10.2026 | [0023](adr/0023-organizations-are-removed-anyone-can-register.md) | Organizations are removed; anyone can register as an individual user | [human] | Accepted |
| 28.10.2026 | [0024](adr/0024-product-core-is-correspondence-history-organized.md) | Product core is correspondence history organized as trees per project; sentiment becomes a later layer over the trees | [human] | Accepted |
| 28.10.2026 | [0025](adr/0025-projects-are-created-manually-by-the.md) | Projects are created manually by the user; emails get into a project automatically by clustering; the user can add rules and assign emails by hand | [human] | Accepted |
| 28.10.2026 | [0026](adr/0026-a-tree-is-the-hierarchy-project.md) | A tree is the hierarchy project -> counterparty -> thread | [human] | Accepted |
| 28.10.2026 | [0027](adr/0027-a-user-can-connect-several-mailboxes.md) | A user can connect several mailboxes; one project's correspondence is tracked across all of them | [human] | Accepted |
| 28.10.2026 | [0028](adr/0028-an-empty-project-is-filled-from.md) | An empty project is filled from its description: the user writes a description, the engine finds matching emails, forms threads from them and sorts the emails into those threads | [human] | Accepted |
| 28.10.2026 | [0029](adr/0029-a-thread-is-a-topic-formed.md) | A thread is a topic formed by the engine; it groups whole mail reply chains (References/In-Reply-To), and a chain is never split between threads | [human] | Accepted |
| 28.10.2026 | [0030](adr/0030-stability-policy-a-continuation-goes-to.md) | Stability policy: a continuation goes to its chain's place; then user rules; then the engine if confident; otherwise the project's Unassigned. Priority manual > rule > engine; the engine never moves already placed chains; re-sorting a whole project only by an explicit user action, keeping manual placements | [human] | Accepted |
| 28.10.2026 | [0031](adr/0031-a-chain-with-several-counterparties-is.md) | A chain with several counterparties is shown under each of them | [human] | Accepted |
| 28.10.2026 | [0032](adr/0032-the-analysis-engine-is-built-by.md) | The analysis engine is built by us as our own service, external to the user | [human] | Accepted |
| 28.10.2026 | [0033](adr/0033-access-boundary-invariant-if-the-engine.md) | Access boundary invariant: if the engine uses a third-party model, email text goes there only with the user's consent | [human] | Accepted |
| 28.10.2026 | [0034](adr/0034-a-reply-chain-belongs-to-at.md) | A reply chain belongs to at most one project; an email that touches a second project is shown there as a reference to its chain | [human] | Accepted |
| 28.10.2026 | [0035](adr/0035-migration-keeps-every-existing-user-as.md) | Migration keeps every existing user as a personal account (same email, password, confirmation); organizations, invitations and roles are dropped; downgrade recreates one organization per user | [human] | Accepted |
| 28.10.2026 | [0036](adr/0036-the-is-active-flag-and-deactivation.md) | The is_active flag and deactivation are removed; formerly deactivated users can sign in again | [human] | Accepted |
| 28.10.2026 | [0037](adr/0037-registration-asks-for-name-email-and.md) | Registration asks for name, email and password; the start page shows the name and «Выйти» | [human] | Accepted |
| 28.10.2026 | [0038](adr/0038-this-change-also-removes-organization-employee.md) | This change also removes Organization, Employee, Administrator, Member and Invitation from the glossary and rewrites the harness rules, harness.md, invariant-reviewer, explore and delta-rules for a single-user owner | [human] | Accepted |
| 28.10.2026 | [0039](adr/0039-delta-specs-of-1-1-personal.md) | Delta specs of 1-1-personal-accounts approved: FR-1 renamed «Register a user», FR-1…FR-4, FR-6…FR-8, FR-17, FR-20 modified; FR-9…FR-16, FR-18, FR-19 removed; FR-21 «Users never see each other» added; invitations and organization-members retired | [human] | Accepted |
| 28.10.2026 | [0040](adr/0040-the-deactivation-slice-merges-into-the.md) | The deactivation slice merges into the migration 0003 slice: a deactivated user of task 0.2 signs in after the upgrade is the red test for removing is_active, roles and organizations | [AI → accepted] | Accepted |
| 29.10.2026 | [0041](adr/0041-migration-0003-drops-users-role-users.md) | Migration 0003 drops users.role, users.is_active and the organization_id columns in the same migration whose models stop writing them, an exception to the database rule against dropping a column with data in the same migration that stops writing it | [AI → accepted] | Accepted |
| 29.10.2026 | [0042](adr/0042-check-doc-links-py-and-check.md) | check_doc_links.py and check_doc_facts.py skip .claude/worktrees/ | [human] | Accepted |
| 29.10.2026 | [0043](adr/0043-demo-version-for-the-customer-ships.md) | Demo version for the customer ships as a series of tasks 1.1-1.4: personal accounts, mailboxes and reply chains, projects and engine, manual placement and rules | [human] | Accepted |
| 29.10.2026 | [0044](adr/0044-emails-come-from-real-imap-mailboxes.md) | Emails come from real IMAP mailboxes plus a local demo mailbox with prepared correspondence | [human] | Accepted |
| 29.10.2026 | [0045](adr/0045-first-engine-is-local-and-deterministic.md) | First engine is local and deterministic (text similarity), no third-party model | [human] | Accepted |
| 29.10.2026 | [0046](adr/0046-mailboxes-are-read-in-a-background.md) | Mailboxes are read in a background task inside the backend: right after connecting, every 5 minutes and on the button «Обновить»; each mailbox shows its status and last read time | [human] | Accepted |
| 29.10.2026 | [0047](adr/0047-read-folders-inbox-and-sent-emails.md) | Read folders Inbox and Sent, emails of the last 12 months (an app setting) | [human] | Accepted |
| 29.10.2026 | [0048](adr/0048-disconnecting-a-mailbox-deletes-its-password.md) | Disconnecting a mailbox deletes its password and stops reading; emails and reply chains already read stay | [human] | Accepted |
| 29.10.2026 | [0049](adr/0049-demo-mailboxes-run-on-greenmail-in.md) | Demo mailboxes run on GreenMail in Docker; just demo-mail loads prepared Russian correspondence; manual checks use it, automated tests fake the mailbox | [human] | Accepted |
