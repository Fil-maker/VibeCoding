# Tasks

One code cycle (`.claude/skills/feature/code-step.md`) per slice, each with its own sandbox, red check
and `close`: groups 1–3 (platform units, the migration, FR-1…FR-8), group 4 (FR-9…FR-12), group 5
(FR-13…FR-20), group 6 (SPA). `test-writer` writes the slice's tests from the brief; `code-writer`
writes the slice's groups. Tests sit only at the seams of design «Test seams»: the HTTP API, the public
`platform` functions, the migration chain, the SPA components. Docs
are updated at `/finish` through `/document`, except the product docs of group 7.

## 1. Platform and setup

- [x] 1.1 Add `argon2-cffi` and `aiosmtplib` to `backend/pyproject.toml` and `uv.lock`; add `react-router` to `frontend/package.json` and `pnpm-lock.yaml` — check - `uv sync --directory backend` and `pnpm --dir frontend install --frozen-lockfile` succeed
- [x] 1.2 Settings of design «Settings» in `platform/settings.py`, `.env.example` lines, compose overrides for the backend (`SMTP_HOST=mailpit`, `APP_BASE_URL`) — check - a unit test shows the defaults and that a missing `APP_BASE_URL`, `MAIL_FROM` or `SMTP_HOST` fails at build
- [x] 1.3 `mailpit` service in `docker-compose.yml` with a pinned tag, SMTP 1025 in the network, UI on host port 8025 — check - `docker compose config` is valid and `docker compose up -d mailpit` serves `http://localhost:8025`
- [x] 1.4 `platform/errors.py` (structured error, the 422 → `validation_failed` handler with Russian field messages), `platform/origin.py` (the Origin middleware), `platform/passwords.py` (Argon2id in a worker thread, dummy verify), `platform/mail.py` (`MailSender`, `SmtpMailSender`, `FakeMailSender`, `get_mail_sender`), `get_clock`, `platform/auth_context.py` — check - unit tests: error shape, Origin refused when missing or foreign and passed when equal, hash verify and rehash flag, the fake records and fails on demand

## 2. Schema

- [x] 2.1 Models of design «Data model» in `accounts`, `auth`, `invitations` and the revision `0002` — check - `alembic upgrade head`, `alembic downgrade 0001`, `alembic upgrade head` and `alembic check` succeed against the test database
- [x] 2.2 Test factories in `backend/tests/factories.py` for organizations, users (role, confirmed, active), sessions and invitations (each status) — check - used by the scenario tests of groups 3–5

## 3. Registration and sign-in (FR-1…FR-8)

- [x] 3.1 `accounts`: registration, repeated unconfirmed registration, confirmation; `auth`: sign-in, the lock, sessions and the cookie, sign-out, `GET /auth/me`, reset request and completion, `current_user` and `current_admin` — routes, errors and texts of design «Interface» — check - the FR-1…FR-8 scenario tests pass
- [x] 3.2 Scenario tests for FR-1…FR-8 (`test-writer`, sandbox): integration tests through the HTTP API with the fake sender and the settable clock, taking tokens from the faked emails — check - red before the code, green after `tdd_sandbox.py close`

## 4. Invitations (FR-9…FR-12)

- [x] 4.1 `invitations`: invite, list, resend, revoke, preview, accept; sending after commit with `delivery` updated in a second transaction — check - the FR-9…FR-12 scenario tests pass
- [x] 4.2 Scenario tests for FR-9…FR-12 (`test-writer`, sandbox), including the failing fake sender and the 8-day clock — check - red before the code, green after `close`

## 5. Members and the access boundary (FR-13…FR-20)

- [x] 5.1 `accounts`: members list, deactivate, reactivate, role change, the organization-row lock for the last-administrator guard; administrator-only routes answer 404 to employees and to other organizations — check - the FR-13…FR-20 scenario tests pass
- [x] 5.2 Scenario tests for FR-13…FR-20 (`test-writer`, sandbox): two organizations «ООО Ромашка» and «Лютик» in every negative case, an employee against every administrator route, a body naming `organization_id`, a foreign `Origin`, two concurrent role changes on two connections — check - red before the code, green after `close`

