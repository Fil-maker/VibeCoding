# Mail reading

Updated 05.11.2026

**Code:** `backend/app/modules/mailboxes/`, `backend/app/modules/correspondence/`, the platform files
`backend/app/platform/mail_reader.py`, `imap_folders.py`, `secret_box.py` and `pagination.py`, the migrations
`backend/migrations/versions/0004_mailboxes_and_reply_chains.py` and `0009_email_attachments.py`, the attachments module
`backend/app/modules/attachments/`, the tests `backend/app/platform/test_mail_reader.py`, `test_mail_reader_fetch_message.py` and
`test_secret_box.py`, `backend/tests/integration/` and `backend/tests/mail_factory.py`.

**Requirements:** [FR-22 … FR-27](../../openspec/specs/mailboxes/spec.md) mailboxes (connect, password, reading,
read-only access, failed reads, disconnect), [FR-53 … FR-54](../../openspec/specs/mailboxes/spec.md) connection hints (the
service picked from the address, the steps to connect it), [FR-28 … FR-31](../../openspec/specs/reply-chains/spec.md) reply chains
(stored once, joining, the list, reading a chain), and [FR-57 … FR-58](../../openspec/specs/reply-chains/spec.md) attachments
(the download on click, an attachment that cannot be fetched). The map is in [Requirements map](../domain.md#requirements-map).

**Design:** [Components and processes](../architecture.md#components-and-processes),
[Layers](../architecture.md#layers), [Data model](../architecture.md#data-model),
[Routes and API](../architecture.md#routes-and-api), [Security](../architecture.md#security).

**Related:** [Backend](backend.md) (the reading loop, the mail reader, the secret box, pagination),
[Auth and accounts](auth.md) (the caller and the access boundary), [Frontend](frontend.md).

## Modules and their files

| Module | What it does | Router |
|---|---|---|
| `mailboxes` | Connecting, listing, refreshing and disconnecting a mailbox; the background reading run that reads the due mailboxes | `router` (`/api/v1/mailboxes`) in `backend/app/modules/mailboxes/router.py` |
| `correspondence` | Parsing a read email, storing it once per user with its copies, joining emails into reply chains, the list and the page of a chain | `router` (`/api/v1/reply-chains`) in `backend/app/modules/correspondence/router.py` |
| `attachments` | Downloading one attachment of an email from a connected mailbox that holds it, read-only; nothing is stored | `router` (`/api/v1/emails`) in `backend/app/modules/attachments/router.py` |

Both modules follow the layers of [Layers](../architecture.md#layers): `router.py` → `service.py` → `domain.py` and
`repository.py` → `models.py`. The module `attachments` ([Attachments](#attachments)) has a `router.py`, a `service.py` and an
`errors.py`, and no tables, so no `models.py`, `schemas.py` or `repository.py`. The files of each module are `schemas.py` (request and response models), `errors.py`
(domain errors), and `models.py` (tables). `backend/app/modules/mailboxes/domain.py` holds the Russian reason of a failed read;
`backend/app/modules/correspondence/domain.py` holds the pure logic of a raw message: parsing, the email key, the choice of the chain that
survives a merge, and the HTML to text conversion.

The modules use each other only through their services and repositories:

- `backend/app/modules/mailboxes/service.py` calls `store_raw_messages` in `backend/app/modules/correspondence/service.py` for every batch it
  reads;
- `backend/app/modules/correspondence/service.py` reads the logins of the user's mailboxes through `list_logins_for_owner` in
  `backend/app/modules/mailboxes/repository.py`, and the account email through the accounts repository.
- `backend/app/modules/attachments/service.py` reads the attachment's copies through `get_attachment_target` in
  `backend/app/modules/correspondence/service.py` and the connected copies through `list_message_sources` in
  `backend/app/modules/mailboxes/service.py`; no business module imports the attachments module; `main.py` only includes its router
  and registers its error mapping.

The platform files do the following:

- `mail_reader.py`: the `MailReader` protocol (with `fetch_message`, one message by UID), `ImapMailReader` (read-only IMAP) and
  `FakeMailReader`; see [Mail reader](backend.md#mail-reader).
- `imap_folders.py`: the IMAP `LIST` parsing and the choice of the Sent folder.
- `secret_box.py`: `SecretBox`, the Fernet encryption of the app passwords; see [Secret box](backend.md#secret-box).
- `pagination.py`: `Page[T]` and the keyset cursor of the reply-chains list; see [Pagination](backend.md#pagination).

## Connecting a mailbox

`POST /api/v1/mailboxes` (signed in) takes `MailboxConnect` and answers 201 with `Mailbox`. The body has `server`,
`port`, `login` and `password`; any other field answers 422 `validation_failed`.

| Field | Rule | Russian message when it fails |
|---|---|---|
| `server` | trimmed and lower-cased; 1 to 253 characters | «Укажите сервер IMAP» |
| `port` | 1 to 65535; defaults to 993 | «Порт должен быть от 1 до 65535» |
| `login` | trimmed; 1 to 254 characters | «Укажите логин» |
| `password` | 1 to 256 characters, not trimmed | «Укажите пароль приложения» |

A missing field or one that is not text gets the same message as an empty one. The messages reach the SPA as
`fields` of the `validation_failed` answer ([Error shape](../architecture.md#routes-and-api)).

The service `connect` in `backend/app/modules/mailboxes/service.py` runs in this order:

1. In a transaction it looks up the user's mailbox with this server and login. A connected one answers 409
   `mailbox_exists`.
2. Outside any transaction it signs in to the server through the reader (`check`), with TLS unless the server is in
   `IMAP_INSECURE_HOSTS`. A refused sign-in answers 422 `mailbox_sign_in_failed`; no answer or a broken connection answers
   422 `mailbox_unreachable`. Nothing is saved on either failure.
3. The password is encrypted with the secret box (FR-23) and the mailbox is saved as `pending` with a read requested now.
   A unique violation at the save also answers `mailbox_exists`.

A mailbox the user disconnected before is reused, not inserted again: the row gets the new port and password, its folders
keep their `last_uid`, and no email is read a second time (FR-27). The answer never carries the password (FR-23).

The connect check only proves the sign-in. The emails come with the next reading run ([Reading a mailbox](#reading-a-mailbox)).

## Listing, refreshing and disconnecting

- `GET /api/v1/mailboxes` (signed in) answers the user's connected mailboxes ordered by login and id, at most
  `MAILBOX_LIST_LIMIT` (100) of them. The list is not paginated.
- `POST /api/v1/mailboxes/{mailbox_id}/refresh` (signed in) answers 202 with `Mailbox`. It only asks for a read: it sets
  the read request to now, and if the mailbox is not being read now, its status becomes `pending` and its error is cleared.
  The read happens at the next tick of the reading loop. A mailbox that is another user's, unknown or disconnected answers
  404 `not_found`.
- `DELETE /api/v1/mailboxes/{mailbox_id}` (signed in) answers 204. It sets the password to null, clears the read request and
  sets `disconnected_at`. The mailbox row, its folders, its email copies and the emails and reply chains stay (ADR 0048).
  A disconnected mailbox is no longer read, and its password is gone. Another user's, unknown or already disconnected
  mailbox answers 404 `not_found`.

The answer `Mailbox` has `id`, `server`, `port`, `login`, `status`, `error`, `error_code` and `last_read_at`. It never has the
password. `error` and `error_code` are set only for `failed`; otherwise both are null. `error_code` is one of `sign_in_failed`,
`unreachable` or `read_failed` (the table below).

### Status of a mailbox

`status` is one of `pending`, `reading`, `read` or `failed`. The SPA page `/mailboxes` (`MailboxesPage`) shows it as
follows. While some mailbox is `pending` or `reading`, the list refetches every 5 seconds; otherwise it does not poll
([Mailboxes feature](frontend.md#mailboxes-feature)):

| `status` | Shown as |
|---|---|
| `pending` | «Ожидает чтения» |
| `reading` | «Читается…» |
| `read` | «Прочитан» before the first successful read; «Прочитан» and the time of `last_read_at` after it |
| `failed` | «Ошибка: » and the reason of `error` |

`error` is set only for `failed`. Its reason, from `STATUS_ERROR_MESSAGES` in `backend/app/modules/mailboxes/domain.py`:

| `error_code` | Reason shown |
|---|---|
| `sign_in_failed` | «не удалось войти в ящик, подключите его заново с новым паролем приложения» |
| `unreachable` | «сервер не отвечает» |
| `read_failed` | «не удалось прочитать письма» |

A stored code the module does not know shows as `read_failed`, in both `error` and `error_code`.

## Reading a mailbox

The reading run is started by the app's lifespan and described in [Background mailbox reading](backend.md#background-mailbox-reading).
This section is the part the mailboxes module does with each due mailbox.

**Which mailbox is due.** `claim_next_due_mailbox` in `backend/app/modules/mailboxes/repository.py` takes one connected
mailbox with a password that is not being read and either has a read requested, was never tried, or was last tried
`MAILBOX_READ_INTERVAL_MINUTES` ago or more. A mailbox in `reading` for 15 minutes or more (`ABANDONED_READING_MINUTES`)
is taken again. The lock skips rows another run holds.

**Claim.** The claim, in its own short transaction, ensures the two folder rows (`inbox` and `sent`), sets the status to
`reading`, sets `last_attempt_at` to now and clears the read request. The run keeps a snapshot of the folder progress and
no session.

**Folders.** For each folder the run reads batch by batch. `since` is today minus `MAILBOX_READ_DEPTH_DAYS` days. The
reader returns up to 50 messages above the saved `last_uid`. When the server's UIDVALIDITY differs from the saved one, the
read starts again from `since`. Each batch is stored with its folder progress (`uidvalidity`, `last_uid`) in one
transaction, so a read that stops keeps what it stored. Each stored batch also places its new chains into the filled
projects, in the same transaction (`place_new_chains`; see [Placing new chains](projects.md#placing-new-chains)). The folder
ends when a batch is short or makes no progress. A folder the server does not have is skipped without an error. What the
reader sends to the server is in [Mail reader](backend.md#mail-reader); it only reads (FR-25).

**Outcome.** When both folders are read, the mailbox becomes `read` with `last_read_at` set to now. When a read fails, the
mailbox becomes `failed` with its `error_code`, and the emails already stored stay (FR-26):

- a sign-in refused by the server, or a password the secret box cannot decrypt, is `sign_in_failed`;
- no answer or a broken connection is `unreachable`;
- any other failure is `read_failed`.

The run logs a warning with the mailbox id, the code and the exception's class name only. A failed mailbox is due again at
the next interval or on «Обновить».

One mailbox failing does not stop the run: the run goes on with the next due mailbox. If a whole run fails, `run_reading_loop`
logs it and goes on at the next tick.

## Joining emails into reply chains

`store_raw_messages` in `backend/app/modules/correspondence/service.py` stores a batch of one folder, sorted by UID. For
each message it parses the raw bytes and decides the chain.

**What is read from a message.** `parse_raw_message` in `backend/app/modules/correspondence/domain.py` keeps the
`Message-ID`, the first `In-Reply-To` id, the `References` ids, the subject, the sender, the `To` and `Cc` addresses, the
sent time, the text and the attachments: the file name and the decoded size of each ([Attachments](#attachments)). The sent time is the `Date` header, else the IMAP internal date. Ids
are normalized: without angle brackets and spaces, lower case; an empty or oversized id counts as missing. Addresses are
lower-cased.

**The key.** An email is identified per user by its key: its normalized `Message-ID`. A message without one gets the key
`no-id:<mailbox>:<folder>:<uidvalidity>:<uid>`, the place it was read from. The key is unique per user (FR-28).

**Copies.** When the user already has an email with the key, the message is not stored again: only a copy is recorded in
`email_copies` for this mailbox, folder and UID. The same email in two mailboxes or two folders is stored once and shown
once (FR-28). A copy is unique per folder and UID, so reading the same UID twice adds nothing.

**Joining.** A new email joins the chains found this way (FR-29):

- the chains of the user's stored emails whose key is one of its `In-Reply-To` or `References` ids;
- when the email has a `Message-ID`, the chains of the user's stored emails that name that id in their `References` or
  `In-Reply-To`.

When no chain is found, the email starts a new chain whose latest email time is its own sent time. The subject is not used:
two emails with the same subject and no reply headers stay in two chains.

**Merging.** The chains found by the two searches above can differ: the email may name one chain and be named by stored
emails in another. When more than one chain is found, they become one. The oldest chain survives (ties by the smaller id). The chains are locked in id order, so two merges cannot deadlock; the emails of the other
chains move to the survivor, and the emptied chains are deleted. The result does not depend on the reading order. Before the
emails move, the `on_merge` callable `carry_placement` runs, so the survivor keeps the earliest placement among the merged
chains (see [Merge hook](projects.md#merge-hook)).

**Latest time.** After a new email joins, the chain's latest email time becomes the largest sent time of its emails.

**Races.** Two runs can store the same email at once. The insert is `ON CONFLICT DO NOTHING` on the key. The run that loses
deletes the chain it has just created for the email, if it created one, keeps the chain of the stored email, and adds only
the copy.

**Participants.** A chain's participants are the `From`, `To` and `Cc` addresses of its emails, distinct, in order of first
appearance, oldest email first. The user's own addresses are left out: the logins of all of the user's mailboxes, connected
or disconnected, and the account email (`_own_addresses` in `backend/app/modules/correspondence/service.py`). Where an
address appears with and without a name, the name is taken from the first occurrence that has one (FR-30).

**Documents for placing.** `list_chain_documents` in `backend/app/modules/correspondence/service.py` gives the projects module
every chain of the user as a `ChainDocument`, in reading order: the chain's id, its first email's subject, sent time and key,
the text the placement engine reads, and `senders`. `senders` is the distinct `From` addresses of the chain's emails,
lower-cased and sorted; the placement rules match a chain by them and by its subject. The read covers all of the user's
emails, because the engine weighs words over the whole corpus.

## HTML to text

An email is kept as text only. `_body_text` takes the `text/plain` part when there is one. Otherwise it takes the `text/html`
part and runs `html_to_text` on it:

- the content of `script`, `style` and `head` is dropped;
- block tags (paragraphs, divisions, line breaks, list items, table rows, headings, quotes, preformatted text, tables) end a
  line;
- entities are decoded and runs of spaces collapse; three or more line breaks become two.

The text is kept up to 200,000 characters, and characters PostgreSQL cannot store (NUL, lone surrogates) are removed. The
attachments are kept as a name and a size each; their content is not stored ([Attachments](#attachments)).

The SPA shows the text with `white-space: pre-wrap` (`frontend/src/features/correspondence/ChainPage.module.css`) and never
sets HTML, so the server's text is never run as markup.

## Reading a reply chain

### The list

`GET /api/v1/reply-chains` (signed in) takes `limit` (1 to 100, default 50) and `cursor`. It answers `Page[ReplyChainSummary]`:
`items` and `next_cursor`, which is null on the last page. Chains are ordered by the latest email time, newest first, with
the id as the tie-break. The cursor is the position of the last item, encoded by `encode_cursor`; the client treats it as
opaque. A cursor this app did not issue answers 400 `invalid_cursor` («Страница списка недействительна»).

Each item has `id`, `subject` (the subject of the chain's oldest email), `participants`, `email_count` and
`latest_email_at`. The list reads only the user's chains (owner filter in `list_chains_page_for_owner`).

### One chain

`GET /api/v1/reply-chains/{chain_id}` (signed in) answers `ReplyChain`: `id`, `subject`, `participants` and `emails`, the
oldest first. At most `CHAIN_EMAIL_LIMIT` (500) emails are read, the oldest 500 when a chain has more. Each email has `id`,
`sender`, `to`, `cc`, `sent_at`, `subject`, `text` and `attachments`, the list of its attachments: each has `index` (the position the download takes),
`name` and `size` (null for an email read before migration `0009`). Another user's chain and an unknown id both answer
404 `not_found` (FR-31).

The SPA pages are `/chains` (`ChainsPage`), which shows the list, and `/chains/:id` (`ChainPage`), which shows one chain
([Correspondence feature](frontend.md#correspondence-feature)). On `ChainPage` each email shows «Тема:» with its subject,
then «От:» with the sender, then «Кому:» and, when there are any, «Копия:».

## Attachments

The download is on click and nothing is stored, as recorded in [ADR 0103](../adr/0103-attachments-are-downloaded-on-click-the.md).

**What is kept.** At each read the app keeps, for every attachment of an email, its file name and the size of its decoded content, as
the `attachments` column of `emails` ([Data model](../architecture.md#data-model)). The content is not stored. An attachment is a
part of the message that is not multipart and has a file name; a part without a name is not one. `attachment_parts` in
`backend/app/modules/correspondence/domain.py` lists them in `walk()` order, and that list is the one reading and downloading both
use, so an attachment's `index` is its position in it. An email read before migration `0009` keeps its names, with size null.

**The download.** `GET /api/v1/emails/{email_id}/attachments/{index}` (signed in) answers the file of one attachment. The route is
in `backend/app/modules/attachments/router.py`; the use case `download_attachment` in `backend/app/modules/attachments/service.py`
runs in this order:

1. In one transaction it looks up the email, which must be the user's, and the attachment at `index` in the email's list. An
   unknown or another user's email, or an index out of range, answers 404 `not_found`, and no mailbox is contacted.
2. It lists the copies of the email (mailbox, folder and UID). The transaction closes before any IMAP connection. The copies
   that count are those in a connected mailbox (not disconnected, with its password stored). They are tried in this order:
   Inbox before Sent, then the mailbox's `created_at` (oldest first), then the UID. A copy whose stored password cannot be
   decrypted is skipped, with a warning log that names the mailbox id.
3. For each copy the reader fetches the whole message (`MailReader.fetch_message`): it opens the folder read-only, compares its
   UIDVALIDITY with the stored one, and runs `UID FETCH <uid> (BODY.PEEK[])`. The message is read in memory for this request only.
   The copy is gone (no file) when the folder is missing, its UIDVALIDITY changed, or the server has no message at that UID. The
   attachment at `index` counts only when its part has the stored name; otherwise the copy is treated as not this email.
4. The first copy that yields the attachment wins. The answer is 200 with the bytes, `Content-Type: application/octet-stream`,
   `Content-Disposition: attachment; filename*=UTF-8''` and the percent-encoded name, and `X-Content-Type-Options: nosniff`. A
   browser saves the file under its name and does not show it in the app, so an HTML attachment is not opened.

**Nothing is written.** The app keeps no copy of the content ([ADR 0103](../adr/0103-attachments-are-downloaded-on-click-the.md)): each click fetches it again, and two clicks give the same bytes.
A download writes no row, so the mailbox status, its last read and the email stay as they were, and the email stays unread in its
folder, because the fetch uses `BODY.PEEK`.

**Errors.** When no copy yields the file, the answer is the error of the last copy that failed to be read. When no copy failed
and every connected copy is gone, the answer is 410.

| Case | Status | Code | Message |
|---|---|---|---|
| no live session of a confirmed user | 401 | `not_signed_in` | |
| another user's or an unknown email, or an index out of range | 404 | `not_found` | |
| an index that is negative or not a number | 422 | `validation_failed` | |
| no connected mailbox holds a copy of the email | 409 | `mailbox_disconnected` | «Файл недоступен: ящик отключён» |
| every connected copy is gone from its mailbox | 410 | `email_gone` | «Письмо больше не найдено в ящике» |
| the server refused the sign-in for the last failed copy | 502 | `mailbox_sign_in_failed` | «Не удалось получить файл: не удалось войти в ящик» |
| the server did not answer, the connection broke, or it refused to read the message | 504 | `mailbox_unreachable` | «Не удалось получить файл: сервер не отвечает» |

The codes and messages are in `ERROR_MAPPING` of `backend/app/modules/attachments/router.py`. A failed download leaves every
mailbox status as it was, so the next click tries again (FR-58).

## Errors over HTTP

| Code | Status | When | Mapped in |
|---|---|---|---|
| `validation_failed` | 422 | a body field is invalid, or a field is unknown | `MailboxConnect` ([fields](#connecting-a-mailbox)); `RequestModel` in `backend/app/platform/validation.py` |
| `mailbox_exists` | 409 | the user already has this server and login connected | `ERROR_MAPPING` in `backend/app/modules/mailboxes/router.py` |
| `mailbox_sign_in_failed` | 422 | the server refused the login or the password at the connect check | `ERROR_MAPPING` in `backend/app/modules/mailboxes/router.py` |
| `mailbox_unreachable` | 422 | the server did not answer at the connect check; the message names the server | `register_mailbox_errors` in `backend/app/modules/mailboxes/router.py` |
| `not_found` | 404 | another user's or a disconnected mailbox, another user's or an unknown chain, another user's or an unknown email or attachment index | `NotFound` (`backend/app/platform/errors.py`) |
| `mailbox_disconnected` | 409 | a download: no connected mailbox holds a copy of the email | `ERROR_MAPPING` in `backend/app/modules/attachments/router.py` |
| `email_gone` | 410 | a download: every connected copy is gone from its mailbox | `ERROR_MAPPING` in `backend/app/modules/attachments/router.py` |
| `mailbox_sign_in_failed` | 502 | a download: the server refused the sign-in (the connect check answers 422) | `ERROR_MAPPING` in `backend/app/modules/attachments/router.py` |
| `mailbox_unreachable` | 504 | a download: the server did not answer or refused to read the message (the connect check answers 422) | `ERROR_MAPPING` in `backend/app/modules/attachments/router.py` |
| `invalid_cursor` | 400 | the cursor of the list is not one this app issued | `ERROR_MAPPING` in `backend/app/modules/correspondence/router.py` |
| `not_signed_in` | 401 | no live session of a confirmed user | `current_user` |
| `forbidden_origin` | 403 | a POST or DELETE without the app's `Origin` | `OriginGuardMiddleware` |

The messages of `mailbox_exists`, `mailbox_sign_in_failed` and `invalid_cursor` are in the router's `ERROR_MAPPING`; the
message of `mailbox_unreachable` starts with «Не удалось подключиться к серверу», followed by the server name the user typed.

## Demo mailboxes

The demo mail server is GreenMail in Docker ([ADR 0049](../adr/0049-demo-mailboxes-run-on-greenmail-in.md)). The compose
service `greenmail` uses the image GreenMail standalone 2.1.8, publishes IMAP on port 3143 and creates the users
`anna@demo.test` and `anna.work@demo.test`, both with `DEMO_MAIL_PASSWORD`. The `backend` service reaches it by the service
name, and `IMAP_INSECURE_HOSTS` names `greenmail` so that it is read without TLS ([Environment variables](../tech.md#environment-variables)).

To try the flow by hand:

1. Start the server with `docker compose up -d greenmail` (or `just dev`, which starts it too).
2. Run `just demo-mail` (the same as `just demo-mail load`). The server keeps its mail in memory, so after a restart run it again.
3. Start the stack with `just dev` and sign in to the SPA. On `/mailboxes`, connect a mailbox with the server `greenmail`,
   the port `3143` (the port defaults to 993, so change it), the login `anna@demo.test` or `anna.work@demo.test`, and the
   password `DEMO_MAIL_PASSWORD` from `.env`. The backend container reaches `greenmail` by the service name, without TLS.

`just demo-mail` runs `scripts/demo_mail.py` with one of three commands:

- `load` (the default) appends the prepared messages in `docker/greenmail/demo/*.eml` to the Inbox and Sent folders of both
  mailboxes, as `manifest.json` says. Two of them carry a file, in the chain «Смета на ремонт офиса»: `смета.xlsx` (in
  `01-c01-m1.eml`) and `договор.pdf` (in `03-c01-m3.eml`). The PDF is a tiny PDF, and the `.xlsx` is a minimal zip archive,
  not a real spreadsheet; they are there for the manual download check. The 40 files form 10 chains; the manifest has 43 entries, because three emails
  (`04-c01-m4.eml`, `19-c05-m4.eml`, `32-c08-m4.eml`) sit in one Sent folder and in the other mailbox's Inbox. Emails the
  manifest marks as unread get no `\Seen` flag, and the dates move so that the newest email is yesterday. `load` does nothing
  when a demo Inbox already holds mail;
- `status` prints, for each mailbox and folder, the message count and the unread count;
- `add-new` appends one new unread reply to the Inbox of `anna@demo.test`, in the chain «Смета на ремонт офиса», for the
  check of the «Обновить» button.

The script reads `DEMO_MAIL_HOST` (default `localhost`), `DEMO_MAIL_PORT` (default 3143) and `DEMO_MAIL_PASSWORD`, from the
environment or the repo-root `.env`; it does not read the app's `Settings`.

## Tests

- Unit tests: `backend/app/platform/test_mail_reader.py` (the commands the reader sends, the Sent folder choice, the fake),
  `backend/app/platform/test_mail_reader_fetch_message.py` (fetching one message by UID) and
  `backend/app/platform/test_secret_box.py`.
- Integration tests, one file per group, through HTTP against the test database: `test_mailboxes_connect.py`,
  `test_mailboxes_disconnect.py`, `test_mailboxes_reading.py`, `test_reply_chains_join.py` and `test_reply_chains_read.py`, and the attachment groups `test_attachment_download.py` (the download route),
  `test_reply_chains_attachments.py` (the attachments in the chain API) and `test_migrations_attachments.py` (migration `0009`).
  They override `get_mail_reader` with the `FakeMailReader`, so no test opens a mail server, and `read_due()` in the factories
  runs one reading pass.
- `backend/tests/mail_factory.py` builds raw messages with the standard library, the way a mail server hands them over, and
  attachments of a given size (`sized_attachment`).

Manual checks use the demo mailboxes, not the tests ([Backend](backend.md#integration-tests)).
