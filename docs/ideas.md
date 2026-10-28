# Ideas

Updated 28.10.2026

Ideas not yet planned, by product area, then the technical backlog. `/idea` adds an entry; `/explore`
discusses a raw one.

## Analysis

### Analysis engine

Added 23.10, changed 28.10. The engine is our own service, external to the user. In stage 1 it finds the
emails that match a project's description, forms threads from whole reply chains and places new chains;
in stage 2 it computes sentiment. Why: it decides how good the trees are, how reproducible a placement
is and whether email text leaves our servers.

**Open:** does the engine run a model we host or call a third-party model; quality of search and placement
on Russian business email; cost; how the engine version is recorded with each placement; the similarity
threshold below which a chain goes to «Unassigned».

**Touches:** invariants «Explainable placement», «Reproducible placement» and «Access boundary» (the
user's consent when a third-party model is used).

### Sentiment layer

Added 28.10. Stage 2: the sentiment of a thread and of a counterparty within a project, with the emails
and phrases it rests on. Why: the original goal of the product, now a layer over the trees.

**Open:** what is assessed — a thread, a counterparty in a project, both; how an assessment changes as new
emails arrive.

**Touches:** invariants «Explainable placement» and «Reproducible placement». Needs «Projects and
placement» first.

## Projects

### Projects and placement

Added 28.10. The user creates a project by hand with a description; the engine fills the empty project:
finds the matching emails, forms threads and sorts the reply chains under their counterparties
(project → counterparty → thread). New emails: a reply goes to its chain; then the user's rules; then the
engine when it is sure; otherwise «Unassigned». The engine never moves a chain already placed. A reply
chain belongs to at most one project; an email that touches a second project is shown there as a
reference to its chain. A chain with several counterparties is shown under each of them. Why: the core
of the product after the concept change of 28.10.

**Open:** how «Unassigned» is reviewed; what happens to placements when the description changes.

**Touches:** invariants «Explainable placement», «Reproducible placement», «History is kept». Needs «Reply
chains» and «Analysis engine».

### Rules and manual placement

Added 28.10. The user places a chain by hand and writes rules (for example by address, domain or subject)
that place new chains into a project and a thread; a project is re-sorted only by an explicit action that
keeps the placements made by hand. Priority: by hand, then a rule, then the engine. Why: the engine makes
mistakes and the user must be able to fix them for good.

**Open:** what a rule can match on; what happens when two rules disagree.

**Touches:** invariants «History is kept» and «Explainable placement». Needs «Projects and placement».

### Counterparty with several addresses

Added 28.10. One person or company may write from several addresses; merge them into one counterparty of
the tree. Why: otherwise one counterparty splits into several branches.

**Open:** merged by hand, by domain or by the engine.

**Touches:** nothing new.

## Access

### Personal accounts

Added 28.10. Remove organizations: anyone registers as a user on their own, with email confirmation;
invitations, members, administrators and the organization filter go away; every piece of data belongs to
one user. Why: the concept change of 28.10 — a personal tool, not an organization's one.

**Open:** what happens to the organizations and users created by task 0.2 in existing databases.

**Touches:** invariant «Access boundary»; changes FR-1…FR-3 and FR-18, removes FR-9…FR-16 and FR-19. First
task of stage 1.

### Account settings

Added 23.10. What a signed-in user may change after task 0.2: change the password and the email while
signed in, edit the name, delete their account, two-factor authentication, a per-IP limit on sign-in and
registration. Why: task 0.2 covers only joining, signing in and resetting a forgotten password; these
were left out to keep it shippable.

**Open:** which of them the first users need; what deleting a user does to their correspondence
(«History is kept»).

**Touches:** invariant «History is kept» for deletion; «Access boundary» for the email change.

## Mailbox

### Mailbox connection

Added 23.10, changed 28.10. A user connects one or more mailboxes on a page of the app: server, login and
app password over IMAP; the app checks the connection and keeps each mailbox as the user's. Why: without
a connected mailbox there is no correspondence to lay out, and one project's correspondence is spread
over several mailboxes.

Proposed in the explore session:
- IMAP with an app password first (Yandex 360, Mail.ru, Exchange); OAuth for Gmail later.
- Reading never changes the mailbox: the folder is opened read-only and messages are fetched without
  setting the «seen» flag, so unread emails stay unread — a scenario in the spec.
- The mailbox password is stored encrypted with a key from `.env`.

**Open:** does «connect» only check and save or also start reading emails; how a mailbox is disconnected
and what happens to its data; retention.

**Touches:** invariants «Mailbox read-only» and «Access boundary». Needs «Personal accounts» first.

### Reply chains

Added 28.10. Read the emails of all of a user's mailboxes and collect them into reply chains by the
`References` and `In-Reply-To` headers; an email present in two mailboxes (by `Message-ID`) is one
email. Why: the reply chain is the unit the engine places, and it is never split.

**Open:** which folders are read (inbox, sent, all); how far back.

**Touches:** invariant «Mailbox read-only». Needs «Mailbox connection».

## Technical backlog

None yet.
