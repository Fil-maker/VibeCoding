import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  ANNA,
  alertWith,
  apiError,
  callsTo,
  fieldOf,
  heading,
  press,
  renderApp,
  signedIn,
  type,
} from './test/appHarness';

function postedEmail(body: unknown): string {
  const email = (body as { email?: unknown } | undefined)?.email;
  return typeof email === 'string' ? email.trim().toLowerCase() : '';
}

describe('sign-in page', () => {
  it('FR-4 «Successful sign-in»: lands on the start page with the name', async () => {
    const app = renderApp({
      path: '/sign-in',
      routes: { 'POST /auth/sessions': (_body, session) => signedIn(session, ANNA) },
    });

    await heading('Вход');
    type('Email', ' ANNA@romashka.test ');
    type('Пароль', 'correct-horse-1');
    press('Войти');

    expect(await screen.findByText('Анна Петрова')).toBeInTheDocument();
    expect(screen.queryByText('ООО Ромашка')).not.toBeInTheDocument();
    expect(window.location.pathname).toBe('/');
    expect(screen.queryByRole('heading', { level: 1, name: 'Вход' })).not.toBeInTheDocument();
    const posted = callsTo(app, 'POST', '/auth/sessions');
    expect(postedEmail(posted[0]?.body)).toBe('anna@romashka.test');
    expect((posted[0]?.body as { password?: unknown }).password).toBe('correct-horse-1');
  });

  it.each([
    [
      'FR-4 «Wrong password or unknown email» (wrong password)',
      'anna@romashka.test',
      401,
      'invalid_credentials',
      'Неверный email или пароль',
    ],
    [
      'FR-4 «Wrong password or unknown email» (unknown email)',
      'nobody@romashka.test',
      401,
      'invalid_credentials',
      'Неверный email или пароль',
    ],
    [
      'FR-2 «Sign-in before confirmation»',
      'anna@romashka.test',
      403,
      'email_not_confirmed',
      'Подтвердите email: ссылка в письме, которое мы отправили',
    ],
    [
      'FR-5 «The fifth wrong password locks sign-in»',
      'anna@romashka.test',
      429,
      'sign_in_locked',
      'Слишком много попыток входа. Попробуйте через 15 минут',
    ],
  ])('%s: shows the refusal text', async (_scenario, email, status, code, text) => {
    renderApp({
      path: '/sign-in',
      routes: { 'POST /auth/sessions': () => apiError(status, code) },
    });

    await heading('Вход');
    type('Email', email);
    type(
      'Пароль',
      email.startsWith('anna') && status === 401 ? 'wrong-password-1' : 'some-password-1',
    );
    press('Войти');

    await alertWith(text);
    expect(screen.getByRole('heading', { level: 1, name: 'Вход' })).toBeInTheDocument();
  });

  it('FR-4 «Empty fields»: both fields empty, the refusal text of the server answer is shown', async () => {
    const app = renderApp({
      path: '/sign-in',
      routes: {
        'POST /auth/sessions': () =>
          apiError(422, 'validation_failed', { password: 'Укажите email и пароль' }),
      },
    });

    await heading('Вход');
    press('Войти');

    expect(await screen.findByText('Укажите email и пароль')).toBeInTheDocument();
    expect(callsTo(app, 'POST', '/auth/sessions')).toHaveLength(1);
  });

  it('FR-4 «Empty fields»: only the password empty, the refusal text is shown next to its field', async () => {
    const app = renderApp({
      path: '/sign-in',
      routes: {
        'POST /auth/sessions': () =>
          apiError(422, 'validation_failed', { password: 'Укажите email и пароль' }),
      },
    });

    await heading('Вход');
    type('Email', 'anna@romashka.test');
    press('Войти');

    await screen.findByText('Укажите email и пароль');
    expect(callsTo(app, 'POST', '/auth/sessions')).toHaveLength(1);
    expect(fieldOf('Пароль')).toHaveTextContent('Укажите email и пароль');
  });

  it('SPA interface «Вход»: has the links «Забыли пароль?» and «Регистрация»', async () => {
    renderApp({ path: '/sign-in' });

    await heading('Вход');
    expect(screen.getByRole('link', { name: 'Забыли пароль?' })).toHaveAttribute(
      'href',
      '/forgot-password',
    );
    expect(screen.getByRole('link', { name: 'Регистрация' })).toHaveAttribute('href', '/register');
  });
});
