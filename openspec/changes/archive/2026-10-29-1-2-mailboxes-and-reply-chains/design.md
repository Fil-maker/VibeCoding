# Design

## Context

After task 1.1 the backend has the modules `accounts`, `auth` and `health`, a `user_id`-only
`AuthContext`, no background work and no mail reading (`docs/architecture.md`). Rules that shape this
change: the mail reader only reads and is reached through a dependency factory
(`.claude/rules/server-architecture.md`); no network call inside an open transaction, owner filter on
every query (`.claude/rules/data-access.md`); emails are kept until their mailbox or user is deleted
(`.claude/rules/database.md`); tests use no network and fake the mailbox (`.claude/rules/testing.md`).
User decisions of this change: background reading after connect, every 5 minutes and on «Обновить»;
Inbox and Sent of the last 12 months; disconnect keeps the emails; GreenMail for the demo mailboxes.

## Goals / Non-Goals

**Goals:**
- A reader that cannot change a mailbox: no code path issues a command that writes to the server.
- Reading that survives a restart: what is due is decided from the database, never from memory.
- Deterministic chain joining: the same emails give the same chains whatever order they are read in.

**Non-Goals:**
- Placement of chains in projects (task 1.3); counterparties as entities (only addresses for now).
- Parallel reading of many mailboxes at once; one backend process reads one mailbox at a time.

## Decisions

### Modules

- `mailboxes` — connecting, listing, refreshing, disconnecting mailboxes and the reading run
  (`read_due_mailboxes`). It stores emails through the `correspondence` service.
- `correspondence` — emails, their copies in folders and reply chains; `domain.py` holds the pure parts:
  parsing a raw message into a `ParsedEmail` and the HTML-to-text conversion.
- `platform/mail_reader.py` — `MailReader` protocol, `ImapMailReader`, `FakeMailReader`, `get_mail_reader`.
- `platform/secret_box.py` — encryption of mailbox passwords.
- `platform/pagination.py` — `Page[T]` and keyset cursors, back from task 0.2.

Alternative: one `mail` module for both. Rejected: the chains are the input of task 1.3 and must not
depend on how a mailbox is reached.

### IMAP client: the standard library in a worker thread

`imaplib.IMAP4_SSL` (or `IMAP4` for a host listed in `IMAP_INSECURE_HOSTS`) runs in
`asyncio.to_thread` with a socket timeout. Folders are opened with `select(folder, readonly=True)` and
messages fetched with `UID FETCH <uids> (BODY.PEEK[] FLAGS)`, so the `\Seen` flag is never set.
`ImapMailReader` exposes only `check` and `fetch`; it never calls `store`, `copy`, `move`, `expunge`,
`append` or `delete`. Its IMAP connection comes from a factory argument, so a unit test records the
commands sent and asserts that only `LOGIN`, `LIST`, `SELECT … readonly`, `UID SEARCH`, `UID FETCH`
with `BODY.PEEK` and `LOGOUT` occur.

Alternative: `aioimaplib`. Rejected: a new dependency for no gain at one mailbox at a time.

### Folders and incremental reading

Inbox is `INBOX`. Sent is the folder with the `\Sent` special-use attribute from `LIST`, else the first
existing of «Sent», «Sent Items», «Отправленные», «INBOX.Sent». For each mailbox folder the app keeps
`uidvalidity` and `last_uid`. A read fetches `UID SEARCH UID <last_uid+1>:* SINCE <today − depth>`;
the first read takes everything since the depth. When `uidvalidity` changes the folder is read again
from the depth, and duplicates fall away by the email key (FR-28). Messages are fetched in batches of 50,
each batch stored in its own transaction, so a long first read shows progress and a failure keeps what
was stored.

### Background reading (user decision)

`create_app` starts one asyncio task in the lifespan, `run_reading_loop`, when
`MAILBOX_READING_ENABLED` is true. Every `MAILBOX_READ_TICK_SECONDS` it calls
`read_due_mailboxes(...)`, which reads, one by one, the connected mailboxes that are due:
`read_requested_at` is set (after connect and «Обновить») or the last attempt is older than
`MAILBOX_READ_INTERVAL_MINUTES`. A mailbox is claimed in a short transaction with `FOR UPDATE SKIP
LOCKED` and its status set to `reading`; the network read happens outside any transaction. A `reading`
status older than 15 minutes counts as abandoned and is due again, which covers a restart mid-read.
The loop logs and swallows errors, never stops.

