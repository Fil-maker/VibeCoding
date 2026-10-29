# Mailboxes are read in a background task inside the backend: right after connecting, every 5 minutes and on the button «Обновить»; each mailbox shows its status and last read time

Id: 0046 · Date: 29.10.2026 · Kind: technical · Status: Accepted · Who: [human]

## Context
Task: 1.2.
- Task 1.2 adds backend modules mailboxes (connect, list, refresh, disconnect a mailbox; background reading) and correspondence (emails, email copies, reply chains: joining and reading).
- Mailbox routes: GET /api/v1/mailboxes (connected mailboxes of the user, at most MAILBOX_LIST_LIMIT = 100, unpaginated), POST /api/v1/mailboxes (connect; signs in to IMAP before saving), POST /api/v1/mailboxes/{mailbox_id}/refresh («Обновить»), DELETE /api/v1/mailboxes/{mailbox_id} (disconnect).
- Reply chain routes: GET /api/v1/reply-chains (keyset pages, query limit 1-100, default 50, cursor; latest chain first) and GET /api/v1/reply-chains/{chain_id} (emails oldest first, at most CHAIN_EMAIL_LIMIT = 500; another user's chain answers 404).
- Mailbox reading runs as a background asyncio task started in the FastAPI lifespan (backend/app/main.py): run_reading_loop calls read_due_mailboxes every MAILBOX_READ_TICK_SECONDS; a mailbox is due right after connecting, on refresh, or when MAILBOX_READ_INTERVAL_MINUTES have passed since its last attempt. Mailboxes are claimed from the database one by one; network calls run outside transactions.
- IMAP reading (backend/app/platform/mail_reader.py, ImapMailReader) is read-only: SELECT with readonly=True (EXAMINE), UID SEARCH, UID FETCH BODY.PEEK[] FLAGS INTERNALDATE; never STORE, APPEND, EXPUNGE, COPY or DELETE. Folders Inbox and Sent (found by imap_folders.py), emails of the last MAILBOX_READ_DEPTH_DAYS days. Reader errors: sign-in failed, unreachable, MailboxReadFailed (status failed with error_code sign_in_failed, unreachable or read_failed). FakeMailReader is the test double; it dates messages without a Date header with the fixed FAKE_UNDATED_MESSAGE_DATE.
- TLS is used for every IMAP host except those listed in IMAP_INSECURE_HOSTS (compose sets greenmail).
- Mailbox app passwords are encrypted with Fernet (backend/app/platform/secret_box.py, key MAILBOX_ENCRYPTION_KEY, new dependency cryptography); never returned in an answer or logged; set to null on disconnect. Losing or changing the key makes every connected mailbox ask for a new app password.
- Tables of migration 0004: mailboxes (unique user_id, server, login; status pending/reading/read/failed), mailbox_folders (per mailbox kind inbox/sent with uidvalidity and last_uid), reply_chains (user_id, latest_email_at), emails (unique user_id, key; key is the Message-ID or no-id:<mailbox>:<folder>:<uidvalidity>:<uid>), email_copies (an email in a mailbox folder by uid). Disconnecting keeps emails and chains.
- Joining: an email joins the chains named by its In-Reply-To and References; an email naming two chains merges them; the same subject without reply headers makes two chains. An email present in several mailboxes or folders is stored once per user. HTML-only emails are converted to plain text on the server (html_to_text drops script, style and head); the SPA shows text with white-space pre-wrap and never sets HTML.
- Participants of a chain are the From/To/Cc addresses other than the logins of all the user's mailboxes and the account email.
- backend/app/platform/pagination.py holds the keyset cursor Page[T] {items, next_cursor} used by the reply-chains list.
- SPA: pages /mailboxes (MailboxesPage: connect form, list with status «Ожидает чтения», «Читается», «Прочитан …», error, «Обновить», «Отключить» with confirmation; the list refetches every 5 seconds), /chains (ChainsPage) and /chains/:id (ChainPage); StartPage links to them. Frontend tests pin TZ=UTC in frontend/vite.config.ts.
- Demo mail: compose service greenmail (image greenmail/standalone:2.1.8, IMAP port 3143, users anna@demo.test and anna.work@demo.test with DEMO_MAIL_PASSWORD). just demo-mail [load|status|add-new] runs scripts/demo_mail.py: load appends docker/greenmail/demo/*.eml to Inbox and Sent as manifest.json says (40 emails in 10 chains), status prints counts and unread counts per folder, add-new appends one new unread reply to anna@demo.test. The script reads DEMO_MAIL_HOST (localhost), DEMO_MAIL_PORT (3143) and DEMO_MAIL_PASSWORD, not Settings.
- New env vars with defaults: MAILBOX_ENCRYPTION_KEY (required), MAILBOX_READING_ENABLED=true, MAILBOX_READ_INTERVAL_MINUTES=5, MAILBOX_READ_TICK_SECONDS=10, MAILBOX_READ_DEPTH_DAYS=365, IMAP_TIMEOUT_SECONDS=30, IMAP_INSECURE_HOSTS empty; DEMO_MAIL_PASSWORD, DEMO_MAIL_HOST=localhost, DEMO_MAIL_PORT=3143. Existing .env files need MAILBOX_ENCRYPTION_KEY and DEMO_MAIL_PASSWORD added.

## Decision
Mailboxes are read in a background task inside the backend: right after connecting, every 5 minutes and on the button «Обновить»; each mailbox shows its status and last read time

## Alternatives
only by the button

## Reason
Пользователь выбрал «В фоне + Обновить»
