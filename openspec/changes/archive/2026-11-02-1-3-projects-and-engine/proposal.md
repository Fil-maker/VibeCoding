# Proposal

## Why

After task 1.2 the user sees every reply chain of every mailbox in one long list, but the history of a
project is still scattered among chains of other projects, and the user still sorts it in their head
(`docs/prd.md` «Problem»). The value of the product is the tree: the user describes a project and the
app lays out its correspondence as project → counterparty → thread, and keeps it laid out as new emails
arrive (`docs/prd.md` «Value proposition»). This is task 1.3 of `docs/plan.md`, the third step to the
first version shown to the customer.

## What Changes

- The user creates a project with a name and a description and sees the list of their projects.
- «Заполнить» runs the engine over the user's reply chains that are in no other project: a chain whose
  similarity to the description is at or above the sure threshold goes to a thread of the project, a
  chain between the lower and the sure threshold goes to «Неразобранное» of the project, a chain below
  the lower threshold stays out.
- The engine forms the threads of a project by grouping its chains by their similarity to each other; a
  thread is named by the subject of its earliest chain.
- The project page shows the tree: counterparties (participant addresses), under each the threads with
  that counterparty's chains, and «Неразобранное». A chain with several counterparties is shown under
  each of them.
- Every placed chain shows why it is there: «Движок», its similarity in percent and the engine version.
- «Заполнить» on a filled project asks for confirmation and rebuilds the engine's placements from the
  same emails; the same emails, description and engine version give the same tree.
- After each mailbox read, a new reply chain is placed: into the most similar filled project's closest
  thread or a new thread, or into «Неразобранное» of that project, or nowhere. A continuation stays in
  its chain's place; the engine never moves a placed chain.
- The engine is local and deterministic (ADR 0045): text similarity over the subject and text of the
  chain, no third-party model; email text never leaves the installation.

Out of scope, deferred to `docs/ideas.md`:
- Placing and moving a chain by hand, rules, re-sorting that keeps manual placements (task 1.4).
- Editing a project's name or description, deleting a project («Edit and delete a project»).
- Showing an email that touches a second project there as a reference (ADR 0034).
- Merging the addresses of one counterparty («Counterparty with several addresses»).
- A third-party model and the user's consent to it («Analysis engine»).
- Showing a chain's project in «Переписка».

## Capabilities

### New Capabilities

- `projects`: creating projects with a description, listing them and showing a project's tree of
  counterparties, threads and «Неразобранное».
- `chain-placement`: placing reply chains into projects and threads — filling a project by the engine,
  placing new chains, explaining each placement and keeping it reproducible. Task 1.4 adds placement by
  hand and rules here.

### Modified Capabilities

None: FR-30 and FR-31 keep their behavior; FR-17 and FR-21 already cover the new pages and data, and
the new requirements carry their own negative scenarios.

## Impact

- Product invariants: **Explainable placement** (each placement stores and shows its kind, similarity
  and engine version), **Reproducible placement** (a deterministic engine whose thresholds belong to its
  version), **History is kept** (the engine never moves a placed chain; only the explicit «Заполнить»
  rebuilds a project), **Access boundary** (projects, threads and placements belong to one user; no
  email text leaves the installation, so no consent is needed).
- Backend: a new module `projects` (projects, threads, placements, the tree, filling and placing), a
  local engine in `platform/`, placement of new chains after each mailbox read, new tables and
  migration `0005`.
- New dependency: `snowballstemmer` for Russian and English word stems.
- SPA: pages «Проекты» and a project page with the tree and «Заполнить»; a link from the start page; the
  regenerated API client.
- Demo: the demo mail lays out into three projects (office renovation, equipment purchase, conference).
- Docs: `docs/domain.md` (requirements map, glossary: Counterparty, Thread, Placement, Engine version),
  `docs/architecture.md`, `docs/tech.md`, a guide article on the engine, `docs/ideas.md`.
