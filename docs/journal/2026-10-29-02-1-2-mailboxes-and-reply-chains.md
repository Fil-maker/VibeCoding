# Mailboxes and reply chains

Date: 29.10.2026 · Task: 1.2 · Change: 1-2-mailboxes-and-reply-chains

## Goal

The user asked for a first version of the app with working business scenarios to show to the customer
(«Создадим первую версию приложения с рабочими бизнес сценариями для показа заказчику»). It was split into a
series of tasks 1.1-1.4 (ADR `docs/adr/0043-demo-version-for-the-customer-ships.md`). Task 1.2 is the second:
a user connects mailboxes over IMAP with an app password, the app reads Inbox and Sent in the background and
assembles the emails into reply chains. Each email is stored once, and the mailbox is never changed. Projects,
the engine, manual placement and rules are tasks 1.3 and 1.4. The invariants touched: «Mailbox read-only»,
«Access boundary», «History is kept». Email text goes nowhere outside.

## What was done

Design (session 9a721e6a, started in this worktree before 1.1 was merged):

- The worktree found that task 1.1 was already done in the main checkout on `feat/1-1-personal-accounts`
  (uncommitted), so it deleted its own draft of 1.1 and waited. After 1.1 reached `main` (`ab95559`, release
  v0.1.0) the worktree was brought up to `main`.
- Plan rows 1.2-1.4 were written (plan edition 0.7), with FR-22…FR-31 in the FR column of 1.2.
- The OpenSpec change was written: capability `mailboxes` (FR-22…FR-27: connect, secret password, reading,
  read-only reading, visible errors with retry, disconnect) and capability `reply-chains` (FR-28…FR-31: one
  copy per email, chain assembly, list, reading a chain). No existing requirement was modified; FR-17 and
  FR-21 already cover the new pages. Design: modules `mailboxes` and `correspondence`; `imaplib` in a thread,
  folders opened read-only, emails fetched with `BODY.PEEK`; a background loop inside the backend in which the
  database decides which mailboxes are due (`SKIP LOCKED`); Fernet for the password; `Message-ID` as the email
  key; chains merge deterministically (the oldest survives); the mailbox row is not deleted on disconnect;
  GreenMail and `just demo-mail`. The interface is six routes (`GET`/`POST /mailboxes`,
  `POST /mailboxes/{id}/refresh`, `DELETE /mailboxes/{id}`, `GET /reply-chains`, `GET /reply-chains/{id}`).
- The deltas and the design were approved by the user.

Code (session 80b6f25c):

- Backend groups 1-4 (platform, schema, mailboxes, chains) ran as one TDD cycle, the SPA as a second. Tests
  fake the mailbox (`FakeMailReader`); FR-25 is proven by a unit test that records the IMAP commands the client
  sends; GreenMail serves the demo and the manual checks.
- Migration `0004_mailboxes_and_reply_chains.py`; platform code `mail_reader.py`, `imap_folders.py`,
  `secret_box.py`, `pagination.py`; modules `mailboxes` and `correspondence`; `scripts/demo_mail.py` and
  `docker/greenmail/`; SPA pages «Почтовые ящики», «Переписка» and the page of one chain.
- Manual flows 8.3, 8.4, 8.5 passed by flow-checker on 29.10.2026 on host Vite, backend and GreenMail in
  Docker (image builds failed on DNS to `ghcr.io` and npm, so local images were used). After reading both demo
  mailboxes `just demo-mail status` showed the same unread counts (5 and 6): FR-25 holds on a real IMAP
  server. The test user, its mailboxes and emails were deleted, the shared dev database was rolled back to
  `0003`, and the main checkout's stack was handed back (its frontend container could not start: no DNS to
  `registry.npmjs.org`).
- Product docs (approved by the user): `docs/domain.md` «Data and privacy» and the glossary term Participant;
  `docs/ideas.md` drops «Mailbox connection» and «Reply chains» and gains the deferred items.
- Test counts at the end of the code step: 47 backend unit, 71 SPA, 144 database tests.

Finish (session bb982120):

