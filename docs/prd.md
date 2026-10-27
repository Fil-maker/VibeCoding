# Product requirements

Version 0.3 · 27.10.2026 · **Draft**

Changes in 0.3: task 0.2 «Sign-in and organization» done in stage «0. Skeleton».

Changes in 0.2: stage «0. Skeleton» done by task 0.1.

Changes in 0.1: first draft from the harness interview; everything not said there is TBD.

## Problem

Someone who corresponds with many counterparties (clients, suppliers, partners) has to form an opinion of
each of them by hand: reread the threads, remember the tone, notice when a relationship turns sour. The
opinion lives in one person's head, is not explained, and is lost when that person leaves.

## Users

- **Employee** — corresponds with counterparties from their own mailbox and wants a quick, explained
  picture of each counterparty.
- **Administrator** — the head of the organization or a manager; sees all correspondence of the
  organization and the history of interaction with every counterparty, and decides whether email text
  may go to a third-party service.

TBD: the size of a typical organization, which mail systems it uses.

## Value proposition

The app reads the correspondence and builds the sentiment of every counterparty for the user, so nobody
has to form the opinion by hand. Every assessment says which emails and phrases it rests on.

## Product principles

These are the product invariants; `CLAUDE.md` «Product invariants» holds them for agents.

1. **Explainable verdicts.** Every assessment of a counterparty links to the emails and phrases it rests on.
2. **Mailbox read-only.** The app never sends, deletes or modifies emails.
3. **Reproducible assessments.** The same emails and settings give the same assessment; a change of the
   analysis model is visible in the result.
4. **History is kept.** The history of interaction with each counterparty is kept; the administrator sees
   all correspondence of the organization.
5. **Access boundary.** An employee sees only their own correspondence; the administrator sees all
   correspondence of their organization; email text goes to a third-party service only with the
   administrator's consent.

## Business functions

TBD. Candidates from the interview: connect a mailbox (read-only), group emails by counterparty, assess
the sentiment of a counterparty with its evidence, show the history of interaction, organization
roles (employee, administrator), consent to a third-party analysis service.

## User flow

TBD.

## Stages and scope

| Stage | Scope | Status |
|---|---|---|
| 0. Skeleton | The application starts locally: backend, SPA, database; organizations, sign-in, invitations and members | ✅ done |
| 1. First assessment | TBD | 💭 idea |

## Metrics

TBD.

## Risks

- The choice of the analysis engine (a local model or an external LLM) decides both reproducibility and
  the access boundary: see [ideas.md](ideas.md#analysis-engine).
- Mailbox access needs credentials of a real mail system: TBD which systems and protocols.
