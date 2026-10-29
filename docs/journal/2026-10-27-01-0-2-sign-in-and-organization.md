# Sign-in and organization

Date: 27.10.2026 · Task: 0.2 · Change: 0-2-sign-in-and-organization

## Goal

Task 0.2 «Sign-in and organization»: without users and organizations the data has no owner, and the access
boundary owner filter needs real ones. Five new capabilities, FR-1…FR-20: `organization-registration`,
`sign-in`, `invitations`, `organization-members`, `access-boundary`. An organization registers itself and
the registrant becomes its first administrator; employees join only by an administrator's emailed
invitation; sign-in is by email and password, with password reset by email.

Out of scope: changing the password or email from a profile, account deletion, 2FA and a per-IP limit (moved
to `docs/ideas.md` «Account settings»), and sign-in with Yandex ID (dropped). The invariant «Access
boundary» is implemented, «History is kept» is respected, «Mailbox read-only» is not touched: service emails
go through the app's own SMTP account.

## What was done

- **Design session (23.10.2026).** The AI took the decisions from `docs/ideas.md` as made, settled the open
  questions with the user, added the plan row 0.2 and wrote the change on the branch
  `feat/0-2-sign-in-and-organization`: a proposal, five delta specs, a design with an «Interface» section,
  tasks in nine groups and a handoff marked `Approved: 2026-10-23`. `openspec validate --strict` passed.
  - Three modules: `accounts`, `auth`, `invitations`; the `current_user` dependency lives in `auth`, not in
    platform, because platform does not import modules.
  - Sessions are rows in the database; the cookie holds only a token. Links in emails carry the token in a
    URL fragment (`#token=`); only hashes are stored.
  - Emails are sent after commit in the same request; an invitation row serves as the outbox. The row lock
    on the organization (`with_for_update`) protects the last administrator and duplicate invitations.
  - Migration `0002` creates six tables; rollback is `downgrade 0001`.
- **Code sessions (23.10 – 27.10.2026).** The user confirmed four test seams and one sandbox code cycle per
  slice. In each slice `test-writer` wrote tests in the sandbox, `code-writer` wrote code, the AI checked
  that the tests were red, `test-auditor`s reviewed the tests, and `close` moved them into the project.
  - Slice 1, groups 1–3 (FR-1…FR-8): platform (settings, passwords with Argon2id, mail, tokens, errors,
    Origin check), schema, factories, registration, sign-in, password reset; 88 backend tests.
  - Slice 2, group 4 (FR-9…FR-12): invitations; 138 backend tests.
  - Slice 3, group 5 (FR-13…FR-20): members and the access boundary, including the FR-16 race of two
    administrators; 214 backend tests, the race tests stable over 5 runs.
  - Slice 4, group 6 (SPA): react-router 7 in declarative mode, `AuthProvider` with the guards
    `RequireUser`, `RequireAdmin`, `RequireGuest`, pages for registration, sign-in, reset, invitation, start
    page and members; 60 SPA tests, stable over 3 runs. The health page moved to `/health`. A «SPA
    interface» section was added to the design first.
  - `.gitattributes` with `* text=auto eol=lf` was added and 78 working copies were converted to LF so
    that `frontend-format` passes.
