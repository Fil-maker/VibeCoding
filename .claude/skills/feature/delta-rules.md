# Delta rules

Read before writing `openspec/changes/<change>/specs/<capability>/spec.md`. The requirement format is
`.claude/rules/docs.md` «Requirements».

1. Read the capability's current spec before writing a delta (`openspec show <capability> --type spec`);
   a new feature usually touches neighbours that need MODIFIED.
2. MODIFIED replaces the whole requirement: copy it with every scenario and keep the scenario names, or
   archive rejects it.
3. A scenario that must go away: REMOVED of the old requirement, ADDED of a new one with a new number.
   The old number goes to `docs/domain.md` «Cancelled numbers» at archive.
4. RENAMED (`- FROM:` / `- TO:` with full headings, the number in both) keeps the number; MODIFIED of it
   uses the new name. Archive applies RENAMED, REMOVED, MODIFIED, ADDED in that order.
5. A new capability takes only ADDED and starts with `## Purpose`.
6. A technical change sets `skip_specs: true` in the change's `.openspec.yaml` and has no `specs/`;
   retiring a whole capability sets `retire_capabilities: true`.
7. Never sync deltas into the specs before the code exists (`/opsx:sync`): the specs would promise
   unbuilt behavior. Archive does it at `/finish`.
8. Two open changes that modify one requirement: after the first is archived, rewrite the second's
   MODIFIED from the new text, or archive silently overwrites the first's edit.

Numbers: a new requirement takes «next FR» from `change_state.py` (it also reads the `Last FR number:`
line of `docs/domain.md`); never reuse a number.

Scenarios for this product almost always need these negative cases: a user asks for another
user's correspondence or projects; a request names another user's identifier; email text would go to an
external service without the user's consent; the same emails analysed twice (the assessment
must not change); the analysis model changed (the result shows it).
