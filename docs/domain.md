# Domain

Version 0.4 · 29.10.2026

Changes in 0.4: task 1.1 removes organizations: glossary loses Organization, Employee,
Administrator, Member and Invitation and gains User; requirements map of task 1.1; FR-9…FR-16, FR-18
and FR-19 cancelled.

Changes in 0.3: new concept without organizations: glossary terms Project, Reply chain, Thread,
Unassigned; Counterparty and Correspondence belong to a user; consent to a third-party model is the
user's. Organization, Employee, Administrator, Member and Invitation stay until task 1.1 removes them.

Changes in 0.2: requirements map of task 0.2; glossary terms Member, Invitation, Session; service
emails and stored secrets in «Data and privacy».

Changes in 0.1: skeleton; terms from the harness interview.

Last FR number: FR-21

## Contents

- [Requirements map](#requirements-map)
- [Glossary](#glossary)
- [Lifecycle of an assessment](#lifecycle-of-an-assessment)
- [Data and privacy](#data-and-privacy)
- [Non-functional notes](#non-functional-notes)
- [Cancelled numbers](#cancelled-numbers)

## Requirements map

Capability → its spec and FR numbers. A new FR number also goes into «Last FR number» above.

| Capability | Spec | FR |
|---|---|---|
| organization-registration | [spec](../openspec/specs/organization-registration/spec.md) | FR-1…FR-3 |
| sign-in | [spec](../openspec/specs/sign-in/spec.md) | FR-4…FR-8 |
| access-boundary | [spec](../openspec/specs/access-boundary/spec.md) | FR-17, FR-20, FR-21 |

## Glossary

| Term | Meaning |
|---|---|
| User | A person who registered on their own with a name, an email and a password; owns their mailboxes, projects and correspondence and gives consent to a third-party model |
| Mailbox | An email account connected to the app read-only |
| Counterparty | A person or company the user corresponds with; a reply chain with several of them is shown under each |
| Correspondence | The emails between the user and a counterparty, from all of the user's mailboxes |
| Project | A piece of the user's work, created by hand with a description; its correspondence is laid out as a tree: project → counterparty → thread |
| Reply chain | An email and all replies to it, linked by the `References` and `In-Reply-To` headers across all mailboxes; never split, belongs to at most one project |
| Thread | A topic of a project formed by the engine; it groups whole reply chains |
| Unassigned | The place of a project for reply chains the engine is not sure about; the user places them |
| Assessment | The sentiment of a thread or a counterparty within a project, with its evidence; a later layer over the tree |
| Evidence | The emails and phrases an assessment rests on |
| Session | The signed-in state of a user in one browser; ends at sign-out, after its lifetime or on a password reset |
| Analysis model | The engine and its version that computes an assessment; shown with the result |

TBD: how a counterparty is identified (address, domain, company).

## Lifecycle of an assessment

TBD.

## Data and privacy

- Email text and metadata are read from the mailbox and stored by the app; the mailbox is never changed.
- If the engine uses a third-party model, email text goes there only after the user's consent.
- The app sends its own service emails (confirmation, password reset) through its own SMTP
  account, never through a connected mailbox, so the mailbox stays read-only.
- A user record keeps the name, the email and a password hash; links and sessions are stored only as
  hashes of their tokens.
- TBD: retention, deletion of a mailbox and its data.

## Non-functional notes

TBD.

## Cancelled numbers

| FR | Was | Cancelled by |
|---|---|---|
| FR-9…FR-12 | Invitations: invite an employee, status and resending, revoke, accept | task 1.1, ADR 0023 |
| FR-13…FR-16 | Members: list, deactivate and reactivate, appoint administrators, keep one administrator | task 1.1, ADR 0023 |
| FR-18 | Organizations never see each other; replaced by FR-21 | task 1.1, ADR 0023 |
| FR-19 | Administrator actions are closed to employees | task 1.1, ADR 0023 |