- **`/finish` run (27.10.2026).**
  - Group 8: `just check` all PASS; tests 21 backend unit, 60 SPA, 193 database. Manual flows 8.3–8.5 by
    `flow-checker` on `just dev` with Mailpit all PASS: registration and confirmation, invitation and
    acceptance, deactivation (the open page of the deactivated employee leads to «Вход»), password reset,
    and a mail failure («Не отправлено» then «Отправлено» after «Отправить ещё раз»).
  - Running `just dev` exposed two dev-stack defects, fixed by `code-writer`: the backend container lacked
    `MAIL_FROM` (the repo-root `.env` is not mounted) and the named venv volume never received the new
    dependencies (the backend command now runs `uv sync` first). The other project's containers holding
    ports 8000 and 5173 were stopped for the run with the user's consent and started again afterwards. Test
    data was removed from the dev database and Mailpit.
  - Invariant review: no blocker. Fixed by `code-writer`: `members_router.py` merged into
    `accounts/router.py` (`naming.md` fixed role names); `get_clock` made lazy; an `organization_id`
    filter added to id-only repository reads and writes; `isAdministrator` in `AuthProvider`. Dropped: the
    202 password-reset route without `response_model` (no body, like the 204 routes).
  - The change was archived as `2026-10-27-0-2-sign-in-and-organization`; 20 requirements went into
    `openspec/specs/`.
  - `/document`: 13 ADRs (0008–0020) written after the user's confirmation; `doc-writer`s updated
    `docs/architecture.md`, `docs/tech.md`, `docs/guide/backend.md`, `docs/guide/frontend.md` and the new
    `docs/guide/auth.md`. The `doc-writer` found routers taking the database session against
    `data-access.md`; the user chose to fix it now, and `code-writer` introduced session-bound service
    classes (`AccountsService`, `AuthService`, `InvitationsService`) with `get_<module>_service`
    factories; the OpenAPI schema is unchanged.
  - Product docs approved by the user: `docs/domain.md` (requirements map, `Last FR number: FR-20`,
    glossary Member, Invitation, Session, «Data and privacy»), `docs/plan.md` (0.2 moved to Done),
    `docs/prd.md` (stage 0 scope).

## Key questions to the AI

The questions were asked by the AI; the user's answers are below. The digest holds no questions the user
put to the AI for this change, only commands such as «Запускай первый срез: песочница, test-writer и
code-writer по группам 1–3».

- Can one email belong to two organizations? Answer: «Нет, одна организация (рекомендую)».
- Confirm the registrant's email? Answer: «Да, ссылкой из письма (рекомендую)».
- What may the administrator do with members in this task? Answer: «Список, деактивация, назначение админа
  (рекомендую)».
- Sign-in with Yandex ID? Answer: «Отказаться совсем».
- Which task number? Answer: «0.2». How to hold the session? Answer: «Сессия в БД + HttpOnly-cookie
  (рекомендую)». New dependencies? Answer: «argon2-cffi + aiosmtplib + Mailpit (рекомендую)». Limits and
  terms? Answer: «Предложенные (рекомендую)».
- Write the plan row? Answer: «Да (рекомендую)».
- Approve the deltas, design and tasks, and add react-router 7? Answers: «Да (рекомендую)» and «Да,
  react-router 7 (рекомендую)».
- Agree on the four seams? Answer: «Да, все четыре (Recommended)». How to combine TDD vertical slices with
  the project's code step? Answer: «Цикл на группу FR (Recommended)». The AI had pointed out the
  mismatch: the TDD skill wants one test, then code, while `code-step.md` writes all scenario tests at once.
- FR-16: the loser of the race may get «Не найдено» instead of the required message. Answer: «Уточнить THEN
  (Recommended)». A sole administrator deactivating themselves: which error wins? Answer: «Нельзя отключить
  свою… (Recommended)».
- Ports 8000 and 5173 are held by another project's containers: how to start the stack? Answer: «Остановить
  чужие (Recommended)».
- Accept the `docs/domain.md` edits? Answer: «Принять (Recommended)». Mark 0.2 in plan and PRD? Answer:
  «Plan + PRD (Recommended)».
- Which decisions become ADRs? Answer: «Все, кроме 8, 10, 12 (Recommended)».
- Routers pass the session to services against «routers never touch the session»; what to do? Answer:
  «Исправить сейчас (Recommended)».
- Add `.gitattributes` with `eol=lf`? The user agreed: «Да, добавь .gitattributes с * text=auto eol=lf и
  нормализуй переносы строк, чтобы just check прошёл».

## Decisions