## 6. SPA

- [x] 6.1 `just api-client`; routing, `AuthProvider`, `RequireUser`/`RequireAdmin` with `next`, and the pages of design «SPA pages» with the exact Russian texts; tokens read from the URL fragment — check - `pnpm --dir frontend lint`, `typecheck`, `build` pass and the client freshness check in `just check` passes
- [x] 6.2 Component tests (`test-writer`, sandbox) for the guards (signed out → «Вход» with return, employee → «Страница не найдена»), the start page per role, the sign-in error texts, the invitation statuses and «Отправить ещё раз», the members actions and the last-administrator message — check - red before the code, green after `close`

## 7. Product docs

- [x] 7.1 `docs/domain.md`: glossary terms Member, Invitation, Session; «Data and privacy» says the app's service emails go through its own SMTP account and do not touch «Mailbox read-only»; requirements map and «Last FR number: FR-20» at archive — check - `just check` doc facts pass
- [x] 7.2 `docs/ideas.md`: remove «Sign-in and organization» (now task 0.2), add «Account settings» with the deferred items of proposal «Out of scope» — check - the entry exists and the plan row links nothing stale

## 8. Verification

- [x] 8.1 `just check` passes — check - all PASS
- [x] 8.2 `/test` with `all` passes — check - backend unit, backend database and frontend suites report counts, none NOT PRESENT
- [x] 8.3 Manual flow 1 (`flow-checker`, preview + Mailpit): register «Ромашка» as `flow-0-2-sign-in-and-organization@example.test`, see the confirmation text, open the link from Mailpit, land signed in as administrator, sign out, sign in — check - its PASS report
- [x] 8.4 Manual flow 2: as that administrator invite a second throwaway address, accept from Mailpit in a fresh tab, see the employee start page without «Участники», open `/members` → «Страница не найдена»; as administrator deactivate the employee and see the employee sent to «Вход» — check - its PASS report
- [x] 8.5 Manual flow 3: «Забыли пароль?», the reset email in Mailpit, set a new password, the old one is refused; stop Mailpit, invite → «Не отправлено», start it, «Отправить ещё раз» → «Отправлено» — check - its PASS report; test data cleaned up

## 9. Done when

- [x] 9.1 A new organization registers on the page «Регистрация», and its registrant signs in after following the confirmation link from the email caught by Mailpit — check - 8.3 and the FR-1, FR-2 tests
- [x] 9.2 The administrator invites an employee by email; the employee accepts the invitation, sets a password and signs in; a used, revoked or expired invitation is refused — check - 8.4 and the FR-9…FR-12 tests
- [x] 9.3 A user who forgot the password resets it by the emailed link, and their old sessions stop working — check - 8.5 and the FR-7, FR-8 tests
- [x] 9.4 After 5 wrong passwords in 15 minutes sign-in for that email is locked for 15 minutes — check - the FR-5 tests
- [x] 9.5 The administrator sees the members of the organization, deactivates an employee, who can no longer sign in, and appoints another administrator; the last active administrator cannot be removed — check - 8.4 and the FR-13…FR-16 tests
- [x] 9.6 An employee cannot open the administrator's pages or actions, and a user of organization A gets «not found» for data of organization B — check - the FR-18, FR-19 tests and 8.4
- [x] 9.7 When SMTP fails, the invitation is shown as «not sent» and can be sent again — check - 8.5 and the FR-10 tests
- [x] 9.8 `just check` and `just test-all` pass — check - 8.1 and 8.2

## Workflow follow-up

- `/finish 0.2`: invariant review, `openspec archive 0-2-sign-in-and-organization --yes`, `/document` (architecture «Implementation status», «Repository structure», «Layers», «Data model», «Routes and API», «Deploy», «Security»; tech «Stack», «Environment variables»; a guide article on auth), `/journal`, `/commit` with `feat:`.
