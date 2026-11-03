# Proposal

## Why

Since task 1.5 a rule acts only on new chains and on «Заполнить»: a rule the user has just written over
correspondence already read seems to do nothing, and the only way to see it work is to re-sort a whole
project. The user states a reason once (`docs/prd.md` «Business functions»: placement by the user's
rules before the engine) and expects the chains it names to follow it now, while keeping the control
the product promises — nothing placed by hand moves, and nothing moves without the user's say (ADR
0030: re-sorting only by an explicit user action). This is task 1.6 «Apply a rule now» of
`docs/plan.md`.

## What Changes

- After the user creates or edits a rule on «Правила», the page lists the chains the rule would move,
  each with where it is now and where it goes, and offers «Применить» and «Не сейчас»; when there are
  none it says «Подходящих цепочек нет».
- «Применить» moves the listed chains that still qualify into the rule's project and thread (found by
  name or created, or «Неразобранное»); each then shows «Правило» with the rule. «Не сейчас» moves
  nothing.
- A rule may move a chain in no project, a chain placed by the engine (also in «Неразобранное») and a
  chain placed by a rule — the edited rule's own earlier placements included; it never moves a chain
  placed by hand or taken out of projects.
- A chain moves only when the applied rule is its winning rule by the priority of FR-46, so applying
  gives the same placement by rules as «Заполнить» would.
- A thread left empty by the move disappears, as after a move by hand.
- Editing a rule no longer promises that nothing moves: nothing moves until the user presses
  «Применить». Deleting a rule still moves nothing.

Out of scope (deferred to `docs/ideas.md`):
- Applying a rule later, from its row in the list, after «Не сейчас» — new entry «Apply a rule later».
- Applying several rules, or all rules, at once.
- Rules by recipient or body, «or»/«not», manual order — «Richer rules»; a rule from a chain's page — «A
  rule from a chain».

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `placement-rules`: new requirement FR-47 «Apply a rule now»; FR-45 «Edit and delete a rule» — an
  edit moves nothing by itself, the chains move only when the user applies the rule.
- `chain-placement`: FR-46 «Place chains by rules» — a rule also places when the user applies it; the
  scenario «A new rule moves nothing» holds until «Применить».

## Impact

- Product invariants: **History is kept** — touched: a rule now moves chains already placed by the
  engine or by a rule, but only on the user's explicit «Применить» over a list they have seen (session
  decisions 3 and 4), and never a chain placed by hand or taken out; **Explainable placement** — every
  moved chain shows «Правило» and the rule as applied; **Reproducible placement** — the moves follow
  the same winning rule as a fill; **Access boundary** — a user applies only their own rule to their own
  chains. No invariant changes its meaning.
- Backend: the `projects` module — listing and applying the moves of one rule under the projects lock,
  reusing the rule placement and the empty-thread removal; two routes under `/api/v1/placements`; the
  `rules` module gives one rule for matching. No migration: placements by a rule already exist.
- SPA: the confirmation on «Правила» after saving a rule; the regenerated API client.
- Docs: `docs/domain.md` (glossary: Rule), `docs/architecture.md`, the rules guide article,
  `docs/ideas.md` («Apply a rule now» leaves, «Apply a rule later» comes).