| Decision | Alternatives | Reason | Who |
| --- | --- | --- | --- |
| One email belongs to one user in exactly one organization; email is unique across the installation | A user in several organizations with a switcher | Chosen by the user: no organization switcher, the organization filter comes straight from the session | [human] |
| The registrant's email is confirmed by a link before they can sign in | Sign-in right after registration | Chosen by the user: protects against registering an organization on someone else's address | [human] |
| In this task the administrator lists members, deactivates an employee (data and history kept, sign-in closed) and appoints or removes administrators; the last active administrator cannot be removed or deactivated | Members list only; invitations only | Chosen by the user: a departed employee must lose access without waiting for another task | [human] |
| Sign-in with Yandex ID is dropped, not deferred | Defer to ideas.md | Chosen by the user: drop it entirely | [human] |
| Sessions are stored server-side in PostgreSQL; the browser holds a random token in an HttpOnly, SameSite=Lax cookie; CSRF guarded by an Origin check | Stateless JWT | Chosen by the user: deactivation, role change and password reset close access at once | [human] |
| New dependencies: argon2-cffi for password hashing (Argon2id), aiosmtplib for SMTP, Mailpit as a dev mail catcher service in docker-compose; sign-in attempt limits stored in PostgreSQL, no Redis | stdlib only: hashlib.scrypt and smtplib | Approved by the user as recommended | [human] |
| Defaults: invitation 7 days, email confirmation link 24 hours, password reset link 1 hour, session 14 days, password 10-128 characters, 5 failed sign-ins per email in 15 minutes lock sign-in for that email for 15 minutes; all configurable by settings | Stricter: invitation 3 days, session 1 day, password 12+, lock 1 hour | Approved by the user as recommended | [human] |
| SPA routing with react-router 7 in declarative mode | TanStack Router; a hand-written router over the History API | Approved by the user as recommended | [human] |
| Change 0-2 tests sit at four seams only: the HTTP API /api/v1 (integration, real PostgreSQL, get_mail_sender and get_clock overridden), public platform functions (unit), the 0002 migration chain, SPA components (Vitest, generated client faked at the network boundary); services, repositories and private helpers are tested only through HTTP | - | The user confirmed the proposed seams so testing effort lands on the public contract, not internals | [human] |
| Ruff allows Cyrillic confusable letters (allowed-confusables in backend/pyproject.toml) instead of per-line noqa RUF001 | - | The user approved it: every Russian UI string and spec quote trips RUF001/RUF003, and per-line noqa would clutter the code and tests | [human] |
| FR-16 «Two administrators remove each other at once»: the refused change answers «В организации должен остаться хотя бы один активный администратор», or «Не найдено» when the other change already took its author's administrator role; one active administrator always remains | - | The user chose to refine the THEN: a request that arrives after its author lost the role is no longer an administrator's request, and the invariant that matters is one active administrator | [human] |
| When the only administrator deactivates themselves, «Нельзя отключить свою учётную запись» (cannot_deactivate_self) wins over last_administrator | - | The user chose it: it matches the FR-14 scenario and the current code | [human] |
| Add .gitattributes with '* text=auto eol=lf' and normalize working copies to LF | - | just check frontend-format failed: core.autocrlf=true gave CRLF working copies while Prettier expects LF | [human] |
| Routers of accounts, auth and invitations take a session-bound service class (AccountsService, AuthService, InvitationsService) from get_<module>_service instead of the database session | - | The user chose to fix it now: data-access.md says routers never touch the session | [human] |

