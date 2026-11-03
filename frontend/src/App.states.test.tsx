import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ANNA, heading, json, press, renderApp, rowOf, type Handler } from './test/appHarness';
import { openRules } from './test/rulesPage';

const PROJECT_ID = 'dddddddd-0000-4000-8000-000000000001';
const CHAIN_ID = 'bbbbbbbb-0000-4000-8000-000000000001';
const noBoxes = { 'GET /mailboxes': () => json(200, []) };
const pending: Handler = () => new Promise<Response>(() => undefined);

describe('loading', () => {
  it.each([
    ['/projects', 'GET /projects'],
    ['/chains', 'GET /reply-chains'],
    ['/mailboxes', 'GET /mailboxes'],
    ['/rules', 'GET /rules'],
    ['/', 'GET /projects'],
    [`/projects/${PROJECT_ID}`, `GET /projects/${PROJECT_ID}`],
    [`/chains/${CHAIN_ID}`, `GET /reply-chains/${CHAIN_ID}`],
  ])('FR-51 «Загрузка…» while %s loads its data', async (path, route) => {
    renderApp({ path, me: ANNA, routes: { 'GET /mailboxes': pending, [route]: pending } });

    await screen.findByText('Анна Петрова');
    expect(await screen.findByText('Загрузка…')).toBeInTheDocument();
  });
});

describe('empty pages', () => {
  it('FR-51 «No correspondence yet»: «Переписка» shows «Писем пока нет: подключите почтовый ящик» and «Подключить ящик» opens «Почтовые ящики»', async () => {
    renderApp({
      path: '/chains',
      me: ANNA,
      routes: {
        ...noBoxes,
        'GET /reply-chains': () => json(200, { items: [], next_cursor: null }),
      },
    });

    expect(await screen.findByText('Писем пока нет: подключите почтовый ящик')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('link', { name: 'Подключить ящик' }));

    await heading('Почтовые ящики');
    expect(window.location.pathname).toBe('/mailboxes');
  });

  it('FR-51 empty «Проекты»: «Проектов пока нет: создайте первый» with «Создать проект» that opens «Новый проект»', async () => {
    renderApp({ path: '/projects', me: ANNA, routes: { 'GET /projects': () => json(200, []) } });

    expect(await screen.findByText('Проектов пока нет: создайте первый')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('link', { name: 'Создать проект' }));

    await heading('Новый проект');
    expect(window.location.pathname).toBe('/projects/new');
  });

  it('FR-51 «Rules before any project»: «Правила» shows «Сначала создайте проект» and «Создать проект» opens «Новый проект»', async () => {
    openRules({ rules: [] }, { projects: [] });

    expect(await screen.findByText('Сначала создайте проект')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('link', { name: 'Создать проект' }));

    await heading('Новый проект');
    expect(window.location.pathname).toBe('/projects/new');
  });
});

describe('failed pages', () => {
  it('FR-51 «The server does not answer, then answers»: «Сервер не отвечает» in one alert with «Повторить», then the list of projects', async () => {
    let up = false;
    const office = {
      id: 'dddddddd-0000-4000-8000-000000000001',
      name: 'Ремонт офиса',
      filled: true,
      placed_count: 3,
      unassigned_count: 0,
    };
    renderApp({
      path: '/projects',
      me: ANNA,
      routes: {
        'GET /projects': () =>
          up ? json(200, [office]) : Promise.reject(new TypeError('Failed to fetch')),
      },
    });

    const alert = await screen.findByRole('alert');
    expect(within(alert).getByText('Сервер не отвечает')).toBeInTheDocument();
    expect(screen.getAllByRole('alert')).toHaveLength(1);
    expect(within(alert).getByRole('button', { name: 'Повторить' })).toBeInTheDocument();

    up = true;
    press('Повторить');

    await rowOf('Ремонт офиса');
    await waitFor(() => {
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });
});