Alternatives: a separate worker service, or a task queue. Rejected for now: a new service for one
loop; the database-driven claim lets a separate worker take over later without a schema change.

### Connect check

`connect` validates the input, then calls `MailReader.check` outside any transaction (timeout
`IMAP_TIMEOUT_SECONDS`), then inserts in one transaction. A race of two equal connects ends on the
unique constraint as `mailbox_exists`. Reconnecting a disconnected mailbox (same user, server, login)
reuses its row: new password, status `pending`, `read_requested_at` set; the folders keep `last_uid`, so
no email comes twice (FR-27).

### Password encryption

Fernet (`cryptography`) with `MAILBOX_ENCRYPTION_KEY` from `.env`; the ciphertext is stored, the
plaintext lives only in memory during a check or a read. Disconnecting sets the ciphertext to NULL.
Alternative: PostgreSQL `pgcrypto`. Rejected: the key would travel in SQL parameters and query logs.

### Email identity and chain joining

The email key is the normalized `Message-ID` (angle brackets and spaces stripped, lower case), else
`no-id:<mailbox_id>:<folder_id>:<uidvalidity>:<uid>`. `(user_id, key)` is unique; another copy only adds
an `email_copies` row. Joining, inside the batch transaction: the set of related keys is the email's
`In-Reply-To` and `References` plus the keys of stored emails whose `References`/`In-Reply-To` name this
email. All chains of the related stored emails and the new email become one chain: the chain with the
oldest `created_at` (ties: smallest id) survives, the others' emails move to it and the others are
deleted. The user's chain rows are locked (`FOR UPDATE`) in id order before a merge. The result does not
depend on the reading order.

### Text of an email

`text/plain` part first; otherwise the HTML part converted to text by the standard `html.parser` with
`script` and `style` dropped and entities decoded; charsets by the declared charset with replacement of
undecodable bytes. The text is cut at 200 000 characters. Attachments: only file names. Addresses and
names from `From`, `To`, `Cc`, decoded RFC 2047. The date: `Date` header, else the server's
`INTERNALDATE`, stored in UTC.

### Participants

A chain's participants are the distinct addresses of `From`, `To`, `Cc` of its emails minus the user's
own addresses: the logins of all of the user's mailboxes (connected or not) and the account email. The
`correspondence` service gets them through the `mailboxes` and `accounts` repositories.

### Data model (revision `0004`)

| Table | Columns | Keys and indexes |
|---|---|---|
| `mailboxes` | `id`, `user_id`, `server` (≤253), `port`, `login` (≤254), `password_encrypted` (null when disconnected), `status` (`pending`, `reading`, `read`, `failed`), `error_code` (null, `sign_in_failed`, `unreachable`, `read_failed`), `read_requested_at`, `last_attempt_at`, `last_read_at`, `connected_at`, `disconnected_at`, `created_at` | unique `(user_id, server, login)`; `user_id` → `users` cascade |
| `mailbox_folders` | `id`, `mailbox_id`, `kind` (`inbox`, `sent`), `name`, `uidvalidity`, `last_uid` | unique `(mailbox_id, kind)`; cascade from `mailboxes` |
| `reply_chains` | `id`, `user_id`, `latest_email_at`, `created_at` | index `(user_id, latest_email_at desc, id)`; cascade from `users` |
| `emails` | `id`, `user_id`, `chain_id`, `key` (≤998), `message_id`, `in_reply_to`, `references` (text[]), `subject`, `from_address`, `from_name`, `to_addresses` (jsonb list of `{address, name}`), `cc_addresses` (jsonb), `sent_at`, `text`, `attachment_names` (text[]), `created_at` | unique `(user_id, key)`; index `(chain_id, sent_at, id)`; GIN on `references`; cascade from `users` and `reply_chains` |
| `email_copies` | `id`, `email_id`, `mailbox_id`, `folder_id`, `uid` | unique `(folder_id, uid)`; cascade from `emails` and `mailboxes` |

Statuses and error codes are `StrEnum`s; the jsonb address lists have a pydantic schema. Disconnecting
never deletes a `mailboxes` row, so the emails and copies stay (user decision).

### Settings

