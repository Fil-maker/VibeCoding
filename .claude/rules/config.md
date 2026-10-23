---
paths:
  - ".env.example"
  - "justfile"
  - "pyproject.toml"
  - "backend/pyproject.toml"
  - "frontend/package.json"
  - "frontend/*.config.*"
  - "frontend/tsconfig*.json"
  - "docker-compose.yml"
  - ".pre-commit-config.yaml"
  - ".claude/settings.json"
  - "openspec/config.yaml"
  - "backend/app/platform/settings.py"
---

# Config

Settings, tool configs and command entry points. Neighbours: `docs-sync.md` for the docs a change
updates, `versioning.md` for the product version. Facts: `docs/tech.md` «Environment variables» and
«Dev environment and checks».

## Homes

| Setting | Home | Read by |
|---|---|---|
| Secrets, URLs | `.env` (gitignored); template `.env.example` | `backend/app/platform/settings.py` |
| Product version | root `pyproject.toml` `[project] version` | `/release` only |
| Python tooling | `pyproject.toml` (root: harness scripts; `backend/`: the app) | ruff, pyright, pytest |
| Frontend tooling | `frontend/package.json` and its configs | pnpm, Vite, ESLint, Prettier, tsc |
| Commands | `justfile` | humans, skills |
| Git hooks | `.pre-commit-config.yaml` | prek |
| Agent harness | `.claude/settings.json` | Claude Code |

## Rules

- A new env var in one change: a typed field in `backend/app/platform/settings.py`, a commented line in
  `.env.example`, `docker-compose.yml` only when a container overrides it, a row in `docs/tech.md`.
- Env is read only in `backend/app/platform/settings.py` (pydantic settings); the SPA gets config only
  from `import.meta.env` in one module. Config is parsed with a schema and fails loudly at startup.
- A version pin changes one place plus its lock file (`uv.lock`, `pnpm-lock.yaml`).
- A new `just` recipe gets a comment and a line in `CLAUDE.md` «Commands»; recipes must work under
  PowerShell on Windows (the `windows-shell` setting) — put logic into a Python script, not shell syntax.
- `just check` stays read-only and runs every check to the end.
- Ask before adding a runtime dependency.

## Never

- Never loosen a check (type checker option, lint rule, `exclude`, git hook) without the user's approval.
- Never commit `.env`, keys or `.claude/settings.local.json`.
- Never read `os.environ` or `process.env` outside the settings module.

Enforced by: the commit preflight (never-commit files, version changes), prek hygiene hooks, review.
