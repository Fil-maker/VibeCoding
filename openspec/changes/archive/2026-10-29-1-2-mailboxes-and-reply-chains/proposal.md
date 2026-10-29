# Proposal

## Why

The user's correspondence about a project is scattered over several mailboxes and many reply chains,
and the user rereads the mailboxes by hand to recall what was agreed (`docs/prd.md` «Problem»). The app
cannot lay anything out until it reads the mailboxes and joins their emails into reply chains — the
unit every later placement works with. This is task 1.2 of `docs/plan.md`, the second step to the first
version shown to the customer.

## What Changes

- The user connects one or more mailboxes over IMAP with a login and an app password; the app signs in
  to the server first and reports a wrong password or an unreachable server. The password is stored
  encrypted and never shown back.
- The app reads the folders Inbox and Sent, emails of the last 12 months, in the background: right after
  connecting, every 5 minutes and when the user presses «Обновить». Each mailbox shows its status and
  the time of its last read; a failed read is shown and retried.
- Reading never changes the mailbox: unread emails stay unread, nothing is moved, flagged or deleted.
- The user disconnects a mailbox: its password is deleted and reading stops; the emails already read
  stay.
- An email present in several mailboxes or folders is stored once. Emails are joined into reply chains
  by the `References` and `In-Reply-To` headers across all mailboxes.
- New pages «Почтовые ящики» and «Переписка»: the list of reply chains and one chain with its emails.
- Development: a local demo mail server with two mailboxes and `just demo-mail`, which fills them with
  prepared Russian correspondence for the customer demo.

Out of scope, deferred to `docs/ideas.md`:
- OAuth sign-in to Gmail and Outlook; folders other than Inbox and Sent; a configurable reading depth
  per mailbox.
- Attachments' content (only their names are kept); full-text search over emails.
- Merging counterparties with several addresses («Counterparty with several addresses»).
- Deleting the emails of a disconnected mailbox, and deleting a user's account.
- Projects, threads and placement (tasks 1.3, 1.4).

## Capabilities

### New Capabilities

- `mailboxes`: connecting, checking, reading, refreshing and disconnecting the user's mailboxes,
  read-only, with the password kept secret.
- `reply-chains`: storing each email once and joining the emails of all of a user's mailboxes into reply
  chains that the user lists and reads.

### Modified Capabilities

None: FR-17 (signed-in user) and FR-21 (users never see each other) already cover the new pages and
data; the new requirements carry their own negative scenarios.

## Impact

- Product invariants: **Mailbox read-only** (reading opens folders read-only and never sets a flag),
  **Access boundary** (every mailbox, email and chain belongs to one user; another user's identifier
  answers «not found»), **History is kept** (a disconnected mailbox keeps its emails). No email text
  leaves the installation.
- Backend: new modules `mailboxes` and `correspondence`, a background reading loop started by the app,
  new tables and migration `0004`, new settings and env vars (encryption key, reading interval, depth).
- New dependency: `cryptography` for the encryption of mailbox passwords.
- New dev service: GreenMail in `docker-compose.yml` for the demo mailboxes; `just demo-mail`.
- SPA: pages «Почтовые ящики» and «Переписка», links from the start page; the regenerated API client.
- Docs: `docs/domain.md` (requirements map, «Data and privacy»), `docs/architecture.md`, `docs/tech.md`,
  a guide article on mail reading.