| Env var | Default | Meaning |
|---|---|---|
| `MAILBOX_ENCRYPTION_KEY` | required | Fernet key for mailbox passwords |
| `MAILBOX_READING_ENABLED` | `true` | Start the background loop (tests: `false`) |
| `MAILBOX_READ_INTERVAL_MINUTES` | `5` | Scheduled read interval |
| `MAILBOX_READ_TICK_SECONDS` | `10` | How often the loop looks for due mailboxes |
| `MAILBOX_READ_DEPTH_DAYS` | `365` | How far back a first read goes |
| `IMAP_TIMEOUT_SECONDS` | `30` | Socket timeout of a check and a read |
| `IMAP_INSECURE_HOSTS` | empty | Comma-separated hosts reached without TLS (compose: `greenmail`) |

### Demo mail server (user decision)

`greenmail` service in `docker-compose.yml` (image `greenmail/standalone`, pinned tag), IMAP 3143 and
SMTP 3025 inside the network, IMAP also on the host for the seeding script; two users
`anna@demo.test` and `anna.work@demo.test` with passwords from `.env.example`
(`DEMO_MAIL_PASSWORD`). `just demo-mail` runs `scripts/demo_mail.py`, which APPENDs the prepared
messages of `docker/greenmail/demo/*.eml` into Inbox and Sent, some without `\Seen`, with dates shifted
so that the newest email is yesterday. It does nothing when the Inbox is not empty. The correspondence:
three projects («Ремонт офиса», «Поставка оборудования», «Конференция»), about 40 emails, five
counterparties, replies across the two mailboxes and one email in both. The script is a dev tool
outside `backend/app`; the app itself has no code that writes to a mailbox. GreenMail keeps mail in
memory: after a restart run `just demo-mail` again.

## Interface

The public contract for tests and code. Paths are under `/api/v1`; every route needs a signed-in user
(else 401 `not_signed_in`); state-changing routes need a matching `Origin` (else 403
`forbidden_origin`). Another user's id answers 404 `not_found`.

### Schemas

- `Mailbox`: `{id: uuid, server: str, port: int, login: str, status: "pending" | "reading" | "read" | "failed", error: str | null, last_read_at: datetime | null}` — `error` is the Russian reason of FR-26
- `MailboxConnect` (request): `{server: str 1–253, port: int 1–65535 = 993, login: str 1–254, password: str 1–256}`
- `Address`: `{address: str, name: str | null}`
- `ReplyChainSummary`: `{id: uuid, subject: str, participants: Address[], email_count: int, latest_email_at: datetime}`
- `EmailView`: `{id: uuid, sender: Address, to: Address[], cc: Address[], sent_at: datetime, subject: str, text: str, attachment_names: str[]}`
- `ReplyChain`: `{id: uuid, subject: str, participants: Address[], emails: EmailView[]}` — oldest first, at most 500
- `Page[T]`: `{items: T[], next_cursor: str | null}`; query `limit` 1–100 (default 50), `cursor`

### Routes

| Route | Body | Success | Errors |
|---|---|---|---|
| `GET /mailboxes` | — | 200 `Mailbox[]`, connected only, by login | — |
| `POST /mailboxes` | `MailboxConnect` | 201 `Mailbox` (`pending`) | 409 `mailbox_exists`, 422 `mailbox_sign_in_failed`, 422 `mailbox_unreachable`, 422 `validation_failed` |
| `POST /mailboxes/{id}/refresh` | — | 202 `Mailbox` | 404 `not_found` |
| `DELETE /mailboxes/{id}` | — | 204 | 404 `not_found` |
| `GET /reply-chains` | — | 200 `Page[ReplyChainSummary]`, latest email first | 400 `invalid_cursor` |
| `GET /reply-chains/{id}` | — | 200 `ReplyChain` | 404 `not_found` |

A disconnected mailbox answers 404 to refresh and delete.

### Error messages (Russian, exact)

| Code or status error | Message |
|---|---|
| `mailbox_exists` | «Этот ящик уже подключён» |
| `mailbox_sign_in_failed` | «Не удалось войти в ящик: проверьте логин и пароль приложения» |
| `mailbox_unreachable` | «Не удалось подключиться к серверу <server>» |
| status `sign_in_failed` | «не удалось войти в ящик, подключите его заново с новым паролем приложения» |
| status `unreachable` | «сервер не отвечает» |
| status `read_failed` | «не удалось прочитать письма» |
| field messages | «Укажите сервер IMAP», «Укажите логин», «Укажите пароль приложения», «Порт должен быть от 1 до 65535» |

