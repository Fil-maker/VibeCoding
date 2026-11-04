# Guide

Updated 05.11.2026

How each part of the system works and how to change it, for humans and agents. One article per area;
each opens with **Code** (paths), **Requirements** (FRs and their spec), **Design** (`architecture.md`
sections), **Related** (sibling articles). Articles explain and link; facts stay in
[architecture.md](../architecture.md) and [tech.md](../tech.md).

## Articles

| Article | What is in it |
|---|---|
| [backend.md](backend.md) | The backend: app entry, OpenAPI export, modules layout, adding a module, platform layer, migrations, integration tests |
| [auth.md](auth.md) | Auth and accounts: personal accounts, registration, sign-in and sessions, password reset, the access boundary, errors over HTTP, tests with fake mail and clock |
| [mail-reading.md](mail-reading.md) | Mail reading: connecting, listing, refreshing and disconnecting a mailbox, the reading run, storing emails once, joining them into reply chains, HTML to text, reading a chain, the demo mailboxes |
| [projects.md](projects.md) | Projects and the placement engine: creating and listing projects, the tree, editing and deleting a project, placing by rules, filling a project, placing new chains, placing a chain by hand and taking it out, and the merge hook, the engine text-1 and its versions, the test seams |
| [rules.md](rules.md) | Placement rules: the rule by sender address, domain or subject words, the checks of its input, the matching and its priority, create, list, edit and delete, the project directory, the limit of 200, the page «Правила», the tests |
| [frontend.md](frontend.md) | The SPA: entry and providers, the API client and its regeneration, query client, health page, styles and tokens, tests |

## You change → read

| You change | Read |
|---|---|
| `backend/**` | [backend.md](backend.md) |
| `backend/app/modules/accounts/`, `backend/app/modules/auth/`, or the platform files they use | [auth.md](auth.md) |
| `backend/app/modules/mailboxes/`, `backend/app/modules/correspondence/`, `backend/app/platform/mail_reader.py`, `imap_folders.py`, `secret_box.py`, `pagination.py`, `scripts/demo_mail.py`, `docker/greenmail/` | [mail-reading.md](mail-reading.md) |
| `backend/app/modules/projects/`, `backend/app/platform/placement_engine.py`, `backend/app/platform/test_placement_engine.py`, `backend/tests/project_trees.py` | [projects.md](projects.md) |
| `backend/app/modules/rules/` | [rules.md](rules.md) |
| `frontend/**` | [frontend.md](frontend.md) |

## Where a newcomer starts

1. [prd.md](../prd.md) — what the product is for.
2. [domain.md](../domain.md) — the terms.
3. [architecture.md](../architecture.md) — how it is built.
4. [tech.md](../tech.md) — how to run it.
