# Design

## Context

Task 1.2 parses each email once, when a mailbox is read (`correspondence/domain.py`), and keeps its text
and `emails.attachment_names`: the file names of the non-multipart parts that have one, in `walk()`
order. Every copy of an email in a mailbox folder is a row of `email_copies` (mailbox, folder, IMAP UID);
a folder (`mailbox_folders`) keeps its kind, its server name and its UIDVALIDITY. Disconnecting a mailbox
(FR-27) clears its password and sets `disconnected_at`; its copies stay. `platform/mail_reader.py` signs
in, opens a folder with a read-only `SELECT` and fetches `BODY.PEEK[]`, and raises
`MailboxSignInFailed`, `MailboxUnreachable` or `MailboxReadFailed`. The `mailboxes` service imports the
`correspondence` service (to store what it reads), so `correspondence` cannot import `mailboxes.service`
without a cycle. The chain page is `frontend/src/features/correspondence/ChainPage.tsx`.

## Goals / Non-Goals

**Goals:**
- Show the type and size of each attachment (FR-31).
- Download an attachment from a connected mailbox, read-only, keeping no content (FR-57, FR-25).
- Say why an attachment cannot be fetched, without touching the mailbox status (FR-58).

**Non-Goals:**
- Storing or searching attachment content; previews; splitting attached emails into their files.
- Any cache of fetched messages.

## Decisions

### D1. Fetch on click, keep nothing

Decided by the user. The file is fetched from the mailbox when the user clicks it and streamed back; it
is held in memory only for the request. Alternatives: store the content at read time (works after a
mailbox is disconnected, but the database grows by the size of all attachments and it is the idea
«Attachments' content and search»); previews on the page. Rejected by the user for now.

### D2. An attachment is addressed by the email and its position

`GET /api/v1/emails/{email_id}/attachments/{index}`, where `index` is the position in the email's list of
attachments, from 0. Position, not name, because one email may carry two files with one name. The list
is built by one function used both at read time and at download time, so the positions match. After the
message is fetched, the attachment at `index` must have the stored name; if the list is shorter or the
name differs, the copy is taken as not this email (answer «gone»).
Alternative: the MIME section number (`BODY.PEEK[2.1]`) stored per attachment, so only that part is
fetched. Rejected for now: it needs `BODYSTRUCTURE` parsing and a new stored field for every attachment,
and mail services cap a whole message at a few tens of MB anyway.

### D3. The whole message is fetched by UID

The mail reader gains `fetch_message(credentials, folder_name, uidvalidity, uid)`: sign in, read-only
`SELECT` of the folder by its stored server name, compare UIDVALIDITY with the stored one, `UID FETCH
<uid> (BODY.PEEK[])`, sign out. A changed UIDVALIDITY or an empty answer means the message is gone. It
sends no command that writes (FR-25), the same list as reading.
Alternative: when the UID is gone, search the folder by `Message-ID`. Rejected for now: UIDVALIDITY
rarely changes, and a deleted email is gone either way.

### D4. Which copy is used

Copies of the email in connected mailboxes of the user (password present, not disconnected), Inbox
before Sent, oldest copy first. Each is tried in turn; the first that yields the attachment wins. When
none is connected: «disconnected». When every connected copy is gone: «gone». Otherwise the error of the
last tried copy: sign-in refused or no answer. A failed download writes nothing, so the mailbox status
(FR-23, FR-26) stays as it was.

### D5. A new backend module `attachments`

It owns the download: it reads the email and its copies through `correspondence.service`, the folder,
credentials and the reader through `mailboxes.service`, and it is imported by neither, so there is no
cycle (`server-architecture.md`). Both reads go under the owner filter of the caller.
Alternative: put it in `mailboxes`, which may import `correspondence` — rejected: the route is about an
email, and `mailboxes/service.py` is already large.

### D6. The file is always saved, never rendered

The answer is `application/octet-stream` with `Content-Disposition: attachment; filename*=UTF-8''<name>`
and `X-Content-Type-Options: nosniff`, whatever the declared type, so an HTML or SVG attachment never
runs on the app's origin (FR-57 «An HTML attachment»). The SPA calls the endpoint through the generated
client, receives a blob, and saves it through a temporary object URL with the `download` attribute; on
an error answer it shows the message under the attachment.

### D7. Sizes and the shown type

`size` is the number of bytes of the decoded part. Shown: below 1024 as «N Б»; below 1024 × 1024 as «N КБ»
rounded to a whole number; above as «N,N МБ» with one decimal and a comma. The type is the extension
after the last dot of the name, in capitals; a name without a dot shows no type.

### Data and migration

Migration `0009_email_attachments` adds `emails.attachments` (JSONB, not null): a list of
`{"name": string, "size": int | null}`, filled from `attachment_names` with `size` null for every existing
email, then drops `attachment_names`. New emails store sizes. Downgrade rebuilds `attachment_names` from
the names and drops `attachments`; sizes are lost, nothing else. The engine does not read attachments.

### Who may call

A signed-in user (FR-17). A `GET` changes nothing, so no same-site check beyond the session cookie's
rules (FR-20 covers writes). The email is looked up by id under the owner filter; another user's email,
an unknown id or an index out of range answers 404 before any connection to a mailbox. Only the caller's
own mailboxes are signed into.

## Interface

HTTP:

- `GET /api/v1/emails/{email_id}/attachments/{index}` — `index` an integer from 0.
  - 200: the file bytes, `Content-Type: application/octet-stream`, `Content-Disposition: attachment;
    filename*=UTF-8''<percent-encoded name>`, `X-Content-Type-Options: nosniff`.
  - 401 when signed out; 404 for another user's email, an unknown email or an index out of range.
  - 409 `{"error": {"code": "mailbox_disconnected", "message": "Файл недоступен: ящик отключён"}}`.
  - 410 `{"error": {"code": "email_gone", "message": "Письмо больше не найдено в ящике"}}`.
  - 502 `{"error": {"code": "mailbox_sign_in_failed", "message": "Не удалось получить файл: не удалось войти в ящик"}}`.
  - 504 `{"error": {"code": "mailbox_unreachable", "message": "Не удалось получить файл: сервер не отвечает"}}`.
- `EmailView.attachment_names: list[str]` is replaced by `attachments: list[AttachmentView]`, where
  `AttachmentView` is `{ "index": int, "name": string, "size": int | null }`.

SPA texts (exact): an attachment reads «<name> · <TYPE> · <size>», with the type or the size left out
when unknown, as a button that downloads; the error under it is the `message` of the answer.

## Risks / Trade-offs

- A download needs a connected mailbox and a live server; a disconnected mailbox's attachments are lost
  to the app. Accepted by D1; storing content stays an idea.
- A large message is fetched whole and held in memory for one request. Mail services cap messages at
  about 25–50 MB; acceptable for a personal app.
- The request waits for the IMAP server up to `IMAP_TIMEOUT_SECONDS` per copy tried.
- Old emails show no size until they are read again, which does not happen; accepted.
