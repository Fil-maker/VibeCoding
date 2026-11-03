import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  ANNA,
  callsTo,
  heading,
  json,
  renderApp,
  rowOf,
  type Handler,
  type Me,
  type Rendered,
} from './test/appHarness';
import { PROJECT_ID, tree } from './test/projectTrees';

const VERA: Me = {
  user_id: '22222222-2222-4222-8222-222222222222',
  name: 'Вера Орлова',
  email: 'vera@romashka.test',
};

const SECOND_PROJECT_ID = 'dddddddd-0000-4000-8000-000000000002';

interface SummaryJson {
  id: string;
  name: string;
  filled: boolean;
  placed_count: number;
  unassigned_count: number;
}

function mailbox(login: string, overrides: Record<string, unknown> = {}): unknown {
  return {
    id: 'aaaaaaaa-0000-4000-8000-000000000001',
    server: 'imap.yandex.ru',
    port: 993,
    login,
    status: 'read',
    error: null,
    last_read_at: '2026-10-20T09:30:00Z',
    ...overrides,
  };
}

const ANNA_BOX = mailbox('anna@yandex.ru');
const VERA_BOX = mailbox('vera@mail.test', { id: 'aaaaaaaa-0000-4000-8000-000000000002' });

function summary(filled: boolean, id = PROJECT_ID, name = 'Ремонт офиса'): SummaryJson {
  return { id, name, filled, placed_count: filled ? 3 : 0, unassigned_count: 0 };
}

// The routes answer the mailboxes and projects of `owner` only, as the server does.
function dataOf(owner: Me, boxes: unknown[], projects: SummaryJson[]): Record<string, Handler> {
  const trees = Object.fromEntries(
    projects.map((p) => [
      `GET /projects/${p.id}`,
      (): Response => json(200, tree({ id: p.id, name: p.name, filled: false })),
    ]),
  );
  return {
    ...trees,
    'GET /mailboxes': (_body, session) =>
      json(200, session.me?.user_id === owner.user_id ? boxes : []),
    'GET /projects': (_body, session) =>
      json(200, session.me?.user_id === owner.user_id ? projects : []),
  };
}

// Waits until the page has asked both lists and shows its steps.
async function settled(app: Rendered): Promise<void> {
  await heading('Первые шаги');
  await screen.findByText('Заполните проект');
  await waitFor(() => {
    expect(callsTo(app, 'GET', '/mailboxes').length).toBeGreaterThan(0);
    expect(callsTo(app, 'GET', '/projects').length).toBeGreaterThan(0);
  });
}

