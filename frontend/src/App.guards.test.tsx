import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ANNA, BORIS, heading, json, press, renderApp, signedIn, type } from './test/appHarness';

describe('route guards', () => {
  it('FR-17 «A signed-out visitor opens a protected page»: «Участники» shows «Вход» and returns there after sign-in', async () => {
    renderApp({
      path: '/members',
      routes: {
        'POST /auth/sessions': (_body, session) => signedIn(session, ANNA),
        'GET /members': () => json(200, { items: [], next_cursor: null }),
        'GET /invitations': () => json(200, { items: [], next_cursor: null }),
      },
    });

    await heading('Вход');
    type('Email', ANNA.email);
    type('Пароль', 'correct-horse-1');
    press('Войти');

    await heading('Участники');
    expect(window.location.pathname).toBe('/members');
  });

  it('FR-17 «Every page other than … requires a signed-in user»: the start page sends a signed-out visitor to «Вход»', async () => {
    renderApp({ path: '/' });

    await heading('Вход');
    expect(screen.queryByRole('button', { name: 'Выйти' })).not.toBeInTheDocument();
  });

  it('FR-19 «An employee opens the members page»: «Страница не найдена»', async () => {
    renderApp({ path: '/members', me: BORIS });

    await heading('Страница не найдена');
    expect(screen.queryByRole('heading', { level: 1, name: 'Участники' })).not.toBeInTheDocument();
  });

  it('SPA pages «any other»: «Страница не найдена» for a signed-in user', async () => {
    renderApp({ path: '/no-such-page', me: ANNA });

    await heading('Страница не найдена');
  });

  it('SPA pages «any other»: «Страница не найдена» for a signed-out visitor', async () => {
    renderApp({ path: '/no-such-page' });

    await heading('Страница не найдена');
  });
});
