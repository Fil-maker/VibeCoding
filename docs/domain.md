# Domain

Version 0.13 · 05.11.2026

Changes in 0.13: task 1.11: attachment content is fetched from the mailbox on click and never stored;
requirements map row reply-chains takes FR-57, FR-58.

Changes in 0.12: task 1.10: glossary term Project — the user edits and deletes it; requirements map row
projects takes FR-55, FR-56.

Changes in 0.11: task 1.9: glossary term Mail service; requirements map row mailboxes takes FR-53, FR-54.

Changes in 0.10: task 1.7: glossary terms Landing page and Start page; requirements map row app-shell takes FR-48…FR-52.

Changes in 0.9: task 1.6: glossary term Rule — editing or deleting moves nothing until the user applies the rule or fills the project; requirements map row placement-rules takes FR-47.

Changes in 0.8: task 1.5: glossary term Rule; Placement gains placements by a rule; requirements map row placement-rules takes FR-43…FR-45 and chain-placement FR-46.

Changes in 0.7: task 1.4: glossary term Placement gains placements by hand and chains taken out by hand, Thread may be created by hand; requirements map row chain-placement takes FR-40…FR-42.

Changes in 0.6: task 1.3: requirements map rows projects and chain-placement; glossary terms Placement and Engine version; Counterparty is one
participant address for now; Thread is named by its earliest chain; projects and placements in «Data and
privacy».

Changes in 0.5: task 1.2: the mailbox data kept in «Data and privacy»; glossary term Participant.

Changes in 0.4: task 1.1 removes organizations: glossary loses Organization, Employee,
Administrator, Member and Invitation and gains User; requirements map of task 1.1; FR-9…FR-16, FR-18
and FR-19 cancelled.

Changes in 0.3: new concept without organizations: glossary terms Project, Reply chain, Thread,
Unassigned; Counterparty and Correspondence belong to a user; consent to a third-party model is the
user's. Organization, Employee, Administrator, Member and Invitation stay until task 1.1 removes them.

Changes in 0.2: requirements map of task 0.2; glossary terms Member, Invitation, Session; service
emails and stored secrets in «Data and privacy».

Changes in 0.1: skeleton; terms from the harness interview.

Last FR number: FR-58

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
| mailboxes | [spec](../openspec/specs/mailboxes/spec.md) | FR-22…FR-27, FR-53, FR-54 |
| reply-chains | [spec](../openspec/specs/reply-chains/spec.md) | FR-28…FR-31, FR-57, FR-58 |
| projects | [spec](../openspec/specs/projects/spec.md) | FR-32…FR-34, FR-55, FR-56 |
| chain-placement | [spec](../openspec/specs/chain-placement/spec.md) | FR-35…FR-42, FR-46 |
| placement-rules | [spec](../openspec/specs/placement-rules/spec.md) | FR-43…FR-45, FR-47 |
| app-shell | [spec](../openspec/specs/app-shell/spec.md) | FR-48…FR-52 |

## Glossary

