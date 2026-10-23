---
paths:
  - "backend/app/**"
---

# Server architecture

Layers and module boundaries of the FastAPI backend. Neighbours: `data-access.md` for queries and
transactions, `database.md` for schema, `api-contract.md` for the HTTP contract. Facts:
`docs/architecture.md` «Layers».

## Layout

```
backend/app/
  main.py                 app factory: routers, middleware, lifespan
  platform/               settings, db (engine, session), logging, clock, errors, auth context
  modules/<module>/
    router.py             entry point
    schemas.py            pydantic request and response models
    service.py            use cases
    domain.py             pure logic
    repository.py         named queries
    models.py             SQLAlchemy tables
    errors.py             domain errors
```

## Responsibilities

| Layer | Does | Never |
|---|---|---|
| `router.py` | Parse input into schemas, take the user from the auth context, call one service method, map domain errors to HTTP | Queries, business logic |
| `service.py` | One method per use case; opens the transaction; calls domain logic and repositories; checks permissions | HTTP types, raw SQL |
| `domain.py` | Pure functions: sentiment aggregation, evidence selection, access decisions | I/O, clock, randomness |
| `repository.py` | Named queries; takes the session from the service | Commits, business decisions |
| `platform/` | Env, logging, errors, clock, db client | Module imports |

## Rules

- Dependencies point down only: router → service → domain and repository → platform.
- Another module is used only through its `service.py` (or `repository.py` from a service); never import
  its models or private functions.
- Collaborators tests fake (mail reader, analysis engine, clock) come through a FastAPI dependency
  factory; lazy singletons, never created at import.
- No in-memory state that must survive a restart.
- The mail reader only reads: no API that sends, moves, flags or deletes emails exists in the code.
- An assessment stores its evidence (email and phrase references) and the analysis model version.
- Email text goes to an external analysis service only through one gateway that checks the
  organization's consent first.
- Security: the owner filter on every query (`data-access.md`), input parsed at the entry, limits on
  request size and rate.

## Never

- Never call a mail server or the analysis engine from a router or a repository.
- Never decide access in the router alone; the service enforces it.

Enforced by: review (`invariant-reviewer`); import boundaries by ruff `TID` banned imports once the
modules exist.
