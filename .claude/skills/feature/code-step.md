# Code step

Shared by `/feature` (step 6) and `/fix` (step 5). Full variant: two agents, tests in a sandbox before
the code. Script prefix: `uv run --no-project python .claude/skills/feature/scripts/`.

## Interface

From design «Interface»: the public contract both agents build against — exported functions and
signatures, service methods, domain errors, endpoints with fields and error codes, response fields the
UI uses, pydantic schemas, new columns, Russian UI texts. Never SQL, private names or how a value is
computed. Missing and not obvious → add it to the design first and tell the user.

## Sandbox and brief file

1. Integration tests involved → start the test database (`docker compose up -d db`, task 0.1 adds
   `just db`).
2. `tdd_sandbox.py . create <change>` — prints the «Sandbox» block.
3. `change_state.py . brief <change> .claude/session/brief-<change>.md` — the requirement blocks verbatim
   and the «Interface». For a fix without a change: `change_state.py . brief-spec <out> <capability> FR-N`.

## Parallel run

One message, two Agent calls:
- `test-writer`: the «Sandbox» block, the change, the brief file, the factories to update,
  `.claude/rules/testing.md`, out of scope — and nothing else: no assertions of yours, no implementation
  hints, no paths into the main checkout.
- `code-writer`: the code groups' tasks with their checks, the brief file, the design headings to read,
  the files, the rules, what not to touch, «Done when»; it must not touch tests.

## Red check and audit

1. `tdd_sandbox.py . red <change> --change <change> --briefs .claude/session/audit-<change>` — run it
   yourself; never trust the report. Every new or changed test must be RED for the right reason (a
   missing interface name or the THEN value). A GREEN test checks nothing (fine only for a scenario that
   keeps existing behavior) and goes back to `test-writer`.
2. All red → one `test-auditor` per auditor brief, in parallel, one message.
3. Filter their findings against the test lines and the spec. Weak, vacuous, mislabeled, missing,
   overreaching tests go back to the same `test-writer` (SendMessage) as one numbered list quoting the
   requirement, never the code. Spec gaps go to the user ✋.

## Collect and green

`tdd_sandbox.py . close <change> --change <change> --groups <n>…` copies the tests in, runs them with the
area's existing tests, and ticks the groups when green. Judge each failure against the spec: the code
misses the scenario → `code-writer`; the test contradicts the requirement → `test-writer`; the
requirement is wrong → stop, the user re-approves the delta, a new sandbox. Rerun `close` after each fix.
Never weaken, skip or delete a test.

## Review

`git diff --stat` and both reports against the briefs: every task done, no file outside the briefs,
neither agent touched the other's files, deviations and questions answered. The line-by-line review
belongs to `/finish`.

## Manual flow

For scenarios no test reaches: start the preview server (`.claude/launch.json`, added with task 0.1),
then `flow-checker`s of about six steps each. Account: a throwaway `flow-<change>@example.test` on
localhost only, its generated password in `.claude/session/flow-<change>.txt`, never repeated in chat.
A partial run gets one more checker for the remaining steps; then check the rest yourself. Clean up the
test data. Screenshots only for a changed look, on the user's request.

## Handoff

`openspec/changes/<change>/handoff.md` (a fix without a change: `.claude/session/handoff-fix-<slug>.md`):

```markdown
# Handoff: <change>

- Approved: <YYYY-MM-DD>
- Code done: <YYYY-MM-DD>

## Open questions
<for the user, with a recommendation; «none»>

## Spec gaps and agent questions
## Code issues
## Manual checks
```

Add `- Code done: <date>`, accepted spec gaps, agent questions with answers, open questions, code issues
left for later, the manual checks and steps for the user. Decisions are not repeated: they are in the
decision draft. Then «/clear, затем `/finish <id>`».

One cycle per change, not per task group; a second cycle only when a later group cannot be specified
before an earlier one exists.
