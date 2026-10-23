# Architecture decision records

Updated 23.10.2026

One file per decision: `NNNN-<slug>.md`, numbered in order. The index with status is
[decisions.md](../decisions.md). An ADR is written by the decision draft script
(`.claude/skills/document/scripts/session_facts.py write-decisions`) after the user confirms it; its
reason is the user's words. A replaced ADR gets the status «Superseded by NNNN» and stays.

| ADR | Decision |
|---|---|
| [0001](0001-fastapi-backend.md) | Backend in Python with FastAPI |
| [0002](0002-react-spa.md) | UI as a React + TypeScript SPA |
| [0003](0003-postgresql.md) | PostgreSQL in Docker |
| [0004](0004-task-0-1-runs-as-a.md) | Task 0.1 runs as a technical change without specs |
| [0005](0005-frontend-api-client-types-from-openapi.md) | Frontend API client: openapi-typescript, openapi-fetch, TanStack Query |
| [0006](0006-postgresql-driver-psycopg-3-for-the.md) | PostgreSQL driver: psycopg 3 |
| [0007](0007-just-dev-runs-everything-in-docker.md) | `just dev` runs everything in docker compose |
