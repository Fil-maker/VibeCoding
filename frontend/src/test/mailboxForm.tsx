// Helpers of the mailbox tests: the mailbox fixture, the texts and the lookups of the connect form
// and of its «Как подключить» block.
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { expect } from 'vitest';

import { ANNA, json, renderApp, type Handler, type Rendered } from './appHarness';

export interface MailboxJson {
  id: string;
  server: string;
  port: number;
  login: string;
  status: 'pending' | 'reading' | 'read' | 'failed';
  error: string | null;
  error_code: 'sign_in_failed' | 'unreachable' | 'read_failed' | null;
  last_read_at: string | null;
}

export function mailbox(overrides: Partial<MailboxJson> = {}): MailboxJson {
  return {
    id: 'aaaaaaaa-0000-4000-8000-000000000001',
    server: 'imap.yandex.ru',
    port: 993,
    login: 'anna@yandex.ru',
    status: 'pending',
    error: null,
    error_code: null,
    last_read_at: null,
    ...overrides,
  };
}

export const EXPLANATION =
  'Приложение только читает письма: не отправляет, не удаляет и не помечает их прочитанными. Для входа нужен пароль приложения — отдельный пароль для почтовых программ, который можно отозвать, не меняя основной.';
export const UNKNOWN_HINT =
  'Этот почтовый сервис нам незнаком. Адрес сервера IMAP и порт есть в справке вашей почты или у администратора домена.';
export const REFUSED = 'Не удалось войти в ящик: проверьте логин и пароль приложения';
export const HOW_TO = /^Как подключить /;

export function connectRoutes(post: Handler): Record<string, Handler> {
  return { 'GET /mailboxes': () => json(200, []), 'POST /mailboxes': post };
}

export async function openForm(routes?: Record<string, Handler>): Promise<Rendered> {
  const app = renderApp({
    path: '/mailboxes',
    me: ANNA,
    routes: routes ?? { 'GET /mailboxes': () => json(200, []) },
  });
  // The list has loaded: either it is empty or it holds the seeded mailbox.
  await waitFor(() => {
    expect(
      screen.queryByText('Ящики ещё не подключены') ?? screen.queryByText('anna@yandex.ru'),
    ).toBeInTheDocument();
  });
  return app;
}

export function field(label: string): HTMLInputElement {
  return screen.getByLabelText<HTMLInputElement>(label);
}

export function pickService(name: string): void {
  const select = screen.getByLabelText<HTMLSelectElement>('Почтовый сервис');
  const option = within(select).getByRole('option', { name });
  fireEvent.change(select, { target: { value: option.getAttribute('value') } });
}

export function serverSettings(): HTMLDetailsElement {
  const details = screen.getByText('Настройки сервера').closest('details');
  if (!details) throw new Error('«Настройки сервера» is not a disclosure');
  return details;
}

// The «Как подключить <service>» block: a region named by its title.
export async function howToBlock(title: string): Promise<HTMLElement> {
  return screen.findByRole('region', { name: title });
}

export function stepsOf(block: HTMLElement): string[] {
  return within(block)
    .getAllByRole('listitem')
    .map((item) => item.textContent);
}

export function helpHref(block: HTMLElement): URL {
  return new URL(within(block).getByRole('link').getAttribute('href') ?? '');
}

// Lets pending timers and promises run before the test counts requests.
export async function settle(): Promise<void> {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

export function expectNoHowTo(): void {
  expect(screen.queryByRole('region', { name: HOW_TO })).not.toBeInTheDocument();
  expect(screen.queryByRole('link', { name: /^Справка/ })).not.toBeInTheDocument();
}

export function formOf(): HTMLElement {
  const form = field('Адрес почты').closest('form');
  if (!form) throw new Error('No form');
  return form;
}
