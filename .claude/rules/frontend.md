---
paths:
  - "frontend/**"
---

# Frontend

The React + TypeScript SPA. Neighbours: `api-contract.md` for the generated client, `code-quality.md`
for TypeScript, `testing.md` for tests. Facts: `docs/architecture.md` «Components and processes».

## Rules

- Current React and Vite syntax only: function components and hooks.
- Server data only through the generated client in `frontend/src/api/generated/`, wrapped by one query
  layer (chosen in task 0.1); components never call `fetch` directly.
- Auth state and route guards live in one place; components do not check roles themselves beyond what
  the API returns.
- User text is rendered escaped by React. Never `dangerouslySetInnerHTML`; email bodies are shown as
  text, never as HTML.
- An assessment is always shown with its evidence links and the analysis model.
- UI text is Russian, written in the component (or one messages module when there are several); dates
  and numbers formatted with `Intl` for `ru-RU`.
- Styling: one token source for colors, sizes and spacing; components use tokens, never raw colors or
  pixel sizes.
- Forms validate on the client for convenience only; the server is the authority.
- Accessible: labels on inputs, buttons are `<button>`, keyboard reachable.

## Never

- Never edit `frontend/src/api/generated/` by hand.
- Never store tokens in `localStorage`.
- Never show another user's correspondence that the API did not return for this user.

Enforced by: ESLint (react, react-hooks, no-danger), `tsc --strict`, Prettier; the rest by review.
