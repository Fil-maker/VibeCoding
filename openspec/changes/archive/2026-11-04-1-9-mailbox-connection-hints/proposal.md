# Proposal

## Why

A user connecting a mailbox has to find the IMAP server and port of their mail service, learn what an
app password is and where the service hides it — the connect form of task 1.2 gives four bare fields
and a generic error. `docs/prd.md` puts the first value of the app right after the mailboxes are
connected, so a user who gives up on the form never sees a project tree.

Plan task 1.9 «Mailbox connection hints»; requirements FR-53 and FR-54 (new), FR-22 and FR-26 (modified).

## What Changes

- The connect form on «Почтовые ящики» starts with «Адрес почты», which is also the login. A built-in
  table of mail services picks the service from the address's domain and fills the server and port.
- The user can pick the service by hand: Яндекс, Mail.ru, Gmail, iCloud, Демо, Другой. The server,
  port and a login other than the address sit under «Настройки сервера», open for «Другой» with an
  empty server and the port 993. An unknown domain picks «Другой» with a hint where to find the
  server.
- Every real service shows short steps — turn on IMAP access where the service needs it, create an
  app password — and a link to its official help.
- The form says why an app password is needed and that the app only reads the mailbox.
- A sign-in failure on connecting and «не удалось войти в ящик» in the mailbox list show the steps and
  the link of the mailbox's service; other errors do not.
- The mailbox list answer (`GET /api/v1/mailboxes`) gains `error_code`, so the SPA tells a sign-in
  failure from the others without reading the error text.
- The service is picked in the SPA from the built-in table only: no MX lookup, no request to an
  external catalog.

## Capabilities

### New Capabilities

None; the new requirement joins `mailboxes`.

### Modified Capabilities

- `mailboxes`: ADDED FR-53 «Pick the mail service from the address» and FR-54 «Show how to connect
  the service»; MODIFIED FR-22 «Connect a
  mailbox» (the form starts with the address; a sign-in failure shows the service's steps); MODIFIED
  FR-26 «A failed read is shown and retried» (a sign-in failure shows the service's steps).

## Out of scope

- Finding the server of a custom domain by its MX record — deferred to `docs/ideas.md`
  «Server detection by MX record».
- Catalogs outside the app (Mozilla ISPDB, autoconfig) — rejected: the user's domain would leave the
  app.
- Outlook.com — its official help says personal accounts sign in over IMAP only with OAuth since
  16.09.2024, so it waits for `docs/ideas.md` «OAuth sign-in to Gmail and Outlook».
- Рамблер — its official help has no page on mail programs to confirm the server and the steps;
  deferred to `docs/ideas.md` «More mail services in the connection hints».
- Checking automatically that the help links still work.

## Invariants

None is changed. «Mailbox read-only» is now also told to the user in the form. «Access boundary»: the
service is picked in the browser from a built-in table, so neither the address nor its domain goes to a
third party.

## Impact

- SPA: `frontend/src/features/mailboxes/` — the connect form, a table of mail services, the hints
  in the form and in the mailbox list.
- Backend: `backend/app/modules/mailboxes/schemas.py` and `service.py` — `error_code` in the
  `Mailbox` answer; the OpenAPI schema and the generated client change.
- No migration: `mailboxes.error_code` exists since migration 0004.
- No new dependency, no new env var.
