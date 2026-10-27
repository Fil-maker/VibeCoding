import { waitFor, within } from '@testing-library/react';
import { expect } from 'vitest';

import {
  ANNA,
  BORIS,
  type Handler,
  type Invitation,
  type Member,
  type Rendered,
} from './appHarness';
import { heading, json, renderApp, rowOf } from './appHarness';

// Fixtures and helpers of the «Участники» page tests.

export const ANNA_ROW: Member = {
  id: ANNA.user_id,
  name: 'Анна Петрова',
  email: 'anna@romashka.test',
  role: 'administrator',
  is_active: true,
};
export const BORIS_ROW: Member = {
  id: BORIS.user_id,
  name: 'Борис Иванов',
  email: 'boris@romashka.test',
  role: 'employee',
  is_active: true,
};
export const DINA_ROW: Member = {
  id: '33333333-3333-4333-8333-333333333333',
  name: 'Дина Орлова',
  email: 'dina@romashka.test',
  role: 'employee',
  is_active: true,
};

export function invitation(id: string, email: string, status: Invitation['status']): Invitation {
  const sentAt = status === 'not_sent' ? null : '2030-01-01T00:00:00Z';
  return { id, email, sent_at: sentAt, expires_at: '2030-01-08T00:00:00Z', status };
}

export function page(items: unknown[]): Response {
  return json(200, { items, next_cursor: null });
}

export function listRoutes(
  members: () => Member[],
  invitations: () => Invitation[],
): Record<string, Handler> {
  return {
    'GET /members': () => page(members()),
    'GET /invitations': () => page(invitations()),
  };
}

export async function openMembers(routes: Record<string, Handler>, me = ANNA): Promise<Rendered> {
  const app = renderApp({ path: '/members', me, routes });
  await heading('Участники');
  return app;
}

// Waits until the row that holds `key` shows `text` (the list was refreshed).
export async function expectRowShows(key: string, text: string): Promise<void> {
  await waitFor(async () => {
    expect(within(await rowOf(key)).getByText(text)).toBeInTheDocument();
  });
}
