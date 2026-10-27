# Fix of the harness: sandbox close and CRLF

Date: 27.10.2026 · Task: - · Change: fix-harness-close-and-crlf

## Goal

Fix the harness defects left open by change 0.2 (see [Sign-in and organization](2026-10-27-01-0-2-sign-in-and-organization.md),
«Harness defects, not fixed»): `tdd_sandbox.py close` reported failed tests on green runs, and harness
scripts wrote files with CRLF on Windows. A tooling fix on the branch `fix/harness-close-and-crlf`: no plan
task and no OpenSpec change; the product behavior is not touched.

## What was done

- **Diagnosis (case D, tooling).** The AI looked up the exact refusal text of `close` in the earlier session
  and reproduced both defects, then searched for the same error elsewhere. No spec, no `test-writer`: the
  harness scripts have no tests.
- **Defect 1, `close` counted log lines as failed tests.** `parse_pytest` in
  `.claude/skills/feature/scripts/sandbox_tests.py` matched `^ERROR\s+` on every line of the output. With
  `-rA` pytest prints the captured logs of passing tests, for example
  `ERROR    app.platform.mail:mail.py:41 …`; such a line became a failed result and `close` answered «Not
  green». Now only the lines after the `short test summary info` separator are parsed. A summary line such
  as `ERROR tests/x.py - ImportError` still fails.
- **Defect 2, CRLF.** `Path.write_text` without `newline="\n"` translates `\n` to `\r\n` on Windows.
  `newline="\n"` was added to all 12 writes in 9 scripts: `facts_adr.py` (4), `facts_store.py`,
  `change_state.py`, `sandbox_briefs.py`, `sandbox_common.py`, `sandbox_create.py`, `tdd_sandbox.py`,
  `session_digest.py`, `run_tests.py`. No other text writes without the option remain in the harness scripts.
- **Test split refusal left as is.** `close` still refuses a deleted test file. The idea of allowing it when
  every test name of the deleted file is found in the new files is recorded in `.claude/harness.md`
  «Deferred».
- **Verification.** The AI re-ran the reproduction with a synthetic pytest output holding a captured ERROR
  log line: only the PASSED result remains. The bytes of the written files hold no `\r\n`. The collection
  error case was not re-run by the AI; it follows from the run reported by `code-writer`. `just check` all
  PASS; unit tests 21 backend and 60 SPA passed (the database suite was not needed for this change).
  `invariant-reviewer`: no findings; it noted, optionally, that `parse_pytest` has no regression test.
- The handoff is `.claude/session/handoff-fix-harness-close-and-crlf.md`. Nothing is committed. The commit
  type is `chore(harness)`, not `fix`, because it is tooling; no release. No documentation needed changes.

## Key questions to the AI

The digest holds no questions the user put to the AI in this fix, only the choice below, asked by the AI.

- The diagnosis is right, and what to fix in this fix? Answer: «1 и 2, разбиение — в ideas (Recommended)».
  The AI had listed three points: the log lines counted as failures, the CRLF writes, and the refusal to
  split a test file (an intended guard, not a bug). The AI asked first the user to weigh in on the split
  because loosening the check needs the user's decision.

## Decisions

| Decision | Alternatives | Reason | Who |
| --- | --- | --- | --- |
| Fix the harness: parse only the pytest short summary in sandbox_tests.py, write every harness text file with newline='\n'; the deleted-test refusal of tdd_sandbox close stays, and a name-matching split allowance is recorded in .claude/harness.md «Deferred» | - | The user chose it: fix the two confirmed defects, keep the guard against deleted tests; the idea went to harness.md instead of docs/ideas.md because docs/ never holds Claude Code setup (.claude/rules/docs.md) | [human] |

## Mistakes and lessons

- **Harness scripts have no tests,** so nothing caught either defect; they surfaced only during the work on
  0.2, where `close` had to be worked around by hand. A regression test for `parse_pytest` would have
  caught the first one; `invariant-reviewer` also noted that it is missing.
- **`.gitattributes` normalizes line endings only at commit,** not in the working copy, so the CRLF files
  written by the harness stayed unnoticed until `just check` or a review.
- **The same error was in 12 places.** The first report named one file (`facts_adr.py`); the search found
  the other writes in 8 scripts.
- **A wrong commit type was avoided:** `fix` implies a release, but the change is tooling, so `chore(harness)`.

## What remains

- A regression test for `parse_pytest` (optional note of `invariant-reviewer`); the harness still has no
  test suite.
- Allowing a deleted test file when all its test names are found in the new files: only recorded in
  `.claude/harness.md` «Deferred», not done.
- The other open questions of the 0.2 finish are not part of this fix: the sign-in lock message for
  `tech-debt.md`, Mailpit SMTP for a host-run backend for `ideas.md`, and the «Architecture in brief»
  section of `CLAUDE.md`.
- The note is written before the commit; the commit goes through `/commit`.
