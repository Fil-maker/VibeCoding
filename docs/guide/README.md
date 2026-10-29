# Guide

Updated 29.10.2026

How each part of the system works and how to change it, for humans and agents. One article per area;
each opens with **Code** (paths), **Requirements** (FRs and their spec), **Design** (`architecture.md`
sections), **Related** (sibling articles). Articles explain and link; facts stay in
[architecture.md](../architecture.md) and [tech.md](../tech.md).

## Articles

| Article | What is in it |
|---|---|
| [backend.md](backend.md) | The backend: app entry, OpenAPI export, modules layout, adding a module, platform layer, migrations, integration tests |
| [auth.md](auth.md) | Auth and accounts: personal accounts, registration, sign-in and sessions, password reset, the access boundary, errors over HTTP, tests with fake mail and clock |
| [frontend.md](frontend.md) | The SPA: entry and providers, the API client and its regeneration, query client, health page, styles and tokens, tests |

## You change → read

| You change | Read |
|---|---|
| `backend/**` | [backend.md](backend.md) |
| `backend/app/modules/accounts/`, `backend/app/modules/auth/`, or the platform files they use | [auth.md](auth.md) |
| `frontend/**` | [frontend.md](frontend.md) |

## Where a newcomer starts

1. [prd.md](../prd.md) — what the product is for.
2. [domain.md](../domain.md) — the terms.
3. [architecture.md](../architecture.md) — how it is built.
4. [tech.md](../tech.md) — how to run it.
