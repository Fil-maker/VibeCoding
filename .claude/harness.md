# Harness

How this repository's agent harness is set up and why. For agents; English.

## Profile

- Tier: Full
- Requirements: OpenSpec 1.14.3 (checked at generation, 23.10.2026)
- Third-party skills: Matt Pocock's skills (project scope, plugin in `.claude/settings.json`); grill-me / grill-with-docs in `feature` step 2 and `explore`, diagnosing-bugs in `fix`; not used: to-spec, to-tickets, implement
- Languages: talk Russian; agent files English; docs English; commits English; UI Russian
- Modes: guide on; code by subagents; tests two agents (sandbox); commit gate ask; git branch + ff-only; sessions design/code/finish
- Stack: Python + FastAPI (uv, pytest, ruff, pyright strict, SQLAlchemy + Alembic) · React + TypeScript SPA (Vite, pnpm, Vitest, ESLint, Prettier, client generated from OpenAPI) · PostgreSQL in Docker · just · prek
- Invariants: (1) explainable verdicts; (2) mailbox read-only; (3) reproducible assessments, model change visible; (4) interaction history with each counterparty kept, administrator sees all correspondence of the organization; (5) access boundary — employee sees only own correspondence, administrator all of their organization, email text goes to a third-party service only with the administrator's consent
- Decisions home: `docs/adr/` (ADR files), `docs/decisions.md` is the ADR index; decision draft script writes ADRs after confirmation

## Approved file plan (R7, 23.10.2026)

Generate on `main` (no product code yet). Command entry is `just` everywhere the spec says `make`.

