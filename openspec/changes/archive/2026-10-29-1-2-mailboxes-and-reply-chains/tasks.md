# Tasks

One code cycle (`.claude/skills/feature/code-step.md`) per slice, each with its own sandbox, red check
and `close`: groups 1–3 (platform, schema, FR-22…FR-27), group 4 (FR-28…FR-31), group 6 (SPA). Group 5
(the demo mail server) has no scenario tests and is checked by hand. `test-writer` writes the slice's
tests from the brief; `code-writer` writes the slice's groups. Tests sit only at the seams of design
«Test seams»: the HTTP API, `read_due_mailboxes`, the public `platform` functions, the migration chain,
the SPA components. Implementation docs are updated at `/finish` through `/document`; product docs in
group 7.

## 1. Platform and setup

- [x] 1.1 Add `cryptography` to `backend/pyproject.toml` and `uv.lock` with a pinned range — check - `uv sync --directory backend` succeeds
- [x] 1.2 Settings of design «Settings» in `platform/settings.py`, `.env.example` lines (with how to generate the Fernet key), compose overrides for the backend (`IMAP_INSECURE_HOSTS=greenmail`, `MAILBOX_ENCRYPTION_KEY`) — check - a unit test shows the defaults and that a missing `MAILBOX_ENCRYPTION_KEY` fails at build
- [x] 1.3 `platform/secret_box.py`, `platform/pagination.py`, `platform/mail_reader.py` (`MailReader`, `ImapCredentials`, `FolderKind`, `RawMessage`, `FolderBatch`, `ImapMailReader`, `FakeMailReader`, `get_mail_reader`) per design «Platform interface» — check - unit tests: encrypt/decrypt round trip and a wrong key refused; the cursor round trip and a broken cursor refused; `ImapMailReader` against a recording fake connection sends only `LOGIN`, `LIST`, read-only `SELECT`, `UID SEARCH`, `UID FETCH … BODY.PEEK[]`, `LOGOUT` (FR-25) and maps a login failure and a timeout to `MailboxSignInFailed` and `MailboxUnreachable`; the fake keeps flags on fetch

## 2. Schema

- [x] 2.1 Models of design «Data model» in `mailboxes` and `correspondence` and the revision `0004` — check - `alembic upgrade head`, `alembic downgrade 0003`, `alembic upgrade head` and `alembic check` succeed against the test database
- [x] 2.2 Test helpers: `backend/tests/mail_factory.py` (raw emails per design «Test seams») and a factory in `backend/tests/factories.py` that connects a mailbox through the API with the fake reader — check - used by the scenario tests of groups 3 and 4

## 3. Mailboxes (FR-22…FR-27)

- [x] 3.1 `mailboxes` module: connect with the check outside the transaction, list, refresh, disconnect, reconnect reusing the row; `read_due_mailboxes` with the `SKIP LOCKED` claim, incremental folders, batches, statuses and error codes; `run_reading_loop` started in the lifespan when enabled — routes, errors and texts of design «Interface» — check - the FR-22…FR-27 scenario tests pass
- [x] 3.2 Scenario tests for FR-22…FR-27 (`test-writer`, sandbox): integration tests through the HTTP API and `read_due_mailboxes` with `FakeMailReader` and the settable clock; Вера against Анна's mailbox ids on refresh and disconnect; no answer contains the app password; unread flags of the fake unchanged after a read — check - red before the code, green after `tdd_sandbox.py close`

## 4. Reply chains (FR-28…FR-31)

- [x] 4.1 `correspondence` module: `domain.py` parsing (headers, RFC 2047, charsets, plain or HTML-to-text, attachment names, the email key), storing with copies, chain joining and merging per design «Email identity and chain joining», participants, `GET /reply-chains` with keyset pages and `GET /reply-chains/{id}` — check - the FR-28…FR-31 scenario tests and the domain unit tests pass
- [x] 4.2 Scenario tests for FR-28…FR-31 (`test-writer`, sandbox): an email in two mailboxes, the same email for two users, a reply from another mailbox, a reply read before its original, an email joining two chains, the same subject without headers, the list order and counts, an HTML-only email with a script, Вера against Анна's chain id; unit tests of the parsing next to `domain.py` — check - red before the code, green after `close`

## 5. Demo mail server

