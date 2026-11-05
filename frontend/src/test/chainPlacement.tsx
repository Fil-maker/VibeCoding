import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { expect } from 'vitest';

import { ANNA, apiError, json, renderApp, type Handler, type Rendered } from './appHarness';

// Fixtures of the chain page tests: the JSON of «Schemas» («ChainLocation», «PlacementMove»), a stateful
// stub of the placement routes, and lookups of the location block and the form «Перенести».

export type PlacementJson =
  | { kind: 'engine'; engine_version: string; similarity: number; rule?: null }
  | { kind: 'manual'; engine_version: null; similarity: null; rule?: null }
  | {
      kind: 'rule';
      engine_version: null;
      similarity: null;
      rule: { condition: 'address' | 'domain' | 'subject'; value: string };
    };

export interface LocationJson {
  state: 'placed' | 'none' | 'excluded';
  project: { id: string; name: string } | null;
  thread: { id: string; name: string } | null;
  placement: PlacementJson | null;
}

export interface PlacementMoveJson {
  project_id: string;
  thread_id: string | null;
  new_thread_name: string | null;
}

export const CHAIN_ID = 'bbbbbbbb-0000-4000-8000-000000000001';
export const PLACEMENT = `/placements/${CHAIN_ID}`;

export const OFFICE = { id: 'dddddddd-0000-4000-8000-000000000001', name: 'Ремонт офиса' };
export const TECH = { id: 'dddddddd-0000-4000-8000-000000000002', name: 'Закупка техники' };
export const ESTIMATE_THREAD = {
  id: 'ffffffff-0000-4000-8000-000000000001',
  name: 'Смета на ремонт офиса',
};
export const MONITORS_THREAD = {
  id: 'ffffffff-0000-4000-8000-000000000002',
  name: 'Закупка мониторов',
};

export const ENGINE_PLACEMENT: PlacementJson = {
  kind: 'engine',
  engine_version: 'text-1',
  similarity: 0.4271,
};
export const MANUAL_PLACEMENT: PlacementJson = {
  kind: 'manual',
  engine_version: null,
  similarity: null,
};

export const NONE: LocationJson = { state: 'none', project: null, thread: null, placement: null };
export const EXCLUDED: LocationJson = {
  state: 'excluded',
  project: null,
  thread: null,
  placement: null,
};

export function placed(
  project: { id: string; name: string },
  thread: { id: string; name: string } | null,
  placement: PlacementJson,
): LocationJson {
  return { state: 'placed', project, thread, placement };
}

const THREADS: Record<string, { id: string; name: string }[]> = {
  [OFFICE.id]: [ESTIMATE_THREAD],
  [TECH.id]: [MONITORS_THREAD],
};

export const NEW_THREAD_ID = 'ffffffff-0000-4000-8000-000000000099';

// What the server answers to a move: the chain placed by hand where the body says.
export function movedTo(body: PlacementMoveJson): LocationJson {
  const project = [OFFICE, TECH].find((candidate) => candidate.id === body.project_id) ?? null;
  const threads = THREADS[body.project_id] ?? [];
  const thread =
    body.new_thread_name !== null
      ? { id: NEW_THREAD_ID, name: body.new_thread_name }
      : (threads.find((candidate) => candidate.id === body.thread_id) ?? null);
  return placed(project ?? OFFICE, thread, MANUAL_PLACEMENT);
}

export function asMove(body: unknown): PlacementMoveJson {
  const raw = body as Partial<PlacementMoveJson>;
  return {
    project_id: raw.project_id ?? '',
    thread_id: raw.thread_id ?? null,
    new_thread_name: raw.new_thread_name ?? null,
  };
}

export interface ChainState {
  subject?: string;
  location: LocationJson;
}

interface Options {
  put?: Handler;
  del?: Handler;
}

// The chain page of CHAIN_ID; every GET of the location answers `state.location`. By default a move
// and a taking out change `state.location` as the real server would.
export function openChain(state: ChainState, options: Options = {}): Rendered {
  return renderApp({
    path: `/chains/${CHAIN_ID}`,
    me: ANNA,
    routes: {
      [`GET /reply-chains/${CHAIN_ID}`]: () =>
        json(200, {
          id: CHAIN_ID,
          subject: state.subject ?? 'Счёт на мониторы',
          participants: [{ address: 'oleg@stroy.test', name: null }],
          emails: [
            {
              id: 'cccccccc-0000-4000-8000-000000000001',
              sender: { address: 'oleg@stroy.test', name: null },
              to: [{ address: 'anna@yandex.ru', name: null }],
              cc: [],
              sent_at: '2026-10-20T09:00:00Z',
              subject: state.subject ?? 'Счёт на мониторы',
              text: 'Текст письма',
              attachments: [],
            },
          ],
        }),
      'GET /projects': () =>
        json(
          200,
          [OFFICE, TECH].map((project) => ({
            ...project,
            filled: true,
            placed_count: 1,
            unassigned_count: 0,
          })),
        ),
      [`GET /projects/${OFFICE.id}/threads`]: () => json(200, THREADS[OFFICE.id]),
      [`GET /projects/${TECH.id}/threads`]: () => json(200, THREADS[TECH.id]),
      [`GET ${PLACEMENT}`]: () => json(200, state.location),
      [`PUT ${PLACEMENT}`]:
        options.put ??
        ((body) => {
          state.location = movedTo(asMove(body));
          return json(200, state.location);
        }),
      [`DELETE ${PLACEMENT}`]:
        options.del ??
        (() => {
          state.location = EXCLUDED;
          return json(200, state.location);
        }),
    },
  });
}

// A 422 of the move with the message on the field «new_thread_name».
export function rejectedName(message: string): Handler {
  return () => apiError(422, 'validation_failed', { new_thread_name: message });
}

// The text of the block «Проект» around the link to a project (spaces collapsed).
export async function locationAround(projectName: string): Promise<HTMLElement> {
  const link = await screen.findByRole('link', { name: projectName });
  const block = link.parentElement;
  if (!block) throw new Error(`The link «${projectName}» has no block`);
  return block;
}

// Picks the option of a select of the form by the labels of both.
export async function choose(label: string, option: string): Promise<void> {
  const select = screen.getByLabelText<HTMLSelectElement>(label);
  const found = await within(select).findByRole('option', { name: option });
  fireEvent.change(select, { target: { value: (found as HTMLOptionElement).value } });
  await waitFor(() => {
    expect(select.selectedOptions[0]?.textContent).toBe(option);
  });
}
