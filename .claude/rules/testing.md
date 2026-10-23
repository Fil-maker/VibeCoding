---
paths:
  - "backend/app/**/test_*.py"
  - "backend/tests/**"
  - "backend/conftest.py"
  - "frontend/src/**/*.test.ts"
  - "frontend/src/**/*.test.tsx"
  - "frontend/vitest.config.*"
---

# Testing

How tests are written and run. Neighbours: `code-quality.md` for the code under test, `data-access.md`
for databases. Tests are derived from the requirement scenarios, not from the code.

## Layers

| What | Test | Where |
|---|---|---|
| Domain logic (pure functions) | unit | `backend/app/**/test_<file>.py` next to the file |
| Services, repositories, migrations | integration against a real PostgreSQL | `backend/tests/integration/` |
| Components, hooks, client-side logic | unit (Vitest) | `frontend/src/**/<file>.test.tsx` next to the file |
| User flows in the browser | `flow-checker` on the preview server | the change's handoff «Manual checks» |

## Writing

- Name the unit and state the condition and the result: `test_assessment_lists_its_evidence_emails`,
  `describe("CounterpartyCard")` / `it("shows the analysis model with the assessment")`.
- Arrange-act-assert; one behavior per test; small factories; no shared mutable fixtures.
- A scenario test names its requirement: `# FR-12 «Archived task leaves Today»` or `it("FR-12 …")`.
- Failure paths are tested: another user's correspondence, an employee asking for the organization's
  data, a missing consent, empty input.
- A bug fix starts with a failing test at the lowest layer that shows the bug.
- Deterministic: a fake clock, fixed ids, no sleeps, no network (fake the mailbox and the analysis
  engine). Every test asserts.
- In the two-agent flow, `test-writer` writes tests in the TDD sandbox from the requirements and the
  interface only.

## Running

Through `/test` (`.claude/skills/test/scripts/run_tests.py`): `unit`, `db`, `all`, `auto`. A skipped
database suite is never reported as passed.

## Never

- Never fix a red test with `skip`, `xfail`, `.only`, a looser assertion or a longer timeout; fix the cause.
- Never copy a value from the implementation into an assertion; the value comes from the THEN.
- Never let an integration test touch the dev database: it uses `TEST_DATABASE_URL`.

Enforced by: `tdd_sandbox.py red` (tests must fail before the code), `test-auditor`, review.
