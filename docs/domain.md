# Domain

Version 0.3 · 28.10.2026

Changes in 0.3: new concept without organizations: glossary terms Project, Reply chain, Thread,
Unassigned; Counterparty and Correspondence belong to a user; consent to a third-party model is the
user's. Organization, Employee, Administrator, Member and Invitation stay until task 1.1 removes them.

Changes in 0.2: requirements map of task 0.2; glossary terms Member, Invitation, Session; service
emails and stored secrets in «Data and privacy».

Changes in 0.1: skeleton; terms from the harness interview.

Last FR number: FR-20

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
| invitations | [spec](../openspec/specs/invitations/spec.md) | FR-9…FR-12 |
| organization-members | [spec](../openspec/specs/organization-members/spec.md) | FR-13…FR-16 |
| access-boundary | [spec](../openspec/specs/access-boundary/spec.md) | FR-17…FR-20 |

## Glossary

| Term | Meaning |
|---|---|
| Organization | The company that uses the app; it has one or more administrators and employees |
| Employee | A user who sees only their own correspondence |
| Administrator | A user who sees all correspondence of their organization and gives consent to third-party analysis |
| Mailbox | An email account connected to the app read-only |
| Counterparty | A person or company the user corresponds with; a reply chain with several of them is shown under each |
| Correspondence | The emails between the user and a counterparty, from all of the user's mailboxes |
| Project | A piece of the user's work, created by hand with a description; its correspondence is laid out as a tree: project → counterparty → thread |
| Reply chain | An email and all replies to it, linked by the `References` and `In-Reply-To` headers across all mailboxes; never split, belongs to at most one project |
| Thread | A topic of a project formed by the engine; it groups whole reply chains |
| Unassigned | The place of a project for reply chains the engine is not sure about; the user places them |
| Assessment | The sentiment of a thread or a counterparty within a project, with its evidence; a later layer over the tree |
| Evidence | The emails and phrases an assessment rests on |
| Member | A confirmed user of an organization: an administrator or an employee, active or deactivated |
| Invitation | An emailed single-use link, valid 7 days, with which an administrator lets a person join the organization as an employee |
| Session | The signed-in state of a user in one browser; ends at sign-out, after its lifetime, on deactivation or on a password reset |
| Analysis model | The engine and its version that computes an assessment; shown with the result |

TBD: how a counterparty is identified (address, domain, company).

## Lifecycle of an assessment

TBD.

## Data and privacy

- Email text and metadata are read from the mailbox and stored by the app; the mailbox is never changed.
- If the engine uses a third-party model, email text goes there only after the user's consent.
- The app sends its own service emails (confirmation, invitation, password reset) through its own SMTP
  account, never through a connected mailbox, so the mailbox stays read-only.
- A user record keeps the name, the email and a password hash; links and sessions are stored only as
  hashes of their tokens.
- TBD: retention, deletion of a mailbox and its data.

## Non-functional notes

TBD.

## Cancelled numbers

None.
