# Tech

Updated 23.10.2026

## Contents

- [Stack](#stack)
- [Dev environment and checks](#dev-environment-and-checks)
- [Environment variables](#environment-variables)
- [Techniques](#techniques)

## Stack

Versions are pinned when task 0.1 adds the manifests.

| Component | Version | Why |
|---|---|---|
| Python + FastAPI | Python 3.12+ | Backend; typed, async, OpenAPI out of the box — [ADR 0001](adr/0001-fastapi-backend.md) |
| uv | 0.13 | Python packages and environments |
| pytest | — | Python tests |
| ruff | 0.17 | Python lint and format |
| pyright (strict) | 1.1 | Python type checking |
| SQLAlchemy + Alembic | — | Database access and migrations |
| React + TypeScript (Vite) | — | SPA — [ADR 0002](adr/0002-react-spa.md) |
| pnpm | 12 | Node packages |
| Vitest, ESLint, Prettier, tsc strict | — | Frontend tests, lint, format, types |
| OpenAPI client generator | — | Frontend API client from the backend schema; chosen in task 0.1 |
| PostgreSQL in Docker | — | Database — [ADR 0003](adr/0003-postgresql.md) |
| just | 1.59 | Command entry point (works on Windows) |
| prek | 0.5 | Git hooks (pre-commit compatible) |
| OpenSpec | 1.14.3 | Requirements and change deltas |

## Dev environment and checks

Requires: git, uv, just, prek, node with pnpm, Docker, openspec (`npm install -g @fission-ai/openspec`).

| Command | What it does |
|---|---|
| `just setup` | Installs the tooling and the git hooks |
| `just check` | Read-only: every check to the end (lint, types, doc links and facts, OpenSpec validation); fails on warnings |
| `just format` | Autofixes formatting and lint |
| `just test` | Unit tests |
| `just test-all` | Unit and database tests |

`just dev`, `just db` and `just test-db` are planned (task 0.1).

Git hooks (prek, `.pre-commit-config.yaml`): file hygiene, ruff, pyright, doc links and facts, the
journal guard, and a Conventional Commits check of the commit message.

## Environment variables

Secrets live only in `.env` (gitignored); `.env.example` is the template.

| Name | Meaning | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL URL of the dev database | see `.env.example` |
| `TEST_DATABASE_URL` | PostgreSQL URL of the test database | see `.env.example` |
| `POSTGRES_USER` | User of the Docker database | `vibecoding` |
| `POSTGRES_PASSWORD` | Password of the Docker database | set in `.env` |

## Techniques

None yet.