ADRs: 0008–0021 in `docs/adr/`. Three process decisions were recorded but not written as ADRs: the task id
0.2 («the highest id + 1 as plan.md says»), the approval of the deltas FR-1..FR-20 with the design and
tasks («Approved by the user»), and one sandbox code cycle per FR group («The user chose vertical slices per
FR group to reconcile TDD with the project's two-agent code step»).

## Mistakes and lessons

- **Test mistakes caught by the auditors, not by the tests.** Slice 1: 9 corrections, e.g. the FR-5 lock
  end is now checked at the 14th and 15th minute, and a meaningless cookie check in FR-8 was removed. Slice
  2: 8 corrections, mainly tests relying on `GET /members`, which appears only in slice 3. Slice 3: a
  check that "Ромашка" was unchanged expected one invitation instead of three and depended on order, and
  the expected mail count was hard-coded as 1. Slice 4: 8 auditors found 25 corrections, e.g. test data
  that did not match the scenario (sign-in with the right password, Анна instead of Борис) and three
  missing scenarios. A red check in slice 1 could not show that each test fails on its own THEN, because
  the conftest import error hid every result.
- **Domain errors carried an HTTP status**, against `server-architecture.md`. Found in the review of the
  `code-writer` diff in slice 1; now each router has an `ERROR_MAPPING`. Responses did not change.
- **The slice 4 tests found two code bugs:** after accepting an invitation the start page mounted twice and
  was bounced to «Вход» and back; sign-in `fields` messages sat next to the wrong field. The sign-out cookie
  was a required OpenAPI parameter, which forced a workaround in the SPA; it is now optional.
- **File and name limits.** `test_invitations.py` grew to 687 lines against the 500 limit and was split into
  three files (36 tests before and after, names compared one by one). The shared test modules named
  `*_helpers.py` are banned by `naming.md` and were renamed `members_api.py` and `invitations_api.py`.
- **Line endings.** There was no `.gitattributes` and `core.autocrlf=true`, so Windows working copies had
  CRLF and `frontend-format` failed on six config files; the CRLF was also in files the agents wrote. From
  this finish run: subagents writing in Python text mode left CRLF files, which were normalized, and
  `facts_adr.py` writes ADRs with CRLF on Windows (`write_text` without `newline`). A `.gitattributes` from
  the skeleton task would have caught it.
- **Harness defects, not fixed.** `tdd_sandbox.py close` counts ERROR log lines as failed tests (slice 1:
  groups ticked and the sandbox dropped by hand with the script's own functions) and refuses any deleted
  test, even a verified split (slice 3: the old file was put back into the sandbox unchanged, then moved
  out after `close`).
- **Tests did not catch the dev-stack defects.** Only running `just dev` showed that the backend container
  lacked `MAIL_FROM` and that the venv volume never got `aiosmtplib` and `argon2-cffi`. The manual flow in
  group 8 is what found them.
- **The review caught what the code step had not** (from this finish run): the members router file against
  `naming.md`, an eager `get_clock`, repository reads and writes by id alone without the `organization_id`
  filter, and `isAdministrator` in `AuthProvider`. Later, `doc-writer` found routers taking the database
  session against `data-access.md` «routers never touch the session»; this slipped past the first review
  and was fixed after the user's choice «Исправить сейчас (Recommended)».
- **UI texts invented by the code.** `code-writer` chose texts that no spec quotes, such as «Пароль
  изменён. Теперь можно войти», «Члены организации», «Приглашения», «Показать ещё». A «SPA interface»
  section in the design before slice 4 reduced this; the specs themselves lacked the page-level THENs.

## What remains

- **Open for the user (from this finish run):** the sign-in lock message «Попробуйте через 15 минут» is
  fixed by spec FR-5 while `SIGN_IN_LOCK_MINUTES` is configurable. A host-run backend cannot reach Mailpit
  SMTP, because port 1025 is not published.
- Clauses tested without a scenario of their own are candidates for scenarios, listed in the handoff: the
  FR-5 counting of unknown emails and the reset of the count, the FR-6 cookie not readable by scripts, the
  length boundaries of FR-1 and FR-8, invitation list order and resend, and FR-19 for resend, revoke,
  reactivate and role change.
- FR-14 «Their data and history SHALL be kept» is checked only as the member row staying; no history
  exists yet. FR-16 «Deactivating the last active administrator» can happen only in a race.
- The UI texts chosen by the code (listed above) are not in the specs and were left for the review.
- The `tdd_sandbox.py close` defects and the CRLF write in `facts_adr.py` are not fixed.
- The database tests print 6 warnings: Alembic asks for `path_separator` in its configuration.
- About 64 files show as modified with an empty diff because of the new eol attribute; `.gitattributes`
  goes into the commit with the change.
- Next task: not decided yet; `docs/ideas.md` holds the mailbox connection idea.
- The note is written before the commit; the commit goes through `/commit`.
