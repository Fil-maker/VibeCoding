# Proposal

## Why

Some correspondence belongs to a project for a plain reason the user knows better than any similarity:
every email from a contractor's address or domain, or every email about «акт» and «работ». After task
1.4 the user can place such chains only one by one, by hand, and the engine may put the next one
elsewhere. The user must be able to state the reason once, as a rule, and have new and re-sorted chains
follow it before the engine (`docs/prd.md` «Business functions»: «Place new emails: … then the user's
rules; then the engine when it is sure»; priority «by hand, then a rule, then the engine»; ADR 0030).
This is task 1.5 «Rules» of `docs/plan.md`.

## What Changes

- A page «Правила» where the user creates, lists, edits and deletes rules. A rule has a condition — a
  sender address, a domain or words of the subject — and a target: one of the user's projects and,
  optionally, a thread name; without a thread name the target is the project's «Неразобранное».
- After a mailbox read, a new chain that is in no project and was not taken out by hand goes by the
  winning rule into its project and the thread of that name, created when the project has none; only a
  chain no rule matches goes on to the engine.
- «Заполнить» places the candidates whose winning rule targets this project by that rule, leaves out
  the candidates whose winning rule targets another project, and gives the rest to the engine. Filling a
  filled project again also recomputes the placements by rules of that project, so an edited rule takes
  effect on an explicit re-sorting; placements by hand stay.
- When several rules match, an address wins over a domain and a domain over subject words; among rules
  of one kind the one created first.
- Every chain placed by a rule shows «Правило» and the rule as it was when it placed the chain, in the
  project tree and on the chain's page.
- When chains are joined, a placement by hand wins over a rule's, and a rule's over the engine's.
- Creating, editing or deleting a rule never moves a placed chain; a rule never places a chain placed by
  hand or taken out of projects.

Out of scope (deferred to `docs/ideas.md`):
- Applying a rule at once to the chains already in no project, without «Заполнить» — «Apply a rule now».
- Rules by recipient, by body text, with «or»/«not», or ordered by hand — «Richer rules».
- Creating a rule from a chain's page («Сделать правилом») — «A rule from a chain».

## Capabilities

### New Capabilities

- `placement-rules`: the user's rules — FR-43 «Create a rule», FR-44 «List the rules», FR-45 «Edit
  and delete a rule».

### Modified Capabilities

- `chain-placement`: new requirement FR-46 «Place chains by rules»; FR-35 places a fill's candidates by
  the project's rules first and skips those another project's rule claims; FR-36 recomputes the
  placements by rules on filling again; FR-37 explains a placement by a rule; FR-39 places new chains by
  rules before the engine; FR-42 ranks a rule's placement between the hand's and the engine's on a merge.

## Impact

- Product invariants: **Explainable placement** (a placement now also says «by a rule» and which rule),
  **Reproducible placement** (the rules are part of the input: the same emails, description, rules and
  engine version give the same tree), **History is kept** (a rule never moves a placed chain; only an
  explicit «Заполнить» recomputes the placements by rules of that project, and placements by hand
  stay), **Access boundary** (a user's rules target only their own projects and apply only to their own
  chains). No invariant changes its meaning; all follow `docs/prd.md` and ADR 0030 as written.
- Backend: the `projects` module — rules storage and routes, matching and priority, the fill and the
  new-chain placement placing by rules first, the merge ranking; `correspondence` gives the senders of
  each chain; migration `0007` adds the rules table and widens `chain_placements`.
- SPA: the page «Правила» with its form and list, a link «Правила» in the header; «Правило · …» in the
  project tree and on the chain page; the regenerated API client.
- Docs: `docs/domain.md` (requirements map, glossary: Rule, Placement), `docs/architecture.md`, the
  engine guide article, `docs/ideas.md`.
