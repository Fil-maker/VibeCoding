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

### Sign-in and organization

Added 23.10. An organization registers itself, and the person who registers it becomes its first
administrator. One installation serves many organizations. The administrator invites employees by an
invitation email the app sends through SMTP; an employee joins only by invitation, never by the domain
of their address. Users sign in with email and password and reset a forgotten password by email in the
same task. Why: the owner filter of the access boundary needs real users and organizations before a
mailbox can belong to anyone; a built-in stub user would mean reworking the filter in every query later.

Decided in the explore session:
- Data is filtered on two levels: by organization, then by owner within it; organization A never sees B.
- An invitation is single-use, expires, can be revoked; only an administrator invites.
- When SMTP fails, the invitation stays «not sent» and can be sent again; dev uses a local mail catcher,
  tests a fake sender.
- Passwords are stored as a slow hash; sign-in attempts are limited.
- Service emails of the app do not touch the «Mailbox read-only» invariant, which is about the users'
  mailboxes; say so explicitly in `docs/domain.md`.

**Open:** can one email belong to two organizations; is the email of the person who registers an
organization confirmed; can an administrator appoint another administrator and deactivate an employee;
sign-in with Yandex ID later.

**Touches:** invariants «Access boundary» and «History is kept» (the administrator sees all of the
organization) — a new direction. Comes before «Mailbox connection».

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
