# Ideas

Updated 29.10.2026

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

### OAuth sign-in to Gmail and Outlook

Added 29.10. Connect Gmail and Outlook through OAuth instead of an app password. Why: task 1.2 connects
mailboxes over IMAP with an app password only, which these services make hard or forbid.

**Open:** which providers first; how a revoked grant is shown.

**Touches:** invariants «Mailbox read-only» (read-only scopes) and «Access boundary».

### More folders and reading depth

Added 29.10. Read folders other than Inbox and Sent and let the user set how far back a mailbox is read.
Why: task 1.2 reads Inbox and Sent of the last 12 months only; some correspondence sits in other folders
or is older.

**Open:** which folders by default; what a smaller depth does to emails already read («History is kept»).

**Touches:** invariant «History is kept».

### Attachments' content and search

Added 29.10. Keep the content of attachments and search the text of emails and attachments. Why: task 1.2
keeps only attachment names, and the user cannot find an agreement by a word.

**Open:** size limits; which file types are read.

**Touches:** invariant «Access boundary»; storage size.

### Deleting a disconnected mailbox's emails

Added 29.10. Let the user delete the emails and reply chains read from a disconnected mailbox. Why: task
1.2 keeps them after disconnecting and offers no way to delete them.

**Open:** what happens to chains with emails from other mailboxes and to placements of task 1.3.

**Touches:** invariant «History is kept».

### Encryption key rotation

Added 29.10. Change the key that encrypts mailbox passwords without reconnecting every mailbox. Why: a
lost or changed key now makes every mailbox fail to sign in until it is reconnected.

**Open:** how both keys coexist during the change.

**Touches:** nothing new.

## Technical backlog

None yet.
