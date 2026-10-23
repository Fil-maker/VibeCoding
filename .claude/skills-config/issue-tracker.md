# Issue tracker: project docs

Read by Matt Pocock's skills (`code-review` and any skill that talks about "the issue tracker"). This repo
has no GitHub Issues workflow: work is tracked in the project docs.

## Where work lives

- **Tasks** with «Done when»: `docs/plan.md`.
- **Ideas** not planned yet and the technical backlog: `docs/ideas.md`, added through `/idea`.
- **Defects** that work wrong now: `docs/tech-debt.md`.
- **Requirements** `FR-N`: only in OpenSpec (`openspec/specs/`, deltas in `openspec/changes/`).

These are product docs: they change only with the user's approval.

## When a skill says "publish to the issue tracker"

Draft the entry and show it to the user; write it only after they agree. An idea goes through `/idea`, a
defect to `docs/tech-debt.md`, a task to `docs/plan.md`.

## When a skill says "fetch the relevant ticket"

Read the task by its id in `docs/plan.md`, or the entry in `docs/ideas.md` / `docs/tech-debt.md`.

## Not used

- `to-spec`, `to-tickets`, `implement`, `wayfinder`: requirements live only in OpenSpec and work goes
  through `/feature`, `/fix`, `/finish`.
- Pull requests: each change is a branch merged into `main` with `--ff-only`. In `code-review`, the task
  references are the `docs/plan.md` ids in commit messages (the `Plan` footer).
