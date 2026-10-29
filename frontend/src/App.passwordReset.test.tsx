import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  alertWith,
  apiError,
  callsTo,
  fieldOf,
  heading,
  noContent,
  press,
  renderApp,
  type,
} from './test/appHarness';

const COMMON_ANSWER =
  'Если такой email зарегистрирован, мы отправили на него ссылку для сброса пароля';

function accepted(): Response {
  return new Response(null, { status: 202 });
}

describe('forgot-password page', () => {
  it('FR-7 «Reset requested for a registered email»: one request and the common answer', async () => {
    const app = renderApp({
      path: '/forgot-password',
      routes: { 'POST /auth/password-resets': accepted },
    });

    await heading('Восстановление пароля');
    type('Email', 'anna@romashka.test');
    press('Отправить ссылку');

    expect(await screen.findByText(COMMON_ANSWER)).toBeInTheDocument();
    const posts = callsTo(app, 'POST', '/auth/password-resets');
    expect(posts).toHaveLength(1);
    expect(posts[0]?.body).toEqual({ email: 'anna@romashka.test' });
  });

  it('FR-7 «Reset requested for an unknown email»: the same common answer', async () => {
    const app = renderApp({
      path: '/forgot-password',
      routes: { 'POST /auth/password-resets': accepted },
    });

    await heading('Восстановление пароля');
    type('Email', 'nobody@romashka.test');
    press('Отправить ссылку');

    expect(await screen.findByText(COMMON_ANSWER)).toBeInTheDocument();
    expect(callsTo(app, 'POST', '/auth/password-resets')[0]?.body).toEqual({
      email: 'nobody@romashka.test',
    });
  });
});

describe('reset-password page', () => {
  it('FR-8 «Password reset ends old sessions»: posts the fragment token with the new password', async () => {
    const app = renderApp({
      path: '/reset-password#token=reset-token-1',
      routes: { 'POST /auth/password-resets/complete': () => noContent() },
    });

    await heading('Новый пароль');
    type('Новый пароль', 'new-correct-horse-2');
    press('Сохранить пароль');

    await waitFor(() => {
      expect(callsTo(app, 'POST', '/auth/password-resets/complete')).toHaveLength(1);
    });
    expect(callsTo(app, 'POST', '/auth/password-resets/complete')[0]?.body).toEqual({
      token: 'reset-token-1',
      password: 'new-correct-horse-2',
    });
  });

  it('FR-7 «A new request replaces the earlier link»: the earlier link shows «Ссылка недействительна или устарела»', async () => {
    const app = renderApp({
      path: '/reset-password#token=first-token',
      routes: { 'POST /auth/password-resets/complete': () => apiError(400, 'invalid_link') },
    });

    await heading('Новый пароль');
    type('Новый пароль', 'new-correct-horse-2');
    press('Сохранить пароль');

    await alertWith('Ссылка недействительна или устарела');
    expect(callsTo(app, 'POST', '/auth/password-resets/complete')[0]?.body).toEqual({
      token: 'first-token',
      password: 'new-correct-horse-2',
    });
  });

  it('FR-8 «Expired or used reset link»: shows «Ссылка недействительна или устарела» for the fragment token', async () => {
    const app = renderApp({
      path: '/reset-password#token=old-token',
      routes: { 'POST /auth/password-resets/complete': () => apiError(400, 'invalid_link') },
    });

    await heading('Новый пароль');
    type('Новый пароль', 'new-correct-horse-2');
    press('Сохранить пароль');

    await alertWith('Ссылка недействительна или устарела');
    const body = callsTo(app, 'POST', '/auth/password-resets/complete')[0]?.body as
      { token?: unknown } | undefined;
    expect(body?.token).toBe('old-token');
  });

  it('FR-8 «Too short new password»: the message is next to the field and the same link still works', async () => {
    const app = renderApp({
      path: '/reset-password#token=reset-token-1',
      routes: {
        'POST /auth/password-resets/complete': (body) =>
          (body as { password?: unknown }).password === 'short'
            ? apiError(422, 'validation_failed', {
                password: 'Пароль должен быть от 10 до 128 символов',
              })
            : noContent(),
      },
    });

    await heading('Новый пароль');
    type('Новый пароль', 'short');
    press('Сохранить пароль');

    await screen.findByText('Пароль должен быть от 10 до 128 символов');
    expect(fieldOf('Новый пароль')).toHaveTextContent('Пароль должен быть от 10 до 128 символов');

    type('Новый пароль', 'new-correct-horse-2');
    press('Сохранить пароль');

    await waitFor(() => {
      expect(callsTo(app, 'POST', '/auth/password-resets/complete')).toHaveLength(2);
    });
    const posts = callsTo(app, 'POST', '/auth/password-resets/complete');
    expect(posts[0]?.body).toEqual({ token: 'reset-token-1', password: 'short' });
    expect(posts[1]?.body).toEqual({ token: 'reset-token-1', password: 'new-correct-horse-2' });
  });
});
