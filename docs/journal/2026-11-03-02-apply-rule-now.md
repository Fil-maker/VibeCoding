# Apply a rule now

Date: 03.11.2026 · Task: 1.6 · Change: 1-6-apply-rule-now

## Goal

Let a saved rule act at once. Before this task a rule written on the page «Правила» did nothing until the
user pressed «Заполнить»; FR-45 even said that editing or deleting a rule must not change any placement.
After this task, when the user saves a new or edited rule, the page lists the chains the rule would move
(from → to) and moves them only on «Применить»; «Не сейчас» moves nothing. The task was chosen by the user
as «Правило сразу» from the backlog candidates (the others were editing and deleting a project, a rule from
a chain, and the sentiment layer).

The product invariant «History is kept» is touched but kept: applying a rule is an explicit action of the
user on a list the user has seen, and it never moves a chain placed by hand or taken out of projects.

## What was done

- Design session: the path was «changed behavior». The change `1-6-apply-rule-now` got a proposal, delta
  specs for `placement-rules` and `chain-placement`, a design and tasks (18 tasks in five groups). Deltas:
  ADDED FR-47 «Apply a rule now» (14 scenarios at approval), MODIFIED FR-45 (editing a rule does not move
  any chain by itself; chains move only when the user applies the rule) and MODIFIED FR-46. The plan row 1.6
  was written (plan edition 0.15). The branch was renamed to `feat/1-6-apply-rule-now` by the usual scheme.
  Out of scope, sent to `docs/ideas.md`: applying a rule later from a list and applying several rules at
  once («Apply a rule later»).
- Design choices: the logic lives in the `projects` module, in the new file `rule_applying.py`, with routes
  `GET` and `POST /api/v1/placements/by-rule/{rule_id}`; the rule is read through
  `rules.service.get_match_rule`, so the import direction of ADR 0067 stays. The POST receives the ids of
  the shown list (at most 5000) and, under the projects lock, recomputes the moves, so only listed chains
  that still qualify move. A chain already in place is not re-explained as «Правило», so the list has no
  «X → X» rows. No migration: rule placements already exist.
- Backend (group 1): the routes, `get_match_rule` and `rule_applying.py` (movable kinds: engine and rule).
  Tests for FR-45 to FR-47 were written first in the TDD sandbox, and an audit by three test auditors
  followed.
- SPA (group 2): the panel «Применить правило сейчас?» (`RuleApplyPanel.tsx`) on the rules page with rows
  «<тема>: <откуда> → <куда>», the buttons «Применить» and «Не сейчас», and the result «Перемещено цепочек:
  N»; component tests in `App.ruleMoves.test.tsx`. The API client was regenerated.
- Product docs (group 3): `docs/domain.md` (the term Rule, the requirements map with FR-47) and
  `docs/ideas.md` («Apply a rule now» replaced by «Apply a rule later»).
- Manual flows 4.3 and 4.4 passed in a browser (the tail of both was finished by hand after the
  `flow-checker`s ran partial). Not checked live: the disappearing of an emptied thread (the demo engine
  creates no threads); it is covered by a test.
- Finish session: the work was carried from the worktree `feature-request-9a1114` into this worktree by a
  patch, together with `.env` and the decisions draft, because a hook forbids writing into another worktree;
  the source worktree was not touched.
- Finish, Done when: one item, «a chain placed by another rule is moved», had no test and no manual check.
  The user chose a scenario and a test: FR-47 got «A weaker rule's chain» (a new address rule takes a chain
  a domain rule placed) with a backend test.
- Finish, invariant review: 0 BLOCKER, 1 IMPORTANT, 2 MINOR. The IMPORTANT one was a test file of 649
  lines against the limit of 500; it was split into three files (332, 135 and 207 lines, still 27 tests).
  MINOR: `_compute_moves` of about 85 lines was refactored into helpers (about 55 left); a `type: ignore` with
  a reason was dropped as a finding because the rule allows it.
