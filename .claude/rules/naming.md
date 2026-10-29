---
paths:
  - "backend/**/*.py"
  - "frontend/src/**/*.ts"
  - "frontend/src/**/*.tsx"
  - "scripts/**"
  - ".claude/**/*.py"
---

# Naming

Names of files, functions and terms. Neighbours: `server-architecture.md` for layer files,
`code-quality.md` for code structure. Terms: `docs/domain.md` «Glossary».

## Files

- A path tells what the file does: `backend/app/modules/assessments/service.py`,
  `frontend/src/features/counterparties/CounterpartyCard.tsx`.
- Fixed role names in backend modules, and nothing else uses them: `router.py`, `schemas.py`,
  `service.py`, `domain.py`, `repository.py`, `models.py`, `errors.py`.
- Banned catch-all names: `utils`, `helpers`, `common`, `misc`, `manager`, `handler`, `data`, `index`
  (except the `index.html` Vite entry).
- One file, one job: an honest name with «and» means split it.
- Tests sit next to their file: `test_domain.py`, `CounterpartyCard.test.tsx`.
- React components in `PascalCase.tsx`; hooks `useThing.ts`; other TypeScript files `camelCase.ts`;
  Python modules `snake_case.py`.

## Code

- Functions start with a verb: `compute_assessment`, `list_counterparties_of_owner`.
- Booleans read as questions: `is_confirmed`, `has_consent`.
- One term per concept, the glossary's: «counterparty», never «contact» or «partner» for the same thing;
  «assessment», never «score» or «rating».
- Repository functions say what they read or write and by what: `get_mailbox_by_id_for_owner`.

## Never

- Never add a new file named after a banned catch-all.
- Never introduce a synonym for a glossary term; add the term to the glossary first.

Enforced by: review (`invariant-reviewer`).