- [x] 5.1 `greenmail` service in `docker-compose.yml` with a pinned tag and the two demo users; `DEMO_MAIL_PASSWORD` in `.env.example` — check - `docker compose config` is valid and `docker compose up -d greenmail` accepts an IMAP login of `anna@demo.test`
- [x] 5.2 About 40 prepared emails in `docker/greenmail/demo/` (three projects, five counterparties, replies across the two mailboxes, one email in both, some unread) and `scripts/demo_mail.py` with `just demo-mail` (load, skip when not empty, dates shifted to end yesterday) and `just demo-mail status` (count and unread per folder) — check - after `just demo-mail` the status shows both mailboxes filled; a second run adds nothing

## 6. SPA

- [x] 6.1 `just api-client`; routes `/mailboxes`, `/chains`, `/chains/:id` behind `RequireUser`; the pages of design «SPA pages» with the exact Russian texts; links from the start page — check - `pnpm --dir frontend lint`, `typecheck`, `build` pass and the client freshness check in `just check` passes
- [x] 6.2 Component tests (`test-writer`, sandbox): the connect form and its error texts, the statuses, «Обновить», the disconnect confirmation, the chains list with plural counts and «Показать ещё», the chain page as plain text, an unknown chain → «Страница не найдена», the empty texts — check - red before the code, green after `close`

## 7. Product docs

- [x] 7.1 `docs/domain.md`: «Data and privacy» — the mailbox password is stored encrypted and deleted on disconnect, Inbox and Sent of 12 months are read, emails stay after disconnect; glossary terms Email copy and Participant if used; requirements map and «Last FR number: FR-31» at archive — check - `just check` doc facts pass
- [x] 7.2 `docs/ideas.md`: remove «Mailbox connection» and «Reply chains» (now task 1.2); add the deferred items of proposal «Out of scope» (OAuth, more folders and depth, attachments' content and search, deleting a disconnected mailbox's emails, key rotation) — check - the entries exist and nothing stale is linked

## 8. Verification

- [x] 8.1 `just check` passes — check - all PASS
- [x] 8.2 `/test` with `all` passes — check - backend unit, backend database and frontend suites report counts, none NOT PRESENT
- [x] 8.3 Manual flow 1 (`flow-checker`, preview + GreenMail after `just demo-mail`): sign up a throwaway `flow-1-2-mailboxes@example.test`, connect `greenmail`:3143 `anna@demo.test` with a wrong password → the error text, then with the right one → «Ожидает чтения», then «Прочитан …»; connect `anna.work@demo.test` — check - its PASS report
- [x] 8.4 Manual flow 2: «Переписка» lists chains newest first; the email present in both mailboxes appears once; a chain with replies from both mailboxes opens with its emails in order and the attachment name; `just demo-mail status` shows the same unread counts as before the read — check - its PASS report
- [x] 8.5 Manual flow 3: append one new email to `anna@demo.test` with the demo script, press «Обновить» → it appears in its chain; disconnect `anna.work@demo.test` with the confirmation → gone from the list, its emails still in «Переписка» — check - its PASS report; test data cleaned up

## 9. Done when

- [x] 9.1 The user connects two mailboxes, and a wrong password is reported — check - 8.3 and the FR-22 tests
- [x] 9.2 After reading, the user sees the reply chains of all mailboxes and opens one to read its emails; an email present in both mailboxes is shown once; unread emails stay unread in the mailbox — check - 8.4 and the FR-25, FR-28…FR-31 tests
- [x] 9.3 A new email in the mailbox appears after «Обновить» or within 5 minutes — check - 8.5 and the FR-24 tests
- [x] 9.4 A disconnected mailbox is no longer read, and its emails stay — check - 8.5 and the FR-27 tests
- [x] 9.5 `just demo-mail` fills the demo mailboxes with prepared correspondence — check - 5.2 and 8.3
- [x] 9.6 `just check` and `just test-all` pass — check - 8.1 and 8.2

## Workflow follow-up

- `/finish 1.2`: invariant review, `openspec archive 1-2-mailboxes-and-reply-chains --yes`, `/document` (architecture «Components and processes», «Repository structure», «Layers», «Data model», «Routes and API», «Deploy», «Security»; tech «Stack», «Environment variables»; a guide article on mail reading), `/journal`, `/commit` with `feat:`.
