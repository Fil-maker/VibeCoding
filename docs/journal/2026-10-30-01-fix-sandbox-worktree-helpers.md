# Fix of the TDD sandbox: worktree sessions and helpers

Date: 30.10.2026 · Task: - · Change: fix-sandbox-worktree-helpers

## Goal

Remove three defects of the TDD sandbox scripts (`.claude/skills/feature/scripts/`) seen in change
1-3-projects-and-engine, which was done from a Claude Desktop worktree session and worked around by hand.
The fix is case D (tooling, no spec change, no `test-writer`). Done when: a sandbox created from a worktree
session is writable by `test-writer`, `red` treats helpers without tests as neutral and writes the briefs,
`close` copies helper files under the test paths, and `.claude/harness.md` describes the behavior. The
guard's protection of the main checkout was not to be loosened without the user's approval.

## What was done

1. **Sandbox not writable from a worktree session.** `create` put the sandbox next to the current
   worktree, in `.claude/worktrees/<wt>-sandboxes/`. Claude Code refuses writes there («belongs to a
   different worktree»), as reproduced on a probe, and the guard saw the main checkout path in
   `cd <sandbox>` and blocked the command. Now `create` places the sandbox next to the main checkout, in
   `D:\Projects\AI_projects\VibeCoding-sandboxes\<name>`; from the main checkout the path is unchanged.
2. **`red` wrote «NOT all red».** Every file under `backend/tests/**` was treated as a test, so helpers
   (for example `backend/tests/factories.py`) went to pytest and showed «NOT FOUND». A notion of a
   «runnable test» was introduced: `red` runs only those. Helpers are printed as `HELPER` lines, do not
   affect the result and are listed in the auditor briefs under «Helpers».
3. **`close` did not copy helpers under `frontend/src/test/**`.** That folder was not a test path; now it
   is. `collect`, `close` and `drop` handle both tests and helpers, and `close` runs only the tests.

Files changed: four scripts in `.claude/skills/feature/scripts/` (`sandbox_briefs.py`,
`sandbox_common.py`, `sandbox_create.py`, `tdd_sandbox.py`), a new section «TDD sandbox» in
`.claude/harness.md`, two lines in `.claude/skills/feature/code-step.md`. The guard
`.claude/hooks/sandbox_guard.py` was not changed. The handoff is
`.claude/session/handoff-fix-sandbox-worktree-helpers.md`.

Verification on a real sandbox created from this worktree session: a real `test-writer` under its guard
wrote a test, new and changed backend helpers and a helper in `frontend/src/test` without a refusal; `red`
showed the test red, printed three `HELPER` lines, the result «ALL RED», and wrote the brief;
`close --ignore-other` copied all four files and ran only the test. Probe files were removed. The guard was
run with `CLAUDE_PROJECT_DIR` equal to the worktree and to the main checkout: reading the checkout,
commands in it and commands with its path are still blocked. `just check` passes.

## Key questions to the AI

The session had no questions from the user to the AI; the task came as a brief from a previous session, and
the digest records no open questions.

## Decisions

| Decision | Alternatives | Reason | Who |
| --- | --- | --- | --- |

No decisions were recorded in this session.

## Mistakes and lessons

- The sandbox location was derived from the current worktree, so it only worked from the main checkout.
  The probe made from a worktree session (write into `-sandboxes` next to the worktree gave «belongs to a
  different worktree») is what showed it; the same end-to-end run from a worktree session is the check
  that was missing.
- `red` and `close` classified files by directory (`backend/tests/**`) and a path list that lacked
  `frontend/src/test/`, instead of separating tests from helpers. Running a sandbox with a changed helper
  through `red` and `close` catches both.
- The three defects were worked around by hand in change 1-3 and noted in its handoff «Open questions»
  before being fixed here.

## What remains

- Frontend tests inside a sandbox were not verified: this worktree has no `frontend/node_modules`.
- The fix is not committed: the commit goes through `/commit` after the user agrees; the planned type is
  `chore(harness)`, without a release.