- Root: `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `justfile` (setup, check, format, test; dev/db/test-db come with task 0.1), `pyproject.toml` (dev tooling only for harness scripts), `.pre-commit-config.yaml` (prek: hygiene, ruff, pyright, doc links/facts, journal guard, Conventional Commits commit-msg), `.gitignore`, `.env.example`.
- `docs/`: `README.md`, `prd.md` 0.1 draft, `domain.md`, `architecture.md` (status: no code yet), `tech.md`, `decisions.md` (ADR index), `adr/README.md` + `0001` FastAPI backend, `0002` React SPA, `0003` PostgreSQL (from this interview's decisions), `plan.md` with task 0.1 «Application skeleton» (FastAPI + React + Postgres, `just dev`; technical, skip_specs), `ideas.md` (incl. the analysis-engine question), `tech-debt.md`, `setup.md`, `guide/README.md`, `journal/README.md`, `releases/README.md`.
- `openspec/`: `openspec init` (Claude Code) + `config.yaml` from Appendix A.
- `.claude/`: `settings.json` (foreground agents, journal hook, script permissions, enabledPlugins mattpocock-skills, LSP plugins if available), `rules/` ×12, `agents/` ×8, `hooks/protect_journal.py`, `hooks/sandbox_guard.py`, `skills/` ×10 (feature with code-step.md and delta-rules.md; fix; finish; commit; idea; explore; document; test; journal; release) with their scripts (section 9: change state, task card, TDD sandbox, decision draft, doc plan, commit preflight, test runner, session digest, journal checker, next version).
- `scripts/check_doc_links.py`, `scripts/check_doc_facts.py`.
- Not now: application code and docker-compose (task 0.1 via `/feature`), `.claude/launch.json` (with the dev server).
- Delivery: the cloud session cannot push (no GitHub account linked). Before committing, ask the user: connect GitHub in Settings → Connectors, or link a folder on their computer and write the files there.
- The user runs `/setup-matt-pocock-skills` once after generation (it asks questions).

## Recon at generation (23.10.2026)

- Generation moved from the cloud session to the user's laptop: the Claude desktop app on Windows 11.
- Working copy: `D:\Projects\AI_projects\VibeCoding`, a fresh clone of github.com/Fil-maker/VibeCoding (still empty, `main`). No `gh`; push is not needed until the first `/release`.
- Tools found: git 2.45, node 24.20, npm 11.19, Python 3.12 (as `python`; no `python3`), Docker 29.9. Installed at generation with the user's consent: uv 0.13.5 and just 1.59.0 (winget), prek 0.5.7 (`uv tool install`), pnpm 12.15 and openspec 1.14.3 (`npm -g`).
- Every script runs as `uv run --no-project python …`, never `python3`.

## Recon (R0, 22.10.2026)

- Repository: github.com/Fil-maker/VibeCoding, public, empty (no commits), default branch `main`.
- Working copy: cloud session clone at /home/claude/fil-maker/vibecoding; read-only to GitHub (no GitHub account linked to the session, push unavailable).
- Stack: none yet (no manifests, CI, Makefile, Docker files).
- Existing agent setup: none (no CLAUDE.md, AGENTS.md, .claude/, docs/, openspec/).
- Tools in the session: node 22.22.0, python3 3.13.16, uv 0.11.32, docker 29.9.1, gh 2.89.0 (not authenticated), git 2.43.0, claude 2.1.308; openspec not installed; no plugins enabled.
- Host: Claude desktop app on Windows (laptop) → foreground agents setting applies (section 7.3).

## Components

| Component | Path | Why |
|---|---|---|
| Entry map | `CLAUDE.md` | What the project is, docs and rules map, commands, invariants, workflow |
| Product docs | `docs/` (index `docs/README.md`), ADRs in `docs/adr/` | Full tier SDD chain plus tech-debt, setup, guide, journal, releases (R3-Q1..Q3) |
| Requirements | `openspec/` (`config.yaml` with project context and rules) | OpenSpec owns requirements and deltas (R2-Q1) |
| Rules ×12 | `.claude/rules/` | Path-scoped conventions per R4-Q4 |
| Agents ×8 | `.claude/agents/` | Code by subagents, two-agent tests, review, docs, journal (R6-Q1..Q3) |
| Skills ×10 | `.claude/skills/{feature,fix,finish,commit,idea,explore,document,test,journal,release}/` | Guided flows per R5-Q1; guide mode on (R1-Q7) |
| Change state, briefs | `.claude/skills/feature/scripts/change_state.py` (+ `harness_docs.py`) | Skills start from facts; a fresh session finds where a change stopped |
| TDD sandbox | `.claude/skills/feature/scripts/tdd_sandbox.py` (+ `sandbox_*.py`) | Tests written before and apart from the code (R6-Q2) |
| Task card | `.claude/skills/finish/scripts/task_card.py` | `/finish` checks acceptance without reading whole docs |
| Decision draft | `.claude/skills/document/scripts/session_facts.py` (+ `facts_*.py`) | Decisions recorded when made; ADRs only after confirmation (R3-Q4, R2-Q4) |
| Doc plan | `.claude/skills/document/scripts/doc_plan.py` | Small portions for the cheap doc-writer; `EXPECTED_DOCS` shared with the preflight |
| Commit preflight | `.claude/skills/commit/scripts/preflight.py` | Blocks what must never be committed (R5-Q3 gate) |
| Session digest, journal checker | `.claude/skills/journal/scripts/` | Journal written from transcripts, checked by script (R3-Q2) |
| Next version | `.claude/skills/release/scripts/next_version.py` | SemVer from Conventional Commits (R3-Q3) |
| Test runner | `.claude/skills/test/scripts/run_tests.py` | One way to run suites; a skipped suite is never a pass |
| Doc checkers | `scripts/check_doc_links.py`, `scripts/check_doc_facts.py` (+ `doc_scan.py`) | Links, headings, named paths and recipes stay true |
| Check runner | `scripts/run_checks.py` | `just check` runs every check to the end under PowerShell |
| Commit message check | `scripts/check_commit_msg.py` | Conventional Commits enforced by the `commit-msg` hook |
| Journal guard | `.claude/hooks/protect_journal.py` | Committed notes are append-only (agent hook and git hook) |
| Sandbox guard | `.claude/hooks/sandbox_guard.py` | `test-writer` cannot read the main checkout (R6-Q4) |
| Settings | `.claude/settings.json` | Foreground agents, journal hook, script permissions, plugins (mattpocock-skills, pyright-lsp, typescript-lsp) |
| Commands, git hooks | `justfile`, `.pre-commit-config.yaml`, root `pyproject.toml` | `just` entry points (R4-Q2), prek (R4-Q3), harness tooling and the product version |

## Decisions

| Date | Id | Decision | Alternatives | Reason (user's words) | Who |
|---|---|---|---|---|---|
| 23.10.2026 | R1-Q1 | Product: an app that analyses the sentiment of emails so the user does not have to form an opinion about a counterparty by hand | — | «Делаем приложение для анализа настроения писем, чтобы не приходилось составлять мнение о контрагенте вручную» | [human] |
| 22.10.2026 | R1-Q2 | Stage: idea | prototype · used by others | accepted the recommendation (no code yet) | [human] |
| 22.10.2026 | R1-Q3 | Solo | solo with a client · team | accepted the recommendation | [human] |
| 22.10.2026 | R1-Q5 | Docs and commits in English, UI in Russian | all Russian · all English | accepted the recommendation | [human] |
| 23.10.2026 | R1-Q4 | Tier: Full | Standard (recommended) · Lite | not given | [human] |
| 23.10.2026 | R1-Q6 | Invariants: explainable verdicts (every counterparty assessment links to the emails and phrases it rests on); mailbox read-only (never send, delete or modify emails); reproducible (same emails and settings give the same assessment; a change of analysis model is visible in the result); keep the history of interaction with each counterparty so that an administrator or manager has access to all the correspondence | email privacy (no third-party service without consent, full deletion) — proposed, not chosen | own invariant: «Сохраняем историю взаимодействия с контрагентом, чтобы администратор/начальник имел доступ ко всем перепискам» | [human] |
| 23.10.2026 | R1-Q6 | Fifth invariant, access boundary: an employee sees only their own correspondence, an administrator sees all correspondence of their organization; email text is not sent to a third-party service without the administrator's consent | roles only, external services later · keep four | accepted the recommendation | [human] |
| 23.10.2026 | R2-Q1 | Requirements in OpenSpec | own specs in docs/specs · issue tracker | accepted the recommendation | [human] |
| 23.10.2026 | R2-Q2 | Third-party skills: Matt Pocock's skills | none (recommended) · pstack | not given | [human] |
| 23.10.2026 | R2-Q3 | Matt Pocock's skills installed at project scope (.claude/settings.json) | user scope | accepted the recommendation | [human] |
| 23.10.2026 | R2-Q4 | Decisions home: docs/adr/, docs/decisions.md is the ADR index | decisions.md table | accepted the recommendation | [human] |
| 23.10.2026 | R3-Q1 | Optional docs: tech-debt.md, setup.md, guide/ (plus domain.md, tech.md, ideas.md by tier) | fewer | accepted the recommendation | [human] |
| 23.10.2026 | R3-Q2 | Work journal in docs/journal/, append-only, guarded | none | accepted the recommendation | [human] |
| 23.10.2026 | R3-Q3 | Releases from day one: SemVer from Conventional Commits, CHANGELOG.md, release notes, /release | later, at the first deploy (recommended) | not given | [human] |
| 23.10.2026 | R3-Q4 | Decision capture through the decision draft and a script, confirmed by the user | direct writes | accepted the recommendation | [human] |
| 23.10.2026 | R4-Q1 | Backend: Python + FastAPI (uv, pytest, ruff, pyright strict, SQLAlchemy + Alembic) | Django · TypeScript/Node | accepted the recommendation | [human] |
| 23.10.2026 | R4-Q1 | UI: React + TypeScript (Vite) SPA talking to the FastAPI API | server-rendered Jinja + HTMX (recommended) | not given | [human] |
| 23.10.2026 | R4-Q1 | Database: PostgreSQL in Docker | SQLite | accepted the recommendation | [human] |
| 23.10.2026 | R4-Q2 | Command entry point: justfile | Makefile (spec default; recommendation changed because the user's laptop runs Windows) | accepted the recommendation | [human] |
| 23.10.2026 | R4-Q1 | Frontend tooling: pnpm, Vitest, ESLint, Prettier, tsc strict; API client generated from OpenAPI | npm · Biome | accepted the recommendation | [human] |
| 23.10.2026 | R4-Q3 | Git hooks manager: prek | lefthook · none | accepted the recommendation | [human] |
| 23.10.2026 | R4-Q4 | Rules: docs, docs-sync, config, testing, naming, code-quality (Python and TypeScript), versioning, server-architecture, data-access, database, frontend, api-contract; domain rules deferred | domain rules now | accepted the recommendation | [human] |
| 23.10.2026 | R4-Q5 | Quality bar: strict | moderate | accepted the recommendation | [human] |
| 23.10.2026 | R5-Q1 | Skills: feature, fix, finish, commit, idea, explore, document, test, journal, release; redesign and procedural skills deferred | + redesign · + procedural | accepted the recommendation | [human] |
| 23.10.2026 | R5-Q2 | Git: a branch per change, merged fast-forward, no PRs | PR per change · trunk | accepted the recommendation | [human] |
| 23.10.2026 | R5-Q3 | Commit gate: ask before each commit | automatic | accepted the recommendation | [human] |
| 23.10.2026 | R5-Q4 | Sessions: design / code / finish in fresh sessions with a handoff file; minor changes in one | one session | accepted the recommendation | [human] |
| 23.10.2026 | R6-Q1 | Code written by subagents; the main session orchestrates and reviews | main session writes code | accepted the recommendation | [human] |
| 23.10.2026 | R6-Q2 | Tests: two agents, tests written in a sandbox before the code | test-first by code-writer · with the code | accepted the recommendation | [human] |
| 23.10.2026 | R6-Q3 | Agents: code-writer, test-writer, invariant-reviewer, journal-writer on sonnet; test-auditor, doc-writer, doc-checker, flow-checker on haiku | without flow-checker · all on sonnet | accepted the recommendation | [human] |
| 23.10.2026 | R6-Q4 | Hooks: journal guard, sandbox guard, foreground agents | formatter after edits (not recommended: prek formats at commit) | accepted the recommendation | [human] |
| 23.10.2026 | R6-Q5 | Manual flow checks with flow-checker in the built-in browser on a local preview server | none | accepted the recommendation | [human] |
| 23.10.2026 | R7 | File plan approved; generation in a fresh session | generate in this session | accepted the recommendation | [human] |
| 22.10.2026 | R1-Q7 | Guide mode on | terse | accepted the recommendation | [human] |
| 23.10.2026 | G-1 | Generate on the laptop in `D:\Projects\AI_projects\VibeCoding` (a clone of the GitHub repo) | clone into PycharmProjects (recommended) · empty folder with `git init` | «Выберу папку сам» | [human] |
| 23.10.2026 | G-2 | Install the missing tools: uv, just, prek, pnpm, openspec | the user installs them | accepted the recommendation | [human] |
| 23.10.2026 | G-3 | Additions to the R7 plan: `scripts/run_checks.py` (a `just check` that runs every check to the end needs logic PowerShell recipes cannot hold), `scripts/check_commit_msg.py` (the commit-msg hook), sibling modules of the larger scripts (500-line limit) | shell logic in the justfile; a third-party commit-msg hook | needed to meet the spec on Windows | [AI → to review] |
| 23.10.2026 | G-4 | `check_doc_facts.py` skips existence checks in `docs/plan.md` and `docs/ideas.md`, and on lines that say «planned» or «(task …)» | marking every future name by hand | plan and ideas describe what does not exist yet by design | [AI → to review] |
| 23.10.2026 | G-5 | `just check` runs only the read-only hygiene hooks; `end-of-file-fixer` and `trailing-whitespace` run at commit | all hooks in check | `check` must stay read-only | [AI → to review] |

## Deferred

- Sentiment analysis engine (local model vs LLM) — a product decision tied to the reproducibility and access-boundary invariants; settle it in the first `/explore`.
- Domain rules (`access-control.md`, `sentiment-analysis.md`) — nothing to say beyond the invariants yet; add them with the first specs of those capabilities.
- `/redesign` — no design system yet; add it when the UI has one.
- Procedural skills (`db-migration`, `contract-change`) — add one when its procedure has repeated twice.
- Formatter-after-edit hook — prek formats at commit; add it if unformatted code keeps reaching review.
- pstack — not chosen in R2-Q2.

## Bootstrap status

- [x] R0 recon · [x] R1 · [x] R2 · [x] R3 · [x] R4 · [x] R5 · [x] R6 · [x] R7 file plan approved (23.10.2026; generation in a fresh session)
- [x] docs · [x] framework · [x] CLAUDE.md · [x] rules · [x] agents · [x] scripts and hooks · [x] skills · [x] settings and git hooks (23.10.2026)
- [x] validated (23.10.2026; see «Validation») · [ ] committed
- After the commit, the user runs `/setup-matt-pocock-skills` once and restarts the desktop app (new PATH for uv, just, prek; new settings and agents load in new sessions).

## Validation

23.10.2026: `just check` all PASS (ruff, ruff format, pyright strict, doc links, doc facts, `openspec validate --specs --strict`, hygiene hooks); every skill, agent and rule frontmatter parses; `--help` runs for all 14 scripts; the skills' `!` state commands run from the root; `openspec instructions` shows every project rule (proposal 3, specs 4, design 3, tasks 3); journal guard: a new note and `README.md` exit 0 — the blocking case (committed note → exit 2) was tested by its author in a throwaway repo, since this repo had no commits; `prek install` done. Not tested: the database path of `tdd_sandbox.py create` and `run_tests.py db` (no Docker database before task 0.1), vitest output parsing (no frontend yet), the `/idea` dry run (project skills load only in sessions started after them), the LSP plugin ids (`pyright-lsp`, `typescript-lsp` are expected in claude-plugins-official, not verified).
