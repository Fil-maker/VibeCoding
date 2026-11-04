# Design

## Context

The SPA styles with CSS modules over one token file, `frontend/src/styles/tokens.css`, loaded once by
`main.tsx`; `.claude/rules/frontend.md` already forbids raw colors and pixel sizes outside it. Buttons
are plain `<button className={styles.button}>`, all alike. The placement reason is the string from
`placementLabel()` in `features/projects/format.ts`, shown inline in the tree and on a chain page. The
project tree renders each counterparty as a `<section>` with an `<h2>`. The tables of «Проекты»,
«Переписка» and «Почтовые ящики» use `styles.table`, with no header row. The app frame (task 1.7) has a
header with the sections and folds it into a menu below `40rem`. Motivation: see proposal.md «Why».

## Goals / Non-Goals

**Goals:**

- One place for every color and size, with a light and a dark set.
- A small, typed set of UI pieces — button, badge — so pages cannot drift.
- Guards that run in `just test`, not a manual review.

**Non-Goals:**

- A CSS framework, a component library or CSS-in-JS.
- Any change of text, route, query or confirmation step.
- Visual regression tests by screenshots.

## Decisions

### Themes: a dark token set under `prefers-color-scheme`

`tokens.css` keeps the light values in `:root` and redefines only the color tokens inside
`@media (prefers-color-scheme: dark)`; `:root` sets `color-scheme: light dark` so native inputs,
selects and scrollbars follow. Components keep using the same token names.

- Alternative: a `data-theme` attribute set by script — needed only for a manual switch, which is out of
  scope; the media query needs no JavaScript and no flash on load.
- Alternative: two token files — two places to keep in step for every new token.

### Contrast and «no raw values» as tests

One Vitest file reads `tokens.css` and checks the contrast of text tokens (text, muted text, link,
danger, ok, each badge text) over their backgrounds (background, surface, badge background) in both
sets: at least 4.5:1. A second check scans every `.css` file under `frontend/src` except `tokens.css`
and every `.tsx` for hex, `rgb(`/`hsl(` colors, named colors in color properties and `px` values;
`style={{…}}` is not used today and stays forbidden.

- Alternative: a stylelint rule — a new tool and config for two checks; a test is enough and runs in
  `just test`.
- Media queries cannot read custom properties, so the breakpoint stays a literal `40rem` (not `px`), the
  same one the header uses.

### Buttons: a `Button` component with a `kind`

`components/Button.tsx` renders a `<button>` with `kind: 'primary' | 'secondary' | 'danger'`
(default `secondary`) and the usual button props; `type` defaults to `"button"`. Styles live in
`ui.module.css` as one base class and one class per kind. Primary: the main action of a form or page
(form submits, «Заполнить», «Применить», «Подключить»). Danger: the confirming button of «Отключить» a
mailbox, of «Удалить» a rule and of the project refill; the first press still only opens the
confirmation. Everything else is secondary. Every `<button>` in `features/` goes through it.

- Alternative: only CSS modifier classes — nothing stops a page from forgetting the class; the typed prop
  makes the kind a choice.

### The placement reason as a `PlacementBadge`

`features/projects/PlacementBadge.tsx` takes a placement and renders a `<span>` with the text of
`placementLabel()` unchanged and a style per kind: manual, rule, engine. It replaces the inline text in
the tree and in the chain's «Проект» block. The kind is carried by text as well as color, so color is
never the only signal.

- Alternative: lowercase short badges («вручную», «правило», «движок») with details in a tooltip — it
  would change texts specified in FR scenarios («Вручную», «Правило» with the rule, the similarity) and
  hide the reason behind a hover.

### Folding counterparties with `<details>`

Each counterparty becomes `<details open>` with the name and address in `<summary>`; «Неразобранное»
too. The browser gives keyboard and screen-reader support; nothing is remembered between visits.

- Alternative: a button with `aria-expanded` and state — more code for the same behavior.

### Tables become cards below `40rem`

`styles.table` gets a media query: rows and cells turn into blocks, each row a card with border, radius
and spacing from tokens. The cells already read on their own (a name, «N цепочек», a date), so no
labels are added. Panels lose their side margins at that width, and long words and addresses wrap
(`overflow-wrap: anywhere`) so nothing scrolls sideways at 360 px.

- Alternative: separate card markup for phones — two renderings of the same data.

### Leftover links

`ProjectsPage` shows the button «Создать проект» only when projects are listed; the empty state keeps its
link. The `<p><Link to="/">На главную</Link></p>` blocks go from «Проекты», «Правила», «Почтовые ящики»
and «Переписка»; `NotFoundPage` keeps its link, since a guest sees it without the sections. The
user's choice, recorded in this session.

## Interface

- `Button` (`frontend/src/components/Button.tsx`): props of a native `<button>` plus
  `kind?: 'primary' | 'secondary' | 'danger'`; renders a `<button>` whose accessible name is its
  children; `type` defaults to `"button"`; the kind is exposed as `data-kind` for tests.
- `PlacementBadge` (`frontend/src/features/projects/PlacementBadge.tsx`): prop `placement` of the
  generated `Placement` shape; renders the exact text of `placementLabel(placement)`; the kind is exposed
  as `data-kind` (`manual`, `rule`, `engine`).
- Tokens: every color token has a value in the light set and in the dark set. Color tokens are the
  `--color-*` custom properties with `#rrggbb` values; the dark set is
  `@media (prefers-color-scheme: dark) { :root { … } }` in `tokens.css`. Text tokens `--color-text`,
  `--color-text-muted`, `--color-link`, `--color-danger`, `--color-ok` sit over `--color-background`
  and `--color-surface`; each button kind (`button-primary`, `button-danger`) and badge kind
  (`badge-manual`, `badge-rule`, `badge-engine`) has `--color-<kind>-text` over `--color-<kind>-bg`.

## Risks / Trade-offs

- [jsdom does not lay out pages, so «reads at 360 px» cannot be unit-tested] → a manual flow check in
  the browser at 360 px on every page, light and dark.
- [A raw value slips into a `.tsx` as a string] → the scan covers `.tsx` files too.
- [The danger color in dark mode reads poorly on a dark surface] → the contrast test covers danger text
  and the danger button in both sets.

## Migration Plan

SPA only, no data. Rollback: revert the commit.
