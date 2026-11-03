# Ideas

Updated 03.11.2026

Ideas not yet planned, by product area, then the technical backlog. `/idea` adds an entry; `/explore`
discusses a raw one.

## Analysis

### Analysis engine

Added 23.10, changed 29.10. Task 1.3 built a local deterministic engine (`text-1`, ADR 0045) that fills
projects and places new chains. Left open: a third-party model for better placement and for the
sentiment of stage 2. Why: text similarity misses meaning that a language model would catch.

**Open:** a model we host or a third-party one; quality on Russian business email; cost; how the user
gives consent before email text goes to a third party.

**Touches:** invariants «Reproducible placement» (a model change is a new engine version) and «Access
boundary» (the user's consent when a third-party model is used).

### Sentiment layer

Added 28.10. Stage 2: the sentiment of a thread and of a counterparty within a project, with the emails
and phrases it rests on. Why: the original goal of the product, now a layer over the trees.

**Open:** what is assessed — a thread, a counterparty in a project, both; how an assessment changes as new
emails arrive.

**Touches:** invariants «Explainable placement» and «Reproducible placement». Needs «Projects and
placement» first.

## Projects

### Edit and delete a project

Added 29.10. The user renames a project, changes its description or deletes it. Why: task 1.3 creates
projects but cannot change them.

**Open:** what happens to the placements when the description changes; whether deleting a project
releases its chains for other projects.

**Touches:** invariant «History is kept».

### A reference in a second project

Added 29.10. An email that touches a second project is shown there as a reference to its chain, which
stays in its own project (ADR 0034). Why: a chain belongs to at most one project, but its topic may
concern two.

**Open:** how the engine finds the second project; how the reference looks in the tree.

**Touches:** invariant «Explainable placement».

### A chain's project in «Переписка»

Added 29.10. The list «Переписка» shows the project and thread of each placed reply chain. Why: the user
sees where a chain went without opening every project.

**Open:** a link to the project page or only its name.

**Touches:** nothing new.

### Edit threads by hand

Added 02.11. The user renames, merges and deletes threads of a project, moves a chain from the project
tree, and moves several chains at once. Why: since task 1.4 a chain is moved only one at a time from its
own page, and a thread the engine named badly keeps its name. Re-sorting also adds engine chains to a
thread kept by hand, even chains that had threads of their own before, and only splitting the thread
undoes that.

**Open:** what happens to the chains of a deleted thread; which name a merged thread keeps.

**Touches:** invariants «History is kept» and «Explainable placement».

### Counterparty with several addresses

Added 28.10. One person or company may write from several addresses; merge them into one counterparty of
the tree. Why: otherwise one counterparty splits into several branches.

**Open:** merged by hand, by domain or by the engine.

**Touches:** nothing new.

### Apply a rule later

Added 03.11. Apply a saved rule from its row on «Правила», or several rules at once, with the same list
of moves and «Применить». Why: since task 1.6 a rule can be applied only right after it is saved;
after «Не сейчас» the only way is to save it again or «Заполнить».

**Touches:** invariant «History is kept» (never a chain placed by hand or taken out).

### Richer rules

Added 03.11. Rules by recipient and by words of the body, conditions joined by «or» and «not», and an
order of rules set by hand. Why: task 1.5 has one condition per rule — sender address, domain or subject
words — and a fixed priority.

**Open:** how the user reads a rule with several conditions; what an explanation shows for it.

**Touches:** invariants «Explainable placement» and «Reproducible placement».

### A rule from a chain

Added 03.11. On the page of a chain the user creates a rule from its sender, domain or subject with its
current project and thread filled in. Why: today a rule is typed on «Правила» by hand.

**Open:** which fields are offered; whether the rule applies to this chain at once.

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
