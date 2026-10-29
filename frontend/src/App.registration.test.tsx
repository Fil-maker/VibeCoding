import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  ANNA,
  alertWith,
  apiError,
  callsTo,
  fieldOf,
  heading,
  json,
  press,
  renderApp,
  signedIn,
  type,
} from './test/appHarness';

const CONFIRMATION = 'Мы отправили письмо со ссылкой для подтверждения на anna@romashka.test';
const MAIL_FAILURE = 'Не удалось отправить письмо. Попробуйте зарегистрироваться ещё раз позже';

function fillRegistration(email: string, password: string): void {
  type('Имя', 'Анна Петрова');
  type('Email', email);
  type('Пароль', password);
  press('Зарегистрироваться');
}

describe('registration page', () => {
  it('FR-1 «Registration form»: has «Имя», «Email», «Пароль» and no «Название организации»', async () => {
    renderApp({ path: '/register' });

    await heading('Регистрация');
    expect(screen.getByLabelText('Имя')).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Пароль')).toBeInTheDocument();
    expect(screen.queryByLabelText('Название организации')).not.toBeInTheDocument();
  });

  it('FR-1 «Successful registration»: posts exactly {name, email, password} and shows where the confirmation went', async () => {
    const app = renderApp({
      path: '/register',
      routes: {
        'POST /auth/registrations': () =>
          json(201, { email: 'anna@romashka.test', email_sent: true }),
      },
    });

    await heading('Регистрация');
    fillRegistration('Anna@Romashka.test', 'correct-horse-1');

    expect(await screen.findByText(CONFIRMATION)).toBeInTheDocument();
    expect(callsTo(app, 'POST', '/auth/registrations')[0]?.body).toEqual({
      name: 'Анна Петрова',
      email: 'Anna@Romashka.test',
      password: 'correct-horse-1',
    });
  });

  it('FR-1 «The mail server is unavailable»: shows the mail-failure text, and a repeated registration is accepted', async () => {
    let attempts = 0;
    const app = renderApp({
      path: '/register',
      routes: {
        'POST /auth/registrations': () => {
          attempts += 1;
          return json(201, { email: 'anna@romashka.test', email_sent: attempts > 1 });
        },
      },
    });

    await heading('Регистрация');
    fillRegistration('anna@romashka.test', 'correct-horse-1');

    expect(await screen.findByText(MAIL_FAILURE)).toBeInTheDocument();
    expect(screen.queryByText(CONFIRMATION)).not.toBeInTheDocument();

    press('Зарегистрироваться');

    expect(await screen.findByText(CONFIRMATION)).toBeInTheDocument();
    expect(callsTo(app, 'POST', '/auth/registrations')).toHaveLength(2);
  });

  it('FR-1 «Email already belongs to a confirmed user»: shows «Этот email уже зарегистрирован»', async () => {
    renderApp({
      path: '/register',
      routes: { 'POST /auth/registrations': () => apiError(409, 'email_taken') },
    });

    await heading('Регистрация');
    fillRegistration('anna@romashka.test', 'correct-horse-1');

    await alertWith('Этот email уже зарегистрирован');
  });

  it('FR-1 «Invalid input»: each message is next to its own field', async () => {
    renderApp({
      path: '/register',
      routes: {
        'POST /auth/registrations': () =>
          apiError(422, 'validation_failed', {
            name: 'Укажите имя',
            email: 'Укажите корректный email',
            password: 'Пароль должен быть от 10 до 128 символов',
          }),
      },
    });

    await heading('Регистрация');
    type('Имя', ' ');
    type('Email', 'no-at-sign');
    type('Пароль', 'short');
    press('Зарегистрироваться');

    await screen.findByText('Укажите имя');
    expect(fieldOf('Имя')).toHaveTextContent('Укажите имя');
    expect(fieldOf('Email')).toHaveTextContent('Укажите корректный email');
    expect(fieldOf('Пароль')).toHaveTextContent('Пароль должен быть от 10 до 128 символов');
    expect(fieldOf('Email')).not.toHaveTextContent('Укажите имя');
    expect(fieldOf('Email')).not.toHaveTextContent('Пароль должен быть');
  });
});

describe('email confirmation page', () => {
  it('FR-2 «Confirmation by a valid link»: posts the fragment token and lands on the start page', async () => {
    const app = renderApp({
      path: '/confirm-email#token=confirm-token-1',
      routes: {
        'POST /auth/email-confirmations': (_body, session) => signedIn(session, ANNA),
      },
    });

    expect(await screen.findByText('Анна Петрова')).toBeInTheDocument();
    expect(screen.queryByText('Участники')).not.toBeInTheDocument();
    expect(window.location.pathname).toBe('/');
    expect(callsTo(app, 'POST', '/auth/email-confirmations')[0]?.body).toEqual({
      token: 'confirm-token-1',
    });
  });

  it('FR-2 «Expired or used link»: shows «Ссылка недействительна или устарела»', async () => {
    renderApp({
      path: '/confirm-email#token=old-token',
      routes: { 'POST /auth/email-confirmations': () => apiError(400, 'invalid_link') },
    });

    await alertWith('Ссылка недействительна или устарела');
    expect(screen.queryByRole('button', { name: 'Выйти' })).not.toBeInTheDocument();
  });
});
