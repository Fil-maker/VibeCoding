# Plan

Version 0.2 · 23.10.2026

Changes in 0.2: task 0.1 «Application skeleton» done.

Changes in 0.1: task 0.1 «Application skeleton».

## How work runs

- A task is one change: one branch, one OpenSpec change, one journal note.
- `/feature` leads a task from the plan row to `/finish`; `/fix` leads a bug.
- «Done when» is what the user will see, in checkable sentences, each ending with a period.
- FR is «—» until the spec delta is approved.
- Ids are stable: a new task takes the highest id + 1; dropped ids are not reused.

## Tasks

None yet.

## Done

| # | Task | FR | Done when |
|---|---|---|---|
| 0.1 | **Application skeleton.** FastAPI backend, React SPA and PostgreSQL start together with one command; technical change, no specs (`skip_specs`) | — | `just dev` starts the database, the backend and the SPA. The SPA page shows the backend's health status, in Russian, read through the generated API client. `just check` and `just test-all` pass with the backend and frontend checks included. |
