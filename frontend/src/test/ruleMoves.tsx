import { screen, waitFor, within } from '@testing-library/react';
import { expect } from 'vitest';

import { json, type Handler } from './appHarness';

// Fixtures of the panel «Применить правило сейчас?»: the JSON of «Schemas» («RuleMove», «RuleMoves»,
// «RuleApplied») and lookups of the panel.

export const PANEL_TITLE = 'Применить правило сейчас?';
export const NOTHING = 'Подходящих цепочек нет';

interface Ref {
  id: string;
  name: string;
}

export interface MoveJson {
  chain_id: string;
  subject: string;
  latest_email_at: string;
  current: {
    state: 'none' | 'placed';
    project: Ref | null;
    thread: Ref | null;
  };
  target: { project: Ref; thread_name: string | null };
}

export const CHAIN_A = 'cccccccc-0000-4000-8000-00000000000a';
export const CHAIN_B = 'cccccccc-0000-4000-8000-00000000000b';

export const NOT_PLACED: MoveJson['current'] = { state: 'none', project: null, thread: null };

export function move(
  chainId: string,
  subject: string,
  current: MoveJson['current'],
  target: MoveJson['target'],
): MoveJson {
  return { chain_id: chainId, subject, latest_email_at: '2026-10-01T10:00:00Z', current, target };
}

export function placedIn(project: Ref, thread: Ref | null): MoveJson['current'] {
  return { state: 'placed', project, thread };
}

export function movesPath(ruleId: string): string {
  return `/placements/by-rule/${ruleId}`;
}

export function movesAnswer(moves: MoveJson[]): Response {
  return json(200, { moves });
}

export function appliedAnswer(moved: number): Response {
  return json(200, { moved });
}

// The routes of one rule's moves: GET lists `moves`, POST answers `apply`.
export function moveRoutes(
  ruleId: string,
  moves: MoveJson[],
  apply: Handler = () => appliedAnswer(moves.length),
): Record<string, Handler> {
  return {
    [`GET ${movesPath(ruleId)}`]: () => movesAnswer(moves),
    [`POST ${movesPath(ruleId)}`]: apply,
  };
}

export function idsOf(body: unknown): string[] {
  return [...(body as { chain_ids: string[] }).chain_ids].sort();
}

// The panel: the nearest ancestor of its title (or of `anchor`) that holds a button and not the rest
// of the page. The title may show before the buttons do, so it waits for that ancestor.
export async function panel(anchor: string = PANEL_TITLE): Promise<HTMLElement> {
  return waitFor(() => {
    let container: HTMLElement | null = screen.getByText(anchor);
    while (container && within(container).queryAllByRole('button').length === 0) {
      container = container.parentElement;
    }
    if (!container) throw new Error('The panel «Применить правило сейчас?» holds no button');
    if (within(container).queryByRole('button', { name: 'Создать правило' })) {
      throw new Error('The panel is not separate from the rest of the page');
    }
    return container;
  });
}

export function textOf(element: HTMLElement): string {
  return element.textContent.replace(/\s+/g, ' ').trim();
}

export async function textShown(text: string): Promise<void> {
  await waitFor(() => {
    expect(textOf(document.body)).toContain(text);
  });
}