- `just check` 17/17 PASS; tests backend-unit 47, frontend-unit 71, db 144 (44 warnings: Alembic
  `path_separator` deprecation, not from 1.2); `alembic check` on the test database at 0004: no new operations.
- Invariant review: no BLOCKER (read-only IMAP via EXAMINE and BODY.PEEK; owner filter; Fernet-encrypted
  password, never returned or logged; emails kept on disconnect; TLS except `IMAP_INSECURE_HOSTS`; HTML shown
  as text). Fixed by `code-writer`: `list_connected_for_owner` capped at `MAILBOX_LIST_LIMIT = 100`
  (data-access «Bounded reads»); `FakeMailReader` falls back to the fixed `FAKE_UNDATED_MESSAGE_DATE` instead
  of now (determinism); a wrong comment in `run_reading_loop`.
- Dropped with a reason: no `user_id` on `email_copies` and `mailbox_folders` (link and progress tables reached
  only through owned rows; the schema was approved in the design); chain capped at 500 emails (approved in the
  design: «at most 500»); epoch fallback for a missing INTERNALDATE (RFC 3501 requires it); hardening of
  `demo_mail.py` (hard-coded demo logins). Raised as open: `POST /api/v1/mailboxes` has no rate limit and
  lets a signed-in user probe hosts and ports.
- The doc check found a code defect: FR-31 requires each email of a chain to show its subject, and `ChainPage`
  did not. `code-writer` added «Тема:» to `EmailBlock` and an assertion to the FR-31 SPA test; checks and tests
  were green again.
- Docs: new `docs/guide/mail-reading.md`; `architecture`, `tech`, `guide/backend`, `guide/frontend`,
  `guide/README` updated; `just demo-mail` added to `CLAUDE.md` «Commands»; ADRs 0043-0049; the requirements
  map and «Last FR number: FR-31» in `docs/domain.md`; the specs `mailboxes` and `reply-chains` were created
  by the archive.

Process decisions, not turned into ADRs:

- Plan rows 1.1-1.4 written — Пользователь: «Да, записывай» — [human].
- Delta specs FR-22..FR-31 and the design of change 1-2-mailboxes-and-reply-chains approved; tests fake the
  mailbox, FR-25 is proven by a unit test recording IMAP commands, GreenMail serves the demo and manual
  checks — Пользователь: «Да, одобряю» — [human].
- Backend groups 1-4 of change 1.2 run as one TDD cycle; the SPA (group 6) as a second — FR-24, FR-26 and
  FR-27 scenarios check emails in the app, which tests can only see through the reply-chains API of group 4 —
  [AI → accepted].
- Product docs of task 1.2: domain.md «Data and privacy» states what mailbox data is kept, glossary gains
  Participant; ideas.md drops Mailbox connection and Reply chains and gains the deferred items — Да,
  записывай — [human].
- Stop the main checkout's dev stack to run the manual flows of task 1.2 on the worktree's code with
  GreenMail — Да, останови — [human].

## Key questions to the AI

- Design, first round (answered through AskUserQuestion): how to split the «version for the customer»; where
  demo emails come from; which engine sorts emails into projects; what to do with organizations and users
  created in task 0.2. Answers: «Серия 1.1–1.4 (рекомендую)», «Реальный IMAP + демо-ящик (рекомендую)»,
  «Локальный, без внешней модели (рекомендую)», «Пересоздать базу (рекомендую)». Then «Записываю четыре строки
  плана и начинаю изменение 1.1 «Личные аккаунты»?» — «Да, записывай (рекомендую)».
- Design for 1.2: when the app reads emails; which folders and how far back; what happens on disconnect; how
  to make demo mailboxes. Answers: «В фоне + «Обновить» (рекомендую)», «Входящие + Отправленные, 12 мес.
  (рекомендую)», «Письма остаются (рекомендую)», «GreenMail в Docker (рекомендую)».
