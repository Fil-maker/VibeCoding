# VibeCoding

An app that analyses the sentiment of emails, so that nobody has to form an opinion of a counterparty by
hand. For the employees of an organization and its administrator. Stage: idea, no code yet; task 0.1
creates the application skeleton.

Talk to the user in Russian.

## Docs map

Docs follow spec-driven development. `docs/README.md` is the index, and every docs folder has its
own `README.md`: start from an index and read only what the task needs.

| Need | Read |
|---|---|
| What the product is and why | `docs/prd.md` |
| Requirements `FR-x` with scenarios | `openspec/specs/<capability>/spec.md`; map — `docs/domain.md` «Requirements map» |
| Glossary, lifecycles, explanations | `docs/domain.md` |
| How the system is built | `docs/architecture.md` |
| Stack, commands, env vars | `docs/tech.md` |
| Why something was decided | `docs/decisions.md` (index) → `docs/adr/` |
| The task and its «Done when» | `docs/plan.md`; backlog `docs/ideas.md`; defects `docs/tech-debt.md` |
| How a part works | `docs/guide/` |
| History of a change | `docs/journal/` |
| How the agent harness is set up | `.claude/harness.md` |

FR numbers are stable; never renumber them. Link to sections by heading, not number.

## Rules

Path-scoped rules in `.claude/rules/` load when you touch matching files; open the one that
applies before editing.

| Rule | Covers |
|---|---|
| `docs.md` | Where each fact lives, doc headers, requirement format, ADRs, append-only journal |
| `docs-sync.md` | Which docs a code change must update |
| `config.md` | Env vars, tool configs, `justfile`, hooks, version pins |
| `testing.md` | Test layers, structure, determinism, what never to do with a red test |
| `naming.md` | File, function and term naming |
| `code-quality.md` | Strict typing, errors, boundaries, size limits — Python and TypeScript |
| `versioning.md` | SemVer from Conventional Commits, releases, CHANGELOG |
| `server-architecture.md` | Backend layers and module boundaries |
| `data-access.md` | Queries, transactions, the owner filter, databases |
| `database.md` | Schema, migrations, columns |
| `frontend.md` | The React SPA: data loading, text, escaping, styling |
| `api-contract.md` | The OpenAPI contract and the generated client |

## Commands

```bash
just setup     # install the tooling and the git hooks
just check     # read-only: every check to the end, incl. doc links and facts; fails on warnings
just format    # autofix formatting and lint
just test      # unit tests
just test-all  # unit and database tests
```

`just dev`, `just db`, `just test-db` are planned (task 0.1). Python scripts run as
`uv run --no-project python <script> . <command>`; there is no `python3` on this machine.

## Architecture in brief

All of it is planned (task 0.1 creates it):

- Backend: FastAPI (Python) in `backend/` (planned), modules `backend/app/modules/<module>/` with
  router → service → domain logic and repository; platform code in `backend/app/platform/` (planned).
- SPA: React + TypeScript (Vite) in `frontend/` (planned), UI in Russian; talks to the backend only
  through the client generated from the OpenAPI schema (`frontend/src/api/generated/`, planned).
- PostgreSQL in Docker; SQLAlchemy models, Alembic migrations.
- The mailbox reader and the analysis engine are not chosen yet (`docs/ideas.md` «Analysis engine»).
- Details: `docs/architecture.md`.

## Product invariants

IMPORTANT: these are the product's core promises. Never trade them for convenience.

- **Explainable verdicts:** every assessment of a counterparty links to the emails and phrases it rests on.
- **Mailbox read-only:** never send, delete or modify emails in a mailbox.
- **Reproducible assessments:** the same emails and settings give the same assessment; a change of the
  analysis model is visible in the result.
- **History is kept:** the interaction history with each counterparty is kept; the administrator sees
  all correspondence of the organization.
- **Access boundary:** an employee sees only their own correspondence, the administrator all of their
  organization; email text goes to a third-party service only with the administrator's consent.

## Conventions

- Language: code, identifiers, comments, docs and commit messages in English; UI text in Russian.
- Strict: pyright strict and `tsc --strict`, lint warnings are errors, no escape hatches without a reason
  in the same comment, files aim at 300 lines and fail at 500. Details: `.claude/rules/code-quality.md`.
- Secrets live only in `.env`; a new env var also goes to `.env.example` and `docs/tech.md`.
- Never loosen a check (type checker option, lint rule, assertion, git hook) without the user's approval.

## Workflow

- One task from `docs/plan.md` = one change, one branch, one journal note. Read the task, its FRs
  and the related architecture sections before coding; ask when requirements are ambiguous.
- Behavior changes go through OpenSpec: delta specs approved by the user before the code.
- Skills: `/explore` → `/idea` | `/feature` | `/fix` → `/finish` (`/document`, `/journal`, `/commit`,
  `/release`); `/test` runs tests. Alignment comes from Matt Pocock's skills: `grill-me` /
  `grill-with-docs` in `/feature` and `/explore`, `diagnosing-bugs` in `/fix`; never `to-spec`,
  `to-tickets` or `implement` — requirements live only in OpenSpec and commits go through `/commit`.
- A change runs in fresh sessions: design up to approval, code, `/finish`; the next session reads the
  change's `openspec/changes/<change>/handoff.md`. A minor change runs in one session.
- Record each decision the moment the user makes it, with the reason as given:
  `uv run --no-project python .claude/skills/document/scripts/session_facts.py . decide --what "…" --why "…" --who human`.
- Delegation: code and tests are written by Sonnet subagents (`code-writer`, `test-writer` in the TDD
  sandbox) from your brief; you review the diff against the brief and never fix their defects by hand.
- Git: a branch `<type>/<change>` per change, merged into `main` with `--ff-only`, no PRs. Commit only
  through `/commit`, when the user agrees. Never `--no-verify`, never amend.
- When compacting, keep the current task id, the change name and branch, the step of the flow, the
  modified files, and the latest check and test results.
