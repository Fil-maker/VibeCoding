# Tech debt

Updated 03.11.2026

Things that work wrong now. An item is removed by the commit that closes it. Future improvements go to
[ideas.md](ideas.md).

## Product

None.

## Tests

### Weak tests of tasks 1.3–1.4

Added 03.11 by task 1.5 (test auditors). FR-35 «Filling a project» checks only the threads, not
«Неразобранное»; FR-35 «Another user's project» uses an empty project; the FR-41 test in
`backend/tests/integration/test_placement_kept.py` lacks the read of a new email; the engine's
percentages of FR-37 are not asserted in the backend tests.

### Rules of a user with more than 200 projects

Added 03.11 by task 1.5. No database test lists a rule whose project is beyond the user's first 200
projects; the list of rules looks the names up by the rules' project ids, and nothing checks it at that
size.

## Tooling

None.