- Finish, spec: all tasks ticked, `openspec validate --strict` passed, the handoff was deleted and the change
  archived as `openspec/changes/archive/2026-11-03-1-6-apply-rule-now`; `Last FR number: FR-47` set in
  `docs/domain.md`. After the archive `just check` failed on FR-46 (see the mistakes); FR-46 got its
  pre-1.6 text back, in the spec and in the archived delta.
- Docs: ADRs 0069 to 0075 (the decisions below); five portions of implementation docs (`docs/guide/projects.md`,
  `docs/guide/rules.md`, `docs/guide/frontend.md`, `docs/architecture.md`, the OpenAPI client).
- Final counts: `just check` all pass; tests backend-unit 109, frontend-unit 185, database 311.

## Key questions to the AI

- Which task comes next (1.6)? The user chose «Правило сразу (рекомендую)».
- Path: changed behavior (MODIFIED FR-45 and FR-46, new FR-47, `feat` and a minor release)? «Да (рекомендую)».
- Which chains may a new or edited rule move at once? «Всё, кроме ручного (рекомендую)».
- How does the user start the applying? «Список и подтверждение (рекомендую)».
- A chain also matches another, stronger rule: what then? «Решает победитель (рекомендую)».
- Write the plan row 1.6? «Да (рекомендую)».
- Approve the deltas? «Да (рекомендую)».
- At the finish the Done when item about a chain placed by another rule had no cover. The AI offered
  «Сценарий и тест (рекомендую)» or a manual check; the user chose the scenario and the test («Сценарий и
  тест», then «Да, одобряю» for its text).
- After the archive FR-46 was over 500 characters. The AI offered to bring back the old text (recommended)
  or to move the sentence into FR-47; the user chose «Вернуть старый текст».
- Which decisions go to the ADRs? The AI listed nine and recommended dropping the second (the path) and the
  sixth (the plan row) as process steps, not product decisions. The user answered «Да, без 2 и 6».

## Decisions

| Decision | Alternatives | Reason | Who |
| --- | --- | --- | --- |
| Task 1.6 is «Apply a rule now»: a new or edited rule places matching chains at once | Edit and delete a project; A rule from a chain; Sentiment layer | User chose «Правило сразу» from the backlog candidates | [human] |
| Applying a rule may move chains in no project, engine placements (incl. «Неразобранное») and rule placements; never chains placed by hand or taken out of projects | Only no-project and engine; only no-project | Всё, кроме ручного (рекомендую) | [human] |
| After a rule is saved the page lists the chains it would move (from → to) with «Применить» and «Не сейчас»; nothing moves without confirmation | Apply silently on save; a separate «Применить» button per rule | Список и подтверждение (рекомендую) | [human] |
| A chain moves only when the applied rule is its winning rule by FR-46 priority, so the result equals what «Заполнить» would give | The newly saved rule always wins | Решает победитель (рекомендую) | [human] |
| Deltas of 1-6-apply-rule-now approved: FR-47 added, FR-45 and FR-46 modified; a chain already in place keeps its placement; apply moves only the listed ids that still qualify | - | Да (рекомендую) | [human] |
| FR-47 gets the scenario «A weaker rule's chain»: a new address rule takes a chain a domain rule placed | - | The «Done when» item «a chain placed by another rule is moved» had no test and no manual check; the user chose a scenario and a test over a manual check | [human] |
| FR-46 keeps its text from before task 1.6; the sentence on when a rule places chains is dropped | - | With it the requirement exceeded 500 characters; applying a rule is already stated in FR-47, and reading and «Заполнить» are shown by the FR-46 scenarios | [human] |

The path (MODIFIED FR-45 and FR-46, ADDED FR-47, `feat`, minor) and the plan row 1.6 were also recorded in
the draft, but the user dropped them from the ADRs («Да, без 2 и 6»): they are visible in the specs and the
plan.

## Mistakes and lessons