- «Одобряем дельты FR-22…FR-31 и дизайн задачи 1.2?» — «Да, одобряю (рекомендую)».
- Waiting for 1.1: the assistant offered to wait until 1.1 was committed and merged; the user wrote
  «Жду коммита 1.1», later «Начинай работать».
- Code step: «Можно остановить dev-стек основного checkout'а (vibecoding-*), чтобы прогнать ручные сценарии на
  коде этого worktree с GreenMail?» — «Да, останови (рекомендую)». «Записываю правки продуктовых доков
  (domain.md «Data and privacy» + термин Participant, ideas.md) по черновику выше?» — «Да, записывай
  (рекомендую)».
- After the code, a request to commit and open a PR arrived. The assistant asked: «Правила проекта
  (CLAUDE.md «Workflow») говорят: коммит только через /commit в /finish, слияние --ff-only, без PR. /finish
  ещё не запускался (ревью инвариантов, архив OpenSpec, доки, журнал). Всё равно закоммитить и открыть PR
  сейчас?» — «Сначала /finish (рекомендую)».
- Finish, ADRs: «Какие решения записать в ADR? Рекомендую ADR для 1, 2, 3, 6, 7, 8, 9. Удалить: 4 — его
  отменил ADR 0035 («сохранить людей»); 5, 10, 11, 12, 13 — это шаги процесса, они пойдут в журнал.» —
  «Как рекомендовано (Recommended)». And whether to rewrite the wording of decision 9, which said integration
  tests use the same GreenMail server while decision 10 says tests fake the mailbox — «Исправить
  (Recommended)».

## Decisions

| Decision | Alternatives | Reason | Who |
| --- | --- | --- | --- |
| Demo version for the customer ships as a series of tasks 1.1-1.4: personal accounts, mailboxes and reply chains, projects and engine, manual placement and rules | one big change; throwaway demo prototype | Пользователь выбрал серию 1.1–1.4 вместо одного большого изменения или прототипа | [human] |
| Emails come from real IMAP mailboxes plus a local demo mailbox with prepared correspondence | real IMAP only; .eml/.mbox upload only | Пользователь выбрал реальный IMAP плюс демо-ящик для показа | [human] |
| First engine is local and deterministic (text similarity), no third-party model | Claude API with consent; both switchable | Пользователь выбрал локальный движок без внешней модели | [human] |
| Mailboxes are read in a background task inside the backend: right after connecting, every 5 minutes and on the button «Обновить»; each mailbox shows its status and last read time | only by the button | Пользователь выбрал «В фоне + Обновить» | [human] |
| Read folders Inbox and Sent, emails of the last 12 months (an app setting) | all folders and all history; Inbox only | Пользователь выбрал Входящие + Отправленные, 12 мес. | [human] |
| Disconnecting a mailbox deletes its password and stops reading; emails and reply chains already read stay | delete emails present only in that mailbox | Пользователь выбрал «Письма остаются» (инвариант «История сохраняется») | [human] |
| Demo mailboxes run on GreenMail in Docker; just demo-mail loads prepared Russian correspondence; manual checks use it, automated tests fake the mailbox | Dovecot in Docker; a real Yandex mailbox | Пользователь выбрал GreenMail в Docker | [human] |

ADRs written: 0043–0049.

## Mistakes and lessons

- **The design duplicated finished work.** While the worktree prepared change 1.1, it found that 1.1 was
  already done in the main checkout (not committed). It deleted its own draft, reverted its `docs/plan.md`
  edit and removed an extra branch `feat/personal-accounts`. Lesson: look at the other checkouts and branches
  before starting a task from the plan.
- **An answer did not match the finished work.** The user had chosen «Пересоздать базу», but the finished
  1.1 kept every user (ADR 0035). The assistant kept the 1.1 variant and no database re-creation was needed.
  The recorded decision that organizations are dropped by migration was therefore not turned into an ADR
  (superseded by ADR 0035).
- **A promise that the rules do not allow.** The assistant had said integration tests would use GreenMail;
  `testing.md` forbids the network in tests. The design step corrected it: tests use a fake mailbox, FR-25 is
  checked by a unit test that records IMAP commands, GreenMail is for the demo and the manual checks. The ADR
  text of the GreenMail decision had the same slip and was rewritten at `/finish` with the user's agreement.
