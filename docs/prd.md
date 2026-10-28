# Product requirements

Version 0.4 · 28.10.2026 · **Draft**

Changes in 0.4: new concept — a personal tool without organizations: correspondence history laid out as
trees by project across several mailboxes; sentiment becomes a later layer over the trees.

Changes in 0.3: task 0.2 «Sign-in and organization» done in stage «0. Skeleton».

Changes in 0.2: stage «0. Skeleton» done by task 0.1.

Changes in 0.1: first draft from the harness interview; everything not said there is TBD.

## Problem

Someone who runs several projects at once corresponds about each of them with many people and from
several mailboxes. The history of a project is scattered: one topic lives in several reply chains, a
reply lands in another mailbox, emails of different projects are mixed in one inbox. To recall what was
agreed with whom, the person rereads the mailboxes by hand.

## Users

- **User** — anyone who registers on their own; runs one or more projects, corresponds about them from
  one or more mailboxes and wants the correspondence of each project gathered in one place.

TBD: the typical number of mailboxes and projects of a user, which mail systems they use.

## Value proposition

The user describes a project in a few sentences; the app finds its correspondence in every connected
mailbox and lays it out as a tree: project → counterparty → thread. New emails take their place in the
tree by themselves, and every placement says why. Later a sentiment layer over the tree shows how the
relationship with each counterparty of a project goes, with the emails and phrases it rests on.

## Product principles

These are the product invariants; `CLAUDE.md` «Product invariants» holds them for agents.

1. **Mailbox read-only.** The app never sends, deletes or modifies emails.
2. **Explainable placement.** Every placement of a reply chain in a project and a thread says why: by
   hand, by a user's rule or by the engine with its similarity. Every sentiment assessment links to the
   emails and phrases it rests on.
3. **Reproducible placement.** The same emails, project description, rules and engine version give the
   same placement and the same assessment; a change of the engine's model is visible in the result.
4. **History is kept.** The correspondence history of every project is kept. The engine never moves a
   reply chain that is already placed; only the user does, by hand or by an explicit re-sorting of the
   project, which keeps the placements made by hand.
5. **Access boundary.** A user sees only their own mailboxes, projects and correspondence. If the engine
   uses a third-party model, email text goes there only with the user's consent.

## Business functions

- Register an account and sign in; no organization.
- Connect several mailboxes read-only.
- Collect the emails of all mailboxes into reply chains; an email present in two mailboxes is one email.
- Create a project by hand with a description.
- Fill an empty project from its description: the engine finds the matching emails, forms threads (topics
  made of whole reply chains) and sorts the chains into them under their counterparties.
- Place new emails: a reply goes to its chain; then the user's rules; then the engine when it is sure;
  otherwise «Unassigned» of the project. Priority: by hand, then a rule, then the engine.
- Rules and placement by hand; re-sort a project by an explicit action.
- Show an email that touches two projects in the second project as a reference to its chain.
- Later: the sentiment of a thread and of a counterparty within a project.

## User flow

Register → confirm the email → connect one or more mailboxes → create a project with a description → the
engine fills the tree → the user reviews «Unassigned» and fixes placements by hand or by a rule → new
emails take their place in the tree.

## Stages and scope

| Stage | Scope | Status |
|---|---|---|
| 0. Skeleton | The application starts locally: backend, SPA, database; organizations, sign-in, invitations and members | ✅ done |
| 1. Project trees | Personal accounts instead of organizations, several mailboxes, reply chains, projects filled by the engine, rules and placement by hand | 💭 idea |
| 2. Sentiment | Sentiment of threads and counterparties over the trees | 💭 idea |

## Metrics

TBD.

## Risks

- The quality of the engine's search and placement on Russian business email decides whether the tree is
  trusted: see [ideas.md](ideas.md#analysis-engine).
- Whether the engine uses a third-party model decides when the user's consent is needed.
- Mailbox access needs credentials of a real mail system: TBD which systems and protocols.
- One counterparty may write from several addresses: TBD whether they are merged.