### Service functions used by tests

- `app.modules.mailboxes.service.read_due_mailboxes(database: Database, reader: MailReader, clock: Clock, settings: Settings) -> int` — reads every due mailbox once, returns how many were read; the loop calls it, tests call it directly.

### Platform interface

- `MailReader` protocol: `async check(credentials: ImapCredentials) -> None`, raises `MailboxSignInFailed` or `MailboxUnreachable`; `async fetch(credentials, folder: FolderKind, since: date, after_uid: int | None, uidvalidity: int | None) -> FolderBatch` with `uidvalidity` and a list of `RawMessage(uid: int, data: bytes, internal_date: datetime)`.
- `ImapCredentials(server: str, port: int, login: str, password: str, use_tls: bool)`; `FolderKind` = `inbox` | `sent`.
- `FakeMailReader`: `add(login, folder, raw: bytes, *, seen: bool = False) -> int` (uid), `seen_flags(login, folder) -> dict[int, bool]`, `fail_sign_in(login)`, `make_unreachable(server)`, `restore(server)`; never changes a flag on fetch.
- `ImapMailReader(timeout: float, connect: Callable[[str, int, bool, float], imaplib.IMAP4] = default)`.
- `get_mail_reader(request) -> MailReader`, lazy, overridden in tests.
- `SecretBox(key: str)`: `encrypt(str) -> bytes`, `decrypt(bytes) -> str`; `get_secret_box`.

### SPA pages

- Start page: links «Почтовые ящики» (`/mailboxes`) and «Переписка» (`/chains`) beside the name and «Выйти».
- «Почтовые ящики»: the list (login, server, status «Ожидает чтения» / «Читается…» / «Прочитан 29.10.2026, 14:05» / «Ошибка: <reason>»), buttons «Обновить» and «Отключить» per mailbox, the confirmation «Отключить ящик <login>? Прочитанные письма останутся.» with «Отключить» and «Отмена»; empty: «Ящики ещё не подключены». Form «Подключить ящик»: «Сервер IMAP», «Порт», «Логин», «Пароль приложения», button «Подключить». The list refreshes every 5 seconds while a mailbox is pending or reading.
- «Переписка» (`/chains`): rows of subject, participants, «N письмо/письма/писем» (Intl plural rules), date `dd.mm.yyyy`; «Показать ещё» for the next page; empty: «Писем пока нет: подключите почтовый ящик».
- Chain (`/chains/:id`): the subject, then each email with «От», «Кому», «Копия», the date and time, the text as plain text with line breaks kept, «Вложения: <names>»; unknown id: «Страница не найдена».

### Test seams

- `get_mail_reader` → `FakeMailReader`; `get_clock` → the settable clock; `MAILBOX_READING_ENABLED=false`
  in tests, which call `read_due_mailboxes` after the clock moves.
- Raw test emails are built with the standard `email.message.EmailMessage` in a factory
  `backend/tests/mail_factory.py`: subject, from, to, cc, date, message id, in-reply-to, references,
  plain or HTML body, attachments.
- `ImapMailReader` is unit-tested with a recording fake connection (FR-25), no network.

## Risks / Trade-offs

- [A big mailbox makes the first read long] → batches of 50 in their own transactions, status
  «Читается», the 12-month depth.
- [Chains merge later, after task 1.3 placed both] → 1.3 must define what a merge does to placements;
  noted in its design.
- [The encryption key is lost or changed] → every mailbox shows «Ошибка: не удалось войти в ящик…» and
  is reconnected; key rotation is a later idea.
- [The loop runs in every backend process] → `SKIP LOCKED` claims make two processes safe.
- [Servers differ in folder names] → special-use first, then known names; other folders are skipped.
- [GreenMail loses mail on restart] → `just demo-mail` refills it.

## Migration Plan

Revision `0004` only creates the five tables; existing users, sessions and tokens are untouched.
Downgrade to `0003` drops them, losing the read correspondence and connected mailboxes; nothing else
changes. A new required env var `MAILBOX_ENCRYPTION_KEY` goes to `.env.example`, `docs/tech.md` and the
compose overrides; the app fails at start without it.
