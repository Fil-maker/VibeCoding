# Ideas

Updated 23.10.2026

Ideas not yet planned, by product area, then the technical backlog. `/idea` adds an entry; `/explore`
discusses a raw one.

## Analysis

### Analysis engine

Added 23.10. Choose what computes the sentiment of the correspondence: a local model or an external LLM.
Why: it decides how reproducible an assessment is and whether email text leaves the app.

**Open:** quality on Russian business email; cost; how the model version is recorded with each
assessment; what the administrator's consent covers.

**Touches:** invariants «Reproducible assessments» and «Access boundary» — a new direction; settle it in
the first `/explore`.

## Access

### Account settings

Added 23.10. What a signed-in user and an administrator may change after task 0.2: change the password
and the email while signed in, edit the name, delete a user or an organization, two-factor
authentication, a per-IP limit on sign-in and registration. Why: task 0.2 covers only joining, signing
in and resetting a forgotten password; these were left out to keep it shippable.

**Open:** which of them the first customers need; what deleting a user does to their correspondence
(«History is kept»).

**Touches:** invariant «History is kept» for deletion; «Access boundary» for the email change.

## Mailbox

### Mailbox connection

Added 23.10. An employee connects their mailbox on a page of the app: server, login and app password over
IMAP; the app checks the connection and keeps the mailbox as the employee's, inside their organization.
Why: without a connected mailbox there is no correspondence to analyse.

Proposed in the explore session:
- IMAP with an app password first (Yandex 360, Mail.ru, Exchange); OAuth for Gmail later.
- Reading never changes the mailbox: the folder is opened read-only and messages are fetched without
  setting the «seen» flag, so unread emails stay unread — a scenario in the spec.
- The mailbox password is stored encrypted with a key from `.env`.

**Open:** does «connect» only check and save or also start reading emails; how many mailboxes an employee
has; how a mailbox is disconnected and what happens to its data; retention.

**Touches:** invariants «Mailbox read-only» and «Access boundary» — a new direction. Needs «Sign-in and
organization» first.

## Technical backlog

None yet.
