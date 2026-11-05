# Proposal

## Why

Task 1.11 «Attachments» of `docs/plan.md`. The point of the app is to read a project's correspondence in
one place (`docs/prd.md`), but a contract, an estimate or an act usually comes as an attachment, and task
1.2 keeps only its name: to open the file the user has to leave the app, find the email in the mail
service by hand and download it there.

## What Changes

- On the page of a reply chain every attachment of an email shows its name, its type (the file
  extension) and its size; attachments of emails read before this change show no size (FR-31).
- A click on an attachment downloads the file under its name (FR-57). The app fetches the email from a
  connected mailbox that holds a copy of it, over IMAP with a read-only `SELECT` and `BODY.PEEK`, takes
  the attachment out and hands it to the user; the content is never stored.
- An attachment that cannot be fetched says why under its name: no connected mailbox holds the email,
  the email is gone from the mailbox, or the server refused or did not answer (FR-58). A failed download
  does not change the status of the mailbox.
- FR-25 now says that fetching an attachment, like reading, never changes the mailbox.

Out of scope: storing the content of attachments and searching it (stays in `docs/ideas.md` «Attachments'
content and search»); previews of images and PDFs on the page; attachments inside forwarded emails
(`message/rfc822`) as separate files; the app's own rendering of the email text (task 1.12).

Touched invariants: «Mailbox read-only» — the app gets a second way into the mailbox; it opens the folder
read-only and fetches with `BODY.PEEK`, so the email stays unread and unchanged. «Access boundary» — an
attachment is fetched only for the owner of the email; another user's email answers «not found»; the
file goes only to the user, never to a third party. «Explainable placement», «Reproducible placement»
and «History is kept» are not touched: placement does not read attachments.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `reply-chains`: FR-31 «Read a reply chain» shows the type and size of attachments; ADDED FR-57
  «Download an attachment» and FR-58 «An attachment that cannot be fetched».
- `mailboxes`: FR-25 «Reading never changes the mailbox» also covers fetching an attachment.

## Impact

- Backend `correspondence` module: a column with the size of each attachment (one Alembic migration),
  a download endpoint, a service that picks a copy of the email and asks the mail reader for it.
- `platform/mail_reader.py`: a read-only fetch of one message by folder and UID.
- SPA `features/correspondence/ChainPage.tsx`: the attachment list with type, size, download and the
  error under an attachment; the regenerated API client.
- Docs: `docs/domain.md` (the note that the content of attachments is never stored, the requirements
  map, `Last FR number`), `docs/architecture.md`.
