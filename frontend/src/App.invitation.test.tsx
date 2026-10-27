import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  BORIS,
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

const PREVIEW = { organization_name: 'ООО Ромашка', email: 'boris@romashka.test' };

describe('invitation page', () => {
  it('FR-12 «Successful acceptance»: shows the organization and email, then lands on the employee start page', async () => {
    const app = renderApp({
      path: '/invitation#token=invite-token-1',
      routes: {
        'POST /invitations/preview': () => json(200, PREVIEW),
        'POST /invitations/accept': (_body, session) => signedIn(session, BORIS),
      },
    });

    await heading('Приглашение');
    expect(await screen.findByText(/ООО Ромашка/)).toBeInTheDocument();
    expect(screen.getByText(/boris@romashka\.test/)).toBeInTheDocument();
    expect(callsTo(app, 'POST', '/invitations/preview')[0]?.body).toEqual({
      token: 'invite-token-1',
    });

    type('Имя', 'Борис Иванов');
    type('Пароль', 'boris-password-1');
    press('Принять приглашение');

    expect(await screen.findByText('Борис Иванов')).toBeInTheDocument();
    expect(screen.getByText('ООО Ромашка')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Выйти' })).toBeInTheDocument();
    expect(screen.queryByText('Участники')).not.toBeInTheDocument();
    expect(callsTo(app, 'POST', '/invitations/accept')[0]?.body).toEqual({
      token: 'invite-token-1',
      name: 'Борис Иванов',
      password: 'boris-password-1',
    });
  });

  it('FR-12 «A used, revoked, replaced or expired link»: shows «Приглашение недействительно или устарело»', async () => {
    renderApp({
      path: '/invitation#token=old-token',
      routes: { 'POST /invitations/preview': () => apiError(400, 'invalid_invitation') },
    });

    await heading('Приглашение');
    expect(await screen.findByText('Приглашение недействительно или устарело')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Принять приглашение' })).not.toBeInTheDocument();
  });

  it('FR-12 «The email became a user meanwhile»: shows «Этот email уже зарегистрирован»', async () => {
    renderApp({
      path: '/invitation#token=invite-token-1',
      routes: {
        'POST /invitations/preview': () => json(200, PREVIEW),
        'POST /invitations/accept': () => apiError(409, 'email_taken'),
      },
    });

    await heading('Приглашение');
    await screen.findByText(/ООО Ромашка/);
    type('Имя', 'Борис Иванов');
    type('Пароль', 'boris-password-1');
    press('Принять приглашение');

    await alertWith('Этот email уже зарегистрирован');
  });

  it('FR-12 «name (1–200 characters) and a password of 10–128 characters»: the messages are next to their fields', async () => {
    renderApp({
      path: '/invitation#token=invite-token-1',
      routes: {
        'POST /invitations/preview': () => json(200, PREVIEW),
        'POST /invitations/accept': () =>
          apiError(422, 'validation_failed', {
            name: 'Укажите имя',
            password: 'Пароль должен быть от 10 до 128 символов',
          }),
      },
    });

    await heading('Приглашение');
    await screen.findByText(/ООО Ромашка/);
    type('Пароль', 'short');
    press('Принять приглашение');

    await screen.findByText('Укажите имя');
    expect(fieldOf('Имя')).toHaveTextContent('Укажите имя');
    expect(fieldOf('Пароль')).toHaveTextContent('Пароль должен быть от 10 до 128 символов');
  });
});
