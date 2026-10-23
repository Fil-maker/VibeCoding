# Architecture

Updated 23.10.2026

**Status: no code yet.** The structure below is planned; task 0.1 «Application skeleton» creates it and
this document then describes what exists.

## Contents

- [Implementation status](#implementation-status)
- [Components and processes](#components-and-processes)
- [Repository structure](#repository-structure)
- [Layers](#layers)
- [Data model](#data-model)
- [Routes and API](#routes-and-api)
- [Deploy](#deploy)
- [Security](#security)

## Implementation status

| Part | Status | Task |
|---|---|---|
| Application skeleton: backend, SPA, database | 🛠 | 0.1 |

## Components and processes

- **Backend** — a FastAPI application (Python): the HTTP API, the analysis, the database access.
- **SPA** — a React + TypeScript single-page app built with Vite; talks to the backend only through an
  API client generated from the backend's OpenAPI schema.
- **Database** — PostgreSQL, in Docker for development.

TBD: the mailbox reader and the analysis engine (see [ideas.md](ideas.md#analysis-engine)).

## Repository structure

Planned (created by task 0.1):

```
backend/                 FastAPI application (own pyproject.toml)
  app/
    main.py              app factory, routers
    platform/            settings (env loader), db, logging, clock, errors
    modules/<module>/    router, schemas, service, domain, repository, models
  migrations/            Alembic
  tests/integration/     database tests
frontend/                React + TypeScript SPA (Vite, pnpm)
  src/
    api/generated/       API client generated from OpenAPI, never edited by hand
docker-compose.yml       PostgreSQL for development and tests
docs/                    product docs
openspec/                requirements and changes
scripts/                 doc checkers and the check runner
.claude/                 the agent harness
```

## Layers

The layer responsibilities are the rules of `.claude/rules/server-architecture.md`; this section will
describe the modules as they appear.

## Data model

TBD (task 0.1 and later).

## Routes and API

TBD. The OpenAPI schema of the backend is the contract; `.claude/rules/api-contract.md` governs it.

## Deploy

Not deployed. Local development only: `docker compose` runs PostgreSQL.

## Security

- An employee reads only their own correspondence; the administrator reads all correspondence of their
  organization. The owner filter is applied in every query.
- The mailbox is accessed read-only.
- Email text is sent to a third-party service only after the administrator's consent.