describe('start page: first steps', () => {
  it('FR-50 «A new user»: «Первые шаги» shows no step «Готово» and «Подключите почтовый ящик» opens «Почтовые ящики»', async () => {
    renderApp({ path: '/', me: ANNA, routes: dataOf(ANNA, [], []) });

    await heading('Первые шаги');
    expect(screen.getByRole('link', { name: 'Подключите почтовый ящик' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Создайте проект' })).toBeInTheDocument();
    expect(screen.getByText('Заполните проект')).toBeInTheDocument();
    expect(screen.queryByText('Готово')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('link', { name: 'Подключите почтовый ящик' }));

    await heading('Почтовые ящики');
  });

  it('FR-50 «Part of the way»: the first two steps show «Готово» and «Заполните проект» opens «Ремонт офиса»', async () => {
    renderApp({ path: '/', me: ANNA, routes: dataOf(ANNA, [ANNA_BOX], [summary(false)]) });

    await heading('Первые шаги');
    expect(await screen.findAllByText('Готово')).toHaveLength(2);
    expect(await rowOf('Подключите почтовый ящик')).toHaveTextContent('Готово');
    expect(await rowOf('Создайте проект')).toHaveTextContent('Готово');
    expect(await rowOf('Заполните проект')).not.toHaveTextContent('Готово');
    expect(
      screen.queryByRole('link', { name: 'Подключите почтовый ящик' }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Создайте проект' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('link', { name: 'Заполните проект' }));

    await heading('Ремонт офиса');
  });

  it('FR-50 «All steps done»: «Проекты» opens and lists «Ремонт офиса»', async () => {
    renderApp({ path: '/', me: ANNA, routes: dataOf(ANNA, [ANNA_BOX], [summary(true)]) });

    await heading('Проекты');
    expect(window.location.pathname).toBe('/projects');
    await rowOf('Ремонт офиса');
    expect(screen.queryByText('Первые шаги')).not.toBeInTheDocument();
  });

  it("FR-50 «Another user's progress does not count»: Анна sees «Первые шаги» with no step «Готово» while Вера has a mailbox and a filled project", async () => {
    const app = renderApp({
      path: '/',
      me: ANNA,
      routes: dataOf(VERA, [VERA_BOX], [summary(true)]),
    });

    await settled(app);
    expect(screen.getByRole('link', { name: 'Подключите почтовый ящик' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Создайте проект' })).toBeInTheDocument();
    expect(screen.getByText('Заполните проект')).toBeInTheDocument();
    expect(screen.queryByText('Готово')).not.toBeInTheDocument();
    expect(window.location.pathname).toBe('/');
  });

  it('FR-50 clause: a mailbox in error status counts as connected', async () => {
    const failed = mailbox('anna@yandex.ru', { status: 'failed', error: 'сервер не отвечает' });
    renderApp({ path: '/', me: ANNA, routes: dataOf(ANNA, [failed], []) });

    await heading('Первые шаги');
    expect(await rowOf('Подключите почтовый ящик')).toHaveTextContent('Готово');
    expect(await rowOf('Создайте проект')).not.toHaveTextContent('Готово');
  });

  it('FR-50 clause: with several projects, one filled and one not, all steps are done and «Проекты» opens', async () => {
    const projects = [summary(false), summary(true, SECOND_PROJECT_ID, 'Закупка техники')];
    renderApp({ path: '/', me: ANNA, routes: dataOf(ANNA, [ANNA_BOX], projects) });

    await heading('Проекты');
    expect(window.location.pathname).toBe('/projects');
    await rowOf('Ремонт офиса');
    await rowOf('Закупка техники');
    expect(screen.queryByText('Первые шаги')).not.toBeInTheDocument();
  });

  it('FR-50 clause: with several projects and none filled, «Заполните проект» opens the first one in the list order', async () => {
    const projects = [summary(false, SECOND_PROJECT_ID, 'Закупка техники'), summary(false)];
    renderApp({ path: '/', me: ANNA, routes: dataOf(ANNA, [ANNA_BOX], projects) });

    await heading('Первые шаги');
    fireEvent.click(await screen.findByRole('link', { name: 'Заполните проект' }));

    await heading('Закупка техники');
    expect(window.location.pathname).toBe(`/projects/${SECOND_PROJECT_ID}`);
  });

  it("FR-50 clause: the page asks for no user identifier, only the signed-in user's own lists", async () => {
    const app = renderApp({ path: '/', me: ANNA, routes: dataOf(ANNA, [], []) });

    await settled(app);
    for (const call of app.calls) {
      const sent = `${call.path}${call.query}${JSON.stringify(call.body ?? '')}`;
      expect(sent).not.toContain(ANNA.user_id);
      expect(sent).not.toContain(ANNA.email);
    }
    const lists = app.calls.filter(
      (call) => call.path === '/mailboxes' || call.path === '/projects',
    );
    expect(lists.length).toBeGreaterThan(0);
    for (const call of lists) {
      expect(call.method).toBe('GET');
      expect(call.query).toBe('');
    }
  });

  it("FR-50 clause: «Создайте проект» on a new user's page opens «Новый проект»", async () => {
    renderApp({ path: '/', me: ANNA, routes: dataOf(ANNA, [], []) });

    fireEvent.click(await screen.findByRole('link', { name: 'Создайте проект' }));

    await heading('Новый проект');
    expect(window.location.pathname).toBe('/projects/new');
  });
});