| Term | Meaning |
|---|---|
| User | A person who registered on their own with a name, an email and a password; owns their mailboxes, projects and correspondence and gives consent to a third-party model |
| Mailbox | An email account connected to the app read-only |
| Mail service | A provider of mailboxes in the app's built-in list (Яндекс Почта, Mail.ru, Gmail, iCloud, Демо), picked by the domain of the address on connecting and giving the server, the port and the steps to connect; any other domain is «Другой» |
| Counterparty | A person or company the user corresponds with; for now one participant address, named by the latest name it wrote with, else by the address; a reply chain with several of them is shown under each, one with none under «Без контрагента» |
| Correspondence | The emails between the user and a counterparty, from all of the user's mailboxes |
| Project | A piece of the user's work, created by hand with a description; its correspondence is laid out as a tree: project → counterparty → thread. The user renames it or changes its description, which moves no chain, and deletes it after a confirmation: its chains become taken out by hand, the rules targeting it are deleted, the emails stay |
| Reply chain | An email and all replies to it, linked by the `References` and `In-Reply-To` headers across all mailboxes; never split, belongs to at most one project |
| Participant | An address in From, To or Cc of a reply chain's emails other than the user's own addresses: the logins of their mailboxes and their account email |
| Thread | A topic of a project that groups whole reply chains: formed by the engine from chains similar to each other and named by the subject of its earliest chain, or created by the user when moving a chain by hand and named by them |
| Placement | Where a reply chain sits — a thread of a project or its «Неразобранное» — and why: by hand («Вручную»), by a rule («Правило» with the rule's condition and value as they were when it placed the chain), or by the engine with the similarity and the engine version; a chain taken out by hand («Убрать из проекта») is in no project and the engine never places it again by itself; the engine never changes a placement by hand |
| Rule | A user's instruction that places a reply chain into a project and a thread named by the rule, or its «Неразобранное», before the engine: by a sender address, a sender domain with its subdomains, or words that begin words of the subject; an address wins over a domain and a domain over subject words, then the earlier rule; a rule never moves a chain placed by hand or taken out, and editing or deleting it moves nothing by itself: a saved rule moves chains when the user applies it on «Правила» or fills the project again |
| Engine version | The name of the engine's method with its thresholds, for example `text-1`; the same version, emails and description give the same placement, and another version is a new name |
| Unassigned | The place of a project for reply chains the engine is not sure about; the user places them |
| Assessment | The sentiment of a thread or a counterparty within a project, with its evidence; a later layer over the tree |
| Evidence | The emails and phrases an assessment rests on |
| Landing page | What a visitor who is not signed in sees at «/»: what the app does in three steps, with «Зарегистрироваться» and «Войти»; shows no user data |
| Start page | What a signed-in user sees at «/»: «Первые шаги» — connect a mailbox, create a project, fill it — counted from the user's own mailboxes and projects; once all three are done it opens «Проекты» |
| Session | The signed-in state of a user in one browser; ends at sign-out, after its lifetime or on a password reset |
| Analysis model | The engine and its version that computes an assessment; shown with the result |

Merging several addresses into one counterparty is an idea: [Ideas](ideas.md#counterparty-with-several-addresses).

## Lifecycle of an assessment

TBD.

## Data and privacy

- Email text and metadata are read from the mailbox and stored by the app; the mailbox is never changed.
- If the engine uses a third-party model, email text goes there only after the user's consent.
- The app sends its own service emails (confirmation, password reset) through its own SMTP
  account, never through a connected mailbox, so the mailbox stays read-only.
- A user record keeps the name, the email and a password hash; links and sessions are stored only as
  hashes of their tokens.
- A connected mailbox keeps its server, login and app password; the password is stored encrypted with
  the installation's key, never shown, and deleted when the mailbox is disconnected.
- The app reads the folders Inbox and Sent, emails of the last 12 months; each email is stored once per
  user with its text, addresses, date and the names and sizes of its attachments, never their content.
- The content of an attachment is fetched from a connected mailbox when the user downloads it and goes
  only to that user; the app never stores it.
- The emails and reply chains of a disconnected mailbox stay; deleting them is not possible yet.
- Projects, threads and placements belong to one user; the engine compares only that user's chains.
- The engine of version `text-1` runs inside the installation: no email text leaves it, so no consent is
  asked.

## Non-functional notes

TBD.

## Cancelled numbers

| FR | Was | Cancelled by |
|---|---|---|
| FR-9…FR-12 | Invitations: invite an employee, status and resending, revoke, accept | task 1.1, ADR 0023 |
| FR-13…FR-16 | Members: list, deactivate and reactivate, appoint administrators, keep one administrator | task 1.1, ADR 0023 |
| FR-18 | Organizations never see each other; replaced by FR-21 | task 1.1, ADR 0023 |
| FR-19 | Administrator actions are closed to employees | task 1.1, ADR 0023 |
