import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { expect } from 'vitest';

import { ANNA, json, noContent, renderApp, type Handler, type Rendered } from './appHarness';

// Fixtures of the page «Правила» tests: the JSON of «Schemas» («Rule», «RuleInput»), a stateful stub of
// the rule routes, and lookups of the rule rows and of the forms.

export type ConditionJson = 'address' | 'domain' | 'subject';

export interface RuleJson {
  id: string;
  condition: ConditionJson;
  value: string;
  project: { id: string; name: string };
  thread_name: string | null;
}

export interface RuleInputJson {
  condition: ConditionJson;
  value: string;
  project_id: string;
  thread_name: string | null;
}

export const OFFICE = { id: 'dddddddd-0000-4000-8000-000000000001', name: 'Ремонт офиса' };
export const TECH = { id: 'dddddddd-0000-4000-8000-000000000002', name: 'Закупка техники' };

export const CONFIRM_DELETE = 'Удалить правило? Цепочки, уже размещённые им, останутся на месте';
export const EXISTS = 'Такое правило уже есть';

export const BY_ADDRESS: RuleJson = rule(
  1,
  'address',
  's.petrov@stroymaster.example',
  OFFICE,
  'Смета',
);
export const BY_DOMAIN: RuleJson = rule(2, 'domain', 'techsnab.example', TECH, null);
export const BY_SUBJECT: RuleJson = rule(3, 'subject', 'акт работ', OFFICE, 'Акты');

export function rule(
  n: number,
  condition: ConditionJson,
  value: string,
  project: { id: string; name: string },
  thread_name: string | null,
): RuleJson {
  return {
    id: `aaaaaaaa-0000-4000-8000-00000000000${String(n)}`,
    condition,
    value,
    project,
    thread_name,
  };
}

export const NEW_RULE_ID = 'aaaaaaaa-0000-4000-8000-000000000099';

export function asInput(body: unknown): RuleInputJson {
  return body as RuleInputJson;
}

export function projectSummaries(): unknown[] {
  return [OFFICE, TECH].map((project) => ({
    ...project,
    filled: true,
    placed_count: 1,
    unassigned_count: 0,
  }));
}

interface Options {
  projects?: unknown[];
  post?: Handler;
  put?: Handler;
  del?: Handler;
}

// The page /rules; GET /rules answers `state.rules`. By default a created rule is appended (value kept
// as lower case for an address and a domain, as the server does), an edit replaces the rule, a delete
// removes it.
export function openRules(state: { rules: RuleJson[] }, options: Options = {}): Rendered {
  const projects = options.projects ?? projectSummaries();
  const known = [OFFICE, TECH];
  const stored = (input: RuleInputJson, id: string): RuleJson => ({
    id,
    condition: input.condition,
    value: input.condition === 'subject' ? input.value.trim() : input.value.trim().toLowerCase(),
    project: known.find((candidate) => candidate.id === input.project_id) ?? OFFICE,
    thread_name:
      input.thread_name === null || input.thread_name.trim() === ''
        ? null
        : input.thread_name.trim(),
  });
  return renderApp({
    path: '/rules',
    me: ANNA,
    routes: {
      'GET /projects': () => json(200, projects),
      'GET /rules': () => json(200, state.rules),
      'POST /rules':
        options.post ??
        ((body) => {
          const created = stored(asInput(body), NEW_RULE_ID);
          state.rules = [...state.rules, created];
          return json(201, created);
        }),
      ...Object.fromEntries(
        state.rules.flatMap((existing) => [
          [
            `PUT /rules/${existing.id}`,
            options.put ??
              ((body: unknown) => {
                const changed = stored(asInput(body), existing.id);
                state.rules = state.rules.map((r) => (r.id === existing.id ? changed : r));
                return json(200, changed);
              }),
          ],
          [
            `DELETE /rules/${existing.id}`,
            options.del ??
              (() => {
                state.rules = state.rules.filter((r) => r.id !== existing.id);
                return noContent();
              }),
          ],
        ]),
      ),
    },
  });
}

// The list item of the rule whose text holds `value` (waits for it to be listed).
export async function ruleRow(value: string): Promise<HTMLElement> {
  return waitFor(() => {
    const row = screen.getAllByRole('listitem').find((item) => item.textContent.includes(value));
    if (!row) throw new Error(`No rule is listed with «${value}»`);
    return row;
  });
}

// The text of every listed rule without its buttons, in the order shown.
export function listedRules(): string[] {
  return screen
    .queryAllByRole('listitem')
    .map((item) => {
      const copy = item.cloneNode(true) as HTMLElement;
      copy.querySelectorAll('button').forEach((button) => {
        button.remove();
      });
      return copy.textContent.replace(/\s+/g, ' ').trim();
    })
    .filter((text) => text.includes('→'));
}

export function chooseIn(scope: HTMLElement, label: string, option: string): void {
  const select = within(scope).getByLabelText<HTMLSelectElement>(label);
  const found = within(select).getByRole('option', { name: option });
  fireEvent.change(select, { target: { value: (found as HTMLOptionElement).value } });
  expect(select.selectedOptions[0]?.textContent).toBe(option);
}

export function typeIn(scope: HTMLElement, label: string, value: string): void {
  fireEvent.change(within(scope).getByLabelText(label), { target: { value } });
}

export function pressIn(scope: HTMLElement, name: string): void {
  fireEvent.click(within(scope).getByRole('button', { name }));
}

// The form «Создать правило» (the one that holds its button).
export function createForm(): HTMLElement {
  const form = screen.getByRole('button', { name: 'Создать правило' }).closest('form');
  if (!form) throw new Error('«Создать правило» is not in a form');
  return form;
}

// The form of the rule being edited in place (the one that holds «Сохранить»).
export async function editForm(): Promise<HTMLElement> {
  const save = await screen.findByRole('button', { name: 'Сохранить' });
  const form = save.closest('form');
  if (!form) throw new Error('«Сохранить» is not in a form');
  return form;
}

// Fills the create form: the condition and project by their option names.
export async function fillCreate(
  condition: string,
  value: string,
  project: string | null,
  thread: string,
): Promise<void> {
  await screen.findByRole('option', { name: 'Ремонт офиса' });
  const form = createForm();
  chooseIn(form, 'Условие', condition);
  typeIn(form, 'Значение', value);
  if (project !== null) chooseIn(form, 'Проект', project);
  typeIn(form, 'Ветка', thread);
}

export function follows(a: HTMLElement, b: HTMLElement): boolean {
  return (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}

// Every request that is not a GET, as «METHOD /path», minus `allowed`.
export function writesOtherThan(app: Rendered, allowed: string[]): string[] {
  return app.calls
    .filter((call) => call.method !== 'GET')
    .map((call) => `${call.method} ${call.path}`)
    .filter((call) => !allowed.includes(call));
}

// The container of one field inside `scope`: the widest ancestor of the labelled control that holds no
// other control and stays inside the scope.
export function fieldOfIn(scope: HTMLElement, label: string): HTMLElement {
  let container: HTMLElement = within(scope).getByLabelText(label);
  for (;;) {
    const parent = container.parentElement;
    if (
      !parent ||
      parent === scope ||
      parent.querySelectorAll('input, textarea, select').length > 1
    ) {
      return container;
    }
    container = parent;
  }
}
