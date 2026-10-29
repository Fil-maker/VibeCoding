import { QueryClient } from '@tanstack/react-query';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { vi } from 'vitest';

import { App } from '../App';

// Shared harness of the page-level tests: renders <App> at a path with a stubbed fetch that is routed
// by "METHOD /path" under /api/v1. No network, no timers.

export interface Me {
  user_id: string;
  name: string;
  email: string;
}

export const ANNA: Me = {
  user_id: '11111111-1111-4111-8111-111111111111',
  name: 'Анна Петрова',
  email: 'anna@romashka.test',
};

export const MESSAGES: Record<string, string> = {
  email_taken: 'Этот email уже зарегистрирован',
  invalid_link: 'Ссылка недействительна или устарела',
  invalid_credentials: 'Неверный email или пароль',
  email_not_confirmed: 'Подтвердите email: ссылка в письме, которое мы отправили',
  sign_in_locked: 'Слишком много попыток входа. Попробуйте через 15 минут',
  not_signed_in: 'Войдите в систему',
  not_found: 'Не найдено',
  validation_failed: 'Проверьте поля формы',
};

export interface Session {
  me: Me | null;
}

export interface Call {
  method: string;
  path: string;
  body: unknown;
}

export type Handler = (body: unknown, session: Session) => Response;

export function json(status: number, body: unknown): Response {
  return Response.json(body, { status });
}

export function noContent(): Response {
  return new Response(null, { status: 204 });
}

export function apiError(status: number, code: string, fields?: Record<string, string>): Response {
  const message = MESSAGES[code] ?? code;
  return json(status, { error: { code, message, ...(fields ? { fields } : {}) } });
}

export function signedIn(session: Session, me: Me): Response {
  session.me = me;
  return json(200, me);
}

export interface Rendered {
  calls: Call[];
  session: Session;
}

interface Options {
  path: string;
  me?: Me;
  routes?: Record<string, Handler>;
}

// Renders the app at `path` (it may hold a #token fragment). `me` is the already signed-in user.
export function renderApp({ path, me, routes = {} }: Options): Rendered {
  const session: Session = { me: me ?? null };
  const calls: Call[] = [];
  const table: Record<string, Handler> = {
    'GET /auth/me': (_body, s) => (s.me ? json(200, s.me) : apiError(401, 'not_signed_in')),
    'DELETE /auth/sessions/current': (_body, s) => {
      s.me = null;
      return noContent();
    },
    ...routes,
  };
  vi.stubGlobal(
    'fetch',
    vi.fn(async (request: Request): Promise<Response> => {
      const url = new URL(request.url);
      const text = await request.clone().text();
      const body: unknown = text === '' ? undefined : JSON.parse(text);
      const apiPath = url.pathname.replace(/^\/api\/v1/, '');
      calls.push({ method: request.method, path: apiPath, body });
      const handler = table[`${request.method} ${apiPath}`];
      return handler
        ? handler(body, session)
        : json(500, { unrouted: `${request.method} ${apiPath}` });
    }),
  );
  window.history.pushState({}, '', path);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<App queryClient={queryClient} />);
  return { calls, session };
}

export function callsTo(rendered: Rendered, method: string, path: string): Call[] {
  return rendered.calls.filter((call) => call.method === method && call.path === path);
}

export function type(label: string, value: string): void {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

export function press(name: string): void {
  fireEvent.click(screen.getByRole('button', { name }));
}

export async function heading(name: string): Promise<HTMLElement> {
  return screen.findByRole('heading', { level: 1, name });
}

export async function alertWith(text: string): Promise<void> {
  const alert = await screen.findByRole('alert');
  within(alert).getByText(text);
}

// The table row or list item that holds `text`.
export async function rowOf(text: string): Promise<HTMLElement> {
  const cell = await screen.findByText(text);
  const row = cell.closest<HTMLElement>('tr, li');
  if (!row) throw new Error(`No row holds «${text}»`);
  return row;
}

// Moves the open app to another path, as the browser's back/forward would.
export function navigate(path: string): void {
  act(() => {
    window.history.pushState({}, '', path);
    window.dispatchEvent(new PopStateEvent('popstate'));
  });
}

// The container of one form field: the widest ancestor of the labelled input that holds no other input
// and stays inside the form. The field's own message must be inside it.
export function fieldOf(label: string): HTMLElement {
  let container: HTMLElement = screen.getByLabelText(label);
  for (;;) {
    const parent = container.parentElement;
    if (!parent || parent.tagName === 'FORM' || parent.querySelectorAll('input').length > 1) {
      return container;
    }
    container = parent;
  }
}
