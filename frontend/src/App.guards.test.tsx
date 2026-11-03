import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ANNA, heading, json, press, renderApp, signedIn, type } from './test/appHarness';

describe('route guards', () => {
  it('FR-17 «A signed-out visitor opens a protected page»: «Проекты» shows «Вход» and returns there after sign-in', async () => {
    renderApp({
      path: '/projects',
      routes: {
        'GET /projects': () => json(200, []),
        'POST /auth/sessions': (_body, session) => signedIn(session, ANNA),
      },
    });

    await heading('Вход');
    expect(screen.queryByRole('button', { name: 'Выйти' })).not.toBeInTheDocument();
    type('Email', ANNA.email);
    type('Пароль', 'correct-horse-1');
    press('Войти');

    expect(await screen.findByText('Анна Петрова')).toBeInTheDocument();
    await heading('Проекты');
    expect(window.location.pathname).toBe('/projects');
  });

  it('FR-12 «Migration»: a signed-in user opening /members sees «Страница не найдена»', async () => {
    renderApp({ path: '/members', me: ANNA });

    await heading('Страница не найдена');
    expect(screen.queryByRole('heading', { level: 1, name: 'Участники' })).not.toBeInTheDocument();
  });

  it.each(['/invitation', '/invitation#token=old-invitation-token'])(
    'FR-12 «Migration»: a visitor opening %s sees «Страница не найдена»',
    async (path) => {
      renderApp({ path });

      await heading('Страница не найдена');
    },
  );

  it('SPA pages «any other»: «Страница не найдена» for a signed-in user', async () => {
    renderApp({ path: '/no-such-page', me: ANNA });

    await heading('Страница не найдена');
  });

  it('SPA pages «any other»: «Страница не найдена» for a signed-out visitor', async () => {
    renderApp({ path: '/no-such-page' });

    await heading('Страница не найдена');
  });
});
