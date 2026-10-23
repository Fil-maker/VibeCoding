---
paths:
  - "backend/**/*.py"
  - "frontend/src/**/*.ts"
  - "frontend/src/**/*.tsx"
  - "scripts/**/*.py"
  - ".claude/**/*.py"
---

# Code quality

The strict quality bar for Python and TypeScript. Neighbours: `naming.md`, `server-architecture.md`,
`frontend.md`, `testing.md`. Tool versions: `docs/tech.md` «Stack».

## Both languages

- Strict types: pyright `strict`, `tsc --strict` with `noUncheckedIndexedAccess`. Lint warnings are errors.
- No escape hatches (`Any`, `cast`, `# type: ignore`, `# noqa`, `any`, `as`, `@ts-expect-error`,
  `eslint-disable`) without the reason in the same comment.
- Parse external input at the boundary with a schema (pydantic, the generated client's types) and trust
  it inside. Mail content is untrusted input.
- Illegal states unrepresentable: closed sets as `Literal`/`StrEnum` or TS literal unions, tagged unions,
  distinct id types (`NewType`, branded types).
- Explicit return types on exported functions.
- Expected failures are domain error classes (`backend/app/modules/<m>/errors.py`); never swallow an
  error; re-raise with the cause (`raise X from e`, `new Error(…, { cause })`).
- Every coroutine and promise awaited; every external call (mail server, analysis engine) has a timeout.
- Functional core, imperative shell: time, randomness and ids are parameters (the injected clock in
  `backend/app/platform/clock.py`).
- Functions about 50 lines; files aim at 300 lines and fail at 500.
- No magic numbers, no dead code; a `TODO` carries a task id: `# TODO(1.4): …`.
- Comments say why, not what.
- Logs through the logger (`backend/app/platform/logging.py`), never `print`/`console.log`; never log
  secrets, email text or personal data.
- Timestamps in UTC, timezone-aware.
- User-visible text in Russian.
- Ask before adding a runtime dependency.

## Python

- Named imports; `__init__.py` files stay empty (no re-exports).
- Async FastAPI handlers; blocking I/O only through `run_in_threadpool`.

## TypeScript

- Named exports only, no default exports (except where Vite config requires), no barrel files.
- No `enum`; use literal unions.

Enforced by: ruff, pyright strict, ESLint (`max-lines` 500), `tsc`; the rest by `invariant-reviewer`.