- The approved delta of FR-46 added the sentence «A rule SHALL place chains on a mailbox read, on
  «Заполнить» and when the user applies it». It grew the requirement from 496 to about 580 characters.
  `openspec validate --strict` of the delta did not notice it; only `just check` on the merged spec failed
  («Requirement text is very long (>500 characters)») after the archive. Lesson: count the length of a
  MODIFIED requirement when the delta is written, not after the merge.
- The Done when item «a chain placed by another rule is moved» was not covered by a test or a manual flow.
  The code supported it (movable kinds engine and rule), but FR-47 had only the reverse scenario «A stronger
  rule wins». The auditors had listed spec gaps in the handoff; this one was caught at the finish step
  «Done when», not at the design or the code step. A check of each Done when item against the scenarios at
  the design approval would have caught it earlier.
- The finish session was started in a worktree with an empty branch while the code lay uncommitted in
  another worktree. A hook forbade writing into the other worktree, so the work was carried over by a patch.
  This is the same lesson as in task 1.5: run `/finish` in the folder that holds the code.
- The invariant review found a test file of 649 lines (limit 500) and a function of about 85 lines; neither
  check nor the code review of the code step had flagged them. The size limits were met only after the
  review.
- At the code review the AI found a real defect: a chain from the «Неразобранное» of the rule's project was
  counted as already in place when the rule's thread did not exist yet. The code-writer fixed it and the
  test-writer added a test. It was found by reading the diff, not by the first green tests.
- `tdd_sandbox.py red` judges a whole file, so in a file with a legitimately green test of existing
  behavior it makes no briefs for the auditors. The AI generated the briefs directly and did not change the
  script. One comment line in a test was moved by hand after the sandbox was gone, because ruff failed on
  the line length.
- The state script of `/feature` proposed the task id 0.1 instead of 1.6: it seems to read only the empty
  «Tasks» table of the plan and not the «Done» section. It was not fixed or recorded in
  `docs/tech-debt.md` in this change.
- The environment again got in the way of the manual flows: the frontend container could not start because
  corepack could not reach the npm registry, so a local Vite was used; port 5175 gave `forbidden_origin`
  on POST, so Vite was restarted on 5173; the backend container was mounted from the old worktree of task
  1.5; `.env` had to be copied. A test user `flow-1-6-apply@example.test` stayed in the dev database.
  Two `flow-checker` runs were partial and their tails were checked by hand.
- Open point, documented and not fixed: when the request for the moves list fails, `RuleApplyPanel` shows
  only the alert and no button.
- Spec gaps found by the auditors and listed in the handoff (deleted at the archive; the list is condensed
  from the coordinator's reading of it in the finish session). The handoff recommended accepting them with
  no delta change; apart from the weaker-rule scenario they were accepted as they are:
  - FR-47 had no scenario for a new stronger rule taking a chain from a weaker one (added at the finish as
    «A weaker rule's chain»).
  - No scenario for a chain in «Неразобранное» of the rule's own project when the rule's thread does not
    exist yet; covered by the test
    `test_fr47_a_chain_of_the_engine_in_unassigned_moves_into_a_new_thread_of_its_project`.
  - «Still qualify» has a scenario only for a move by hand between the list and «Применить».
  - «A thread left empty» has a scenario only for an engine thread.
  - The empty-list text after an edit is in the SHALL text but in no scenario.
  - FR-45 «same checks as on creation» is shown only for the repeat check.
  - FR-46 «a domain over subject words» and «the earlier rule» across kinds have no scenarios (this predates
    1.6).
  - The SPA leaves open the title with an empty list, the panel after «Применить», and a failed request.

## What remains

- The ideas in `docs/ideas.md`: «Apply a rule later» (applying a rule from a list, several rules at once),
  rules by recipient or text, «Сделать правилом» from a chain page, and the earlier «Edit threads by hand».
- The failed moves-list request in `RuleApplyPanel`: only the alert is shown, without a button.
- The state script of `/feature` reads the next task id wrongly; to be recorded as a defect if the user
  agrees.
- Stage 2: sentiment as a layer over the trees.
- The commit and merge of the change into `main` are done by `/finish` after this note.
