import { fireEvent, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { LOADING_MESSAGE } from './messages';
import { ANNA, callsTo, heading, json, navigate, press, renderApp } from './test/appHarness';
import { PROJECT_ID, tree } from './test/projectTrees';

const CHAIN_ID = 'bbbbbbbb-0000-4000-8000-000000000001';
const WIDTH = window.innerWidth;
const SECTIONS = ['Проекты', 'Переписка', 'Почтовые ящики', 'Правила'];
const LANDING = 'Переписка по проектам — в одном дереве';

const noProjects = { 'GET /projects': () => json(200, []) };
const noChains = { 'GET /reply-chains': () => json(200, { items: [], next_cursor: null }) };

function header(): HTMLElement {
  return screen.getByRole('banner');
}

// The texts of the header links marked as the current page.
function current(): string[] {
  return within(header())
    .getAllByRole('link')
    .filter((link) => link.getAttribute('aria-current') === 'page')
    .map((link) => link.textContent);
}

// The elements the keyboard reaches, in document order.
function tabOrder(): HTMLElement[] {
  return Array.from(
    document.querySelectorAll<HTMLElement>('a[href], button, input, select, textarea, [tabindex]'),
  ).filter((el) => el.tabIndex >= 0 && !el.hasAttribute('disabled'));
}

describe('landing page', () => {
  it('FR-48 «A guest opens the app»: «/» shows the landing page with «Зарегистрироваться» and «Войти», no user data, and «Войти» opens «Вход»', async () => {
    const app = renderApp({ path: '/' });

    await heading(LANDING);
    expect(screen.getByRole('link', { name: 'Зарегистрироваться' })).toHaveAttribute(
      'href',
      '/register',
    );
    expect(screen.queryByRole('button', { name: 'Выйти' })).not.toBeInTheDocument();
    expect(screen.queryByText('Анна Петрова')).not.toBeInTheDocument();
    expect(callsTo(app, 'GET', '/mailboxes')).toHaveLength(0);
    expect(callsTo(app, 'GET', '/projects')).toHaveLength(0);

    fireEvent.click(screen.getByRole('link', { name: 'Войти' }));

    await heading('Вход');
    expect(window.location.pathname).toBe('/sign-in');
  });

  it('FR-48 «Registration from the landing page»: «Зарегистрироваться» opens «Регистрация»', async () => {
    renderApp({ path: '/' });

    await heading(LANDING);
    fireEvent.click(screen.getByRole('link', { name: 'Зарегистрироваться' }));

    await heading('Регистрация');
    expect(window.location.pathname).toBe('/register');
  });

  it('FR-48 «A signed-in user opens «/»»: Анна sees the start page and not the landing page', async () => {
    renderApp({
      path: '/',
      me: ANNA,
      routes: { 'GET /mailboxes': () => json(200, []), ...noProjects },
    });

    await heading('Первые шаги');
    expect(screen.queryByRole('heading', { level: 1, name: LANDING })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Зарегистрироваться' })).not.toBeInTheDocument();
  });
});

describe('header and sections', () => {
  afterEach(() => {
    window.innerWidth = WIDTH;
  });

  it('FR-49 «Moving between sections»: from «Проекты», «Переписка» opens and is the only current section, with the name and «Выйти»', async () => {
    renderApp({ path: '/projects', me: ANNA, routes: { ...noProjects, ...noChains } });

    await heading('Проекты');
    expect(current()).toEqual(['Проекты']);
    fireEvent.click(within(header()).getByRole('link', { name: 'Переписка' }));

    await heading('Переписка');
    expect(window.location.pathname).toBe('/chains');
    expect(current()).toEqual(['Переписка']);
    expect(within(header()).getByText('Анна Петрова')).toBeInTheDocument();
    expect(within(header()).getByRole('button', { name: 'Выйти' })).toBeInTheDocument();
  });

  it('FR-49 «Header and sections»: «VibeCoding» opens the start page and the four sections are linked', async () => {
    renderApp({ path: '/projects', me: ANNA, routes: noProjects });

    await heading('Проекты');
    const bar = within(header());
    expect(bar.getByRole('link', { name: 'VibeCoding' })).toHaveAttribute('href', '/');
    expect(bar.getByRole('link', { name: 'Проекты' })).toHaveAttribute('href', '/projects');
    expect(bar.getByRole('link', { name: 'Переписка' })).toHaveAttribute('href', '/chains');
    expect(bar.getByRole('link', { name: 'Почтовые ящики' })).toHaveAttribute('href', '/mailboxes');
    expect(bar.getByRole('link', { name: 'Правила' })).toHaveAttribute('href', '/rules');
  });

  it("FR-49 «A project's page marks «Проекты»»: the page of «Ремонт офиса» marks «Проекты» as current", async () => {
    renderApp({
      path: `/projects/${PROJECT_ID}`,
      me: ANNA,
      routes: { [`GET /projects/${PROJECT_ID}`]: () => json(200, tree()) },
    });

    await heading('Ремонт офиса');
    expect(current()).toEqual(['Проекты']);
  });

  it('FR-49 «Header and sections»: a chain’s page marks «Переписка» as current', async () => {
    renderApp({
      path: `/chains/${CHAIN_ID}`,
      me: ANNA,
      routes: {
        [`GET /reply-chains/${CHAIN_ID}`]: () =>
          json(200, { id: CHAIN_ID, subject: 'Договор поставки', participants: [], emails: [] }),
      },
    });

    await screen.findByText('Договор поставки');
    expect(current()).toEqual(['Переписка']);
  });

  it('FR-49 «Sign-out from the header»: «Выйти» on «Правила» ends the session and shows the landing page', async () => {
    const app = renderApp({ path: '/rules', me: ANNA, routes: noProjects });

    await heading('Правила');
    fireEvent.click(within(header()).getByRole('button', { name: 'Выйти' }));

    await heading(LANDING);
    expect(callsTo(app, 'DELETE', '/auth/sessions/current')).toHaveLength(1);
    expect(app.session.me).toBeNull();
    expect(window.location.pathname).toBe('/');
  });

  it('FR-49 «The menu on a narrow screen»: «Меню» opens the sections, the name and «Выйти»; pressing «Переписка» closes it and opens «Переписка»', async () => {
    window.innerWidth = 360;
    renderApp({ path: '/projects', me: ANNA, routes: { ...noProjects, ...noChains } });

    await heading('Проекты');
    const toggle = within(header()).getByRole('button', { name: 'Меню' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    press('Меню');

    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    const menu = document.getElementById(toggle.getAttribute('aria-controls') ?? '');
    if (!menu) throw new Error('«Меню» controls no element');
    const items = within(menu);
    for (const name of SECTIONS) {
      expect(items.getByRole('link', { name })).toBeInTheDocument();
    }
    expect(items.getByText('Анна Петрова')).toBeInTheDocument();
    expect(items.getByRole('button', { name: 'Выйти' })).toBeInTheDocument();

    fireEvent.click(items.getByRole('link', { name: 'Переписка' }));

    await heading('Переписка');
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });

  it('FR-49 «The menu on a narrow screen»: «Меню» pressed again closes the menu', async () => {
    renderApp({ path: '/projects', me: ANNA, routes: noProjects });

    await heading('Проекты');
    const toggle = screen.getByRole('button', { name: 'Меню' });
    press('Меню');
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    press('Меню');

    expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });
});

describe('keyboard and titles', () => {
  it('FR-52 «Skipping the header»: «К содержимому» is reached first and moves focus to the content of «Проекты»', async () => {
    renderApp({ path: '/projects', me: ANNA, routes: noProjects });

    await heading('Проекты');
    const first = tabOrder()[0];
    if (!first) throw new Error('Nothing is reachable by the keyboard');
    expect(first).toHaveAccessibleName('К содержимому');
    first.focus();
    expect(document.activeElement).toBe(first);
    fireEvent.click(first);

    const content = screen.getByRole('main');
    expect(document.activeElement).toBe(content);
    expect(content).toContainElement(screen.getByRole('heading', { level: 1, name: 'Проекты' }));
  });

  it('FR-52 «Skipping the header»: «К содержимому» is the first element on the landing page too', async () => {
    renderApp({ path: '/' });

    await heading(LANDING);
    expect(tabOrder()[0]).toHaveAccessibleName('К содержимому');
  });

  it('FR-52 «Keyboard and page titles»: every header item is reachable by the keyboard', async () => {
    renderApp({ path: '/projects', me: ANNA, routes: noProjects });

    await heading('Проекты');
    const reachable = tabOrder();
    const bar = within(header());
    for (const el of [
      ...bar.getAllByRole('link'),
      bar.getByRole('button', { name: 'Меню' }),
      bar.getByRole('button', { name: 'Выйти' }),
    ]) {
      expect(reachable).toContain(el);
    }
  });

  it('FR-52 «The tab title»: the page of «Ремонт офиса» is titled «Ремонт офиса — VibeCoding»', async () => {
    renderApp({
      path: `/projects/${PROJECT_ID}`,
      me: ANNA,
      routes: { [`GET /projects/${PROJECT_ID}`]: () => json(200, tree()) },
    });

    await heading('Ремонт офиса');
    expect(document.title).toBe('Ремонт офиса — VibeCoding');
  });

  it('FR-52 «Keyboard and page titles»: «Проекты» is titled «Проекты — VibeCoding»', async () => {
    renderApp({ path: '/projects', me: ANNA, routes: noProjects });

    await heading('Проекты');
    expect(document.title).toBe('Проекты — VibeCoding');
  });

  it('FR-52 «Keyboard and page titles»: the landing page is titled «VibeCoding»', async () => {
    document.title = 'Другая страница';
    renderApp({ path: '/' });

    await heading(LANDING);
    expect(document.title).toBe('VibeCoding');
  });

  it('FR-52 «Keyboard and page titles»: the start page is titled «VibeCoding»', async () => {
    document.title = 'Другая страница';
    renderApp({
      path: '/',
      me: ANNA,
      routes: { 'GET /mailboxes': () => json(200, []), ...noProjects },
    });

    await heading('Первые шаги');
    expect(document.title).toBe('VibeCoding');
  });

  it('FR-52 clause: while the session loads, the tab reads «VibeCoding»', async () => {
    document.title = 'Другая страница';
    renderApp({
      path: '/projects',
      routes: { 'GET /auth/me': () => new Promise<Response>(() => undefined) },
    });

    await screen.findByText(LOADING_MESSAGE);
    expect(document.title).toBe('VibeCoding');
  });

  it('FR-52 «A page that does not exist»: a signed-in user sees «Страница не найдена» with the header and the tab title', async () => {
    renderApp({ path: '/no-such-page', me: ANNA });

    await heading('Страница не найдена');
    expect(within(header()).getByText('Анна Петрова')).toBeInTheDocument();
    expect(within(header()).getByRole('button', { name: 'Выйти' })).toBeInTheDocument();
    expect(document.title).toBe('Страница не найдена — VibeCoding');
  });

  it('FR-52 «A page that does not exist»: a signed-out visitor sees «Страница не найдена» in the guest frame with «VibeCoding» to «/»', async () => {
    renderApp({ path: '/no-such-page' });

    await heading('Страница не найдена');
    expect(within(header()).getByRole('link', { name: 'VibeCoding' })).toHaveAttribute('href', '/');
    expect(document.title).toBe('Страница не найдена — VibeCoding');
  });
});

describe('sign-out and protected pages', () => {
  it('FR-6 «Sign-out»: after «Выйти» the landing page shows, and opening «Проекты» then shows «Вход»', async () => {
    renderApp({ path: '/projects', me: ANNA, routes: noProjects });

    await heading('Проекты');
    press('Выйти');
    await heading(LANDING);

    navigate('/projects');
    await heading('Вход');
    expect(window.location.pathname).toBe('/sign-in');
  });
});
