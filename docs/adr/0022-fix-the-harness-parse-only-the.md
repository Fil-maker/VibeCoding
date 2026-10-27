# Fix the harness: parse only the pytest short summary in sandbox_tests.py, write every harness text file with newline='\n'; the deleted-test refusal of tdd_sandbox close stays, and a name-matching split allowance is recorded in .claude/harness.md «Deferred»

Id: 0022 · Date: 27.10.2026 · Kind: technical · Status: Accepted · Who: [human]

## Context
Task: outside the plan.

## Decision
Fix the harness: parse only the pytest short summary in sandbox_tests.py, write every harness text file with newline='\n'; the deleted-test refusal of tdd_sandbox close stays, and a name-matching split allowance is recorded in .claude/harness.md «Deferred»

## Alternatives
none recorded

## Reason
The user chose it: fix the two confirmed defects, keep the guard against deleted tests; the idea went to harness.md instead of docs/ideas.md because docs/ never holds Claude Code setup (.claude/rules/docs.md)
