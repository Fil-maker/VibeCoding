# VibeCoding

A personal app that gathers the correspondence of a user's projects from several mailboxes and lays it out
as trees: project → counterparty → thread; sentiment comes later as a layer over the trees. Anyone
registers on their own; there are no organizations. Stage: skeleton and sign-in are built (tasks 0.1,
0.2, still with organizations); stage 1 «Project trees» is next.

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
just setup       # install the tooling and the git hooks
just dev         # start the dev stack in Docker (database, backend, SPA) with live reload
just db          # start only the database, detached, and wait until it is healthy
just check       # read-only: every check to the end, incl. doc links and facts; fails on warnings
just format      # autofix formatting and lint
just test        # unit tests
just test-db     # database tests
just test-all    # unit and database tests
just api-client  # regenerate the SPA's API client from the backend's OpenAPI schema
just demo-mail   # load the demo mailboxes into GreenMail (also: status, add-new)
```

Python scripts run as
`uv run --no-project python <script> . <command>`; there is no `python3` on this machine.

## Architecture in brief

Task 0.1 has built the skeleton:

- Backend: FastAPI (Python) in `backend/`, modules `backend/app/modules/<module>/` with
  router → service → domain logic and repository; platform code in `backend/app/platform/`. The health module is the first.
- SPA: React + TypeScript (Vite) in `frontend/`, UI in Russian; talks to the backend only
  through the client generated from the OpenAPI schema (`frontend/src/api/generated/`).
- PostgreSQL in Docker (`docker-compose.yml`); the SQLAlchemy declarative base and Alembic are set up, with an
  empty baseline revision and no models yet.
- The mailbox reader and the analysis engine are not chosen yet (`docs/ideas.md` «Analysis engine»).
- Details: `docs/architecture.md`.

## Product invariants

IMPORTANT: these are the product's core promises. Never trade them for convenience.

- **Mailbox read-only:** never send, delete or modify emails in a mailbox.
- **Explainable placement:** every placement of a reply chain in a project and a thread says why — by
  hand, by a user's rule or by the engine with its similarity; every sentiment assessment links to the
  emails and phrases it rests on.
- **Reproducible placement:** the same emails, project description, rules and engine version give the
  same placement and assessment; a change of the engine's model is visible in the result.
- **History is kept:** the correspondence history of every project is kept; the engine never moves an
  already placed reply chain — only the user does, by hand or by an explicit re-sorting that keeps
  placements made by hand.
- **Access boundary:** a user sees only their own mailboxes, projects and correspondence; if the engine
  uses a third-party model, email text goes there only with the user's consent.

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

## Agent skills

### Issue tracker

Work is tracked in the project docs (`docs/plan.md`, `docs/ideas.md`, `docs/tech-debt.md`), not GitHub
Issues. See `.claude/skills-config/issue-tracker.md`.

### Domain docs

Single-context: glossary in `docs/domain.md` «Glossary», ADRs in `docs/adr/`; no CONTEXT.md file. See
`.claude/skills-config/domain.md`.