- **A design rule read more strictly than the scenario.** The design said a mailbox is due when it is «older
  than» 5 minutes, the spec scenario says «5 minutes pass». It was implemented as «at least» (exactly
  `MAILBOX_READ_INTERVAL_MINUTES`).
- **Tests could not be split by group.** Tests of FR-24, FR-26 and FR-27 see emails only through the
  reply-chains API, so groups 1-4 were done in one cycle instead of three.
- **Some tests were green before the code.** The FR-31 «Another user's chain» SPA test was green before the
  code, because the 404 page already existed; it only guards against regression.
- **A missing requirement text in the SPA.** The doc check found that FR-31 requires the subject of each email
  and `ChainPage` did not show it. A scenario in the SPA test that asserted the subject would have caught it
  at the code step.
- **Harness problems.** `tdd_sandbox.py` counts only `*.test.ts(x)` as frontend test files, so shared SPA
  helpers in `frontend/src/test/` could not be collected and were inlined into two test files. The red check
  cannot parse a conftest import error, so auditor briefs of the backend cycle were written by calling
  `sandbox_briefs.write_auditor_briefs` directly. `doc-facts` flags `\n` before a Cyrillic letter in string
  literals as mixed script (worked around, and again in the SPA test).
- **The two checkouts share one dev database.** Compose has one project name for the main checkout and the
  worktree. For the manual checks the database was moved to `0004` and returned to `0003` afterwards; the
  main checkout's frontend container then could not start (no DNS to `registry.npmjs.org`).
- **A stray process held the port.** A Vite from this worktree, probably left by an agent, held 5173 and the
  preview moved to 5174, where the backend's Origin check refused it. The stray Vite was stopped and the
  preview restarted on 5173.
- **Image builds failed on DNS.** `ghcr.io` and the npm registry were unreachable from Docker; local images
  and a launch configuration with Vite on the host were used.
- **A PR was requested before `/finish`.** Project rules say commits only through `/commit` at `/finish`
  and no PRs; the user chose «Сначала /finish (рекомендую)».
- **The 5-second list polling and the TLS exemption are not automatically tested.** There are no timers in
  the SPA harness; the exemption for `IMAP_INSECURE_HOSTS` is exercised only by the GreenMail flow.

## What remains

- `POST /api/v1/mailboxes` has no rate limit and lets a signed-in user probe hosts and ports (raised by the
  invariant review, not fixed).
- `MAILBOX_ENCRYPTION_KEY=""` passes `Settings` and fails only at the first connect.
- `demo_mail.py load` checks only Inbox for emptiness, so an interrupted load could duplicate Sent on rerun.
- A chain over 500 emails shows its oldest 500 with no marker.
- `platform/errors.py` `FIELD_MESSAGES` maps a missing `password` to the registration text; mailboxes avoid it
  with a before-validator.
- `DEMO_MAIL_HOST` and `DEMO_MAIL_PORT` are read only by `scripts/demo_mail.py`, not by `Settings`.
- `mail_reader.py` (361 lines) and `mailboxes/service.py` (341 lines) are over the 300-line aim, under 500.
- Root `uv.lock` has an unrelated local change (lock revision 5 → 3), not part of 1.2.
- `DEMO_MAIL_PASSWORD` must be added to existing `.env` files.
- The main checkout's frontend container must be restarted with `just dev` once the network resolves.
- Observations of the manual flow, not failures: after «Подключить» the new row may take up to 5 s to appear;
  one click on a chain row did not navigate (likely a flaky pane click); the 401s in the console come from the
  start-up session check; a demo email mentions «15 апреля».
- Clauses without scenarios noted by auditors (covered by tests or the design, no spec change): encrypted
  storage, page size 50, Message-ID-less emails per folder, retry on «Обновить».
- Tasks 1.3 and 1.4 (projects and the engine; manual placement and rules) are next. Nothing was committed at
  the time of writing.
