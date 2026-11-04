import { fireEvent, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ANNA, json, renderApp, rowOf } from './test/appHarness';
import { type MailboxJson, mailbox, HOW_TO, howToBlock, stepsOf } from './test/mailboxForm';

process.env.TZ = 'UTC';

describe('mailbox list: «Как исправить» (FR-26)', () => {
  const REVOKED = 'не удалось войти в ящик, подключите его заново с новым паролем приложения';

  function openList(box: MailboxJson): void {
    renderApp({
      path: '/mailboxes',
      me: ANNA,
      routes: { 'GET /mailboxes': () => json(200, [box]) },
    });
  }

  it('FR-26 «The steps for a refused sign-in»: «Как исправить» opens the steps and the link of Яндекс Почта', async () => {
    openList(mailbox({ status: 'failed', error: REVOKED, error_code: 'sign_in_failed' }));
    const row = await rowOf('anna@yandex.ru');
    expect(screen.queryByRole('region', { name: HOW_TO })).not.toBeInTheDocument();

    fireEvent.click(within(row).getByRole('button', { name: 'Как исправить' }));

    const block = await howToBlock('Как подключить Яндекс Почту');
    expect(stepsOf(block)).toEqual([
      'Включите доступ по IMAP: Настройки → Почтовые программы → «С сервера imap.yandex.ru по протоколу IMAP» и «Пароли приложений и OAuth-токены».',
      'Создайте пароль приложения для почты: Яндекс ID → Безопасность → Пароли приложений. Он начнёт действовать через 2–3 часа.',
    ]);
    expect(within(block).getByRole('link', { name: 'Справка Яндекс Почты' })).toBeInTheDocument();
  });

  it('FR-26 «No steps for the demo mailbox»: the error shows without «Как исправить»', async () => {
    openList(
      mailbox({
        login: 'anna@demo.test',
        server: 'greenmail',
        port: 3143,
        status: 'failed',
        error: REVOKED,
        error_code: 'sign_in_failed',
      }),
    );

    const row = await rowOf('anna@demo.test');

    expect(row).toHaveTextContent(`Ошибка: ${REVOKED}`);
    expect(within(row).queryByRole('button', { name: 'Как исправить' })).not.toBeInTheDocument();
  });

  it('FR-26 «No steps for an unknown server»: the error shows without «Как исправить»', async () => {
    openList(
      mailbox({
        login: 'anna@studio-anna.ru',
        server: 'imap.studio-anna.ru',
        status: 'failed',
        error: REVOKED,
        error_code: 'sign_in_failed',
      }),
    );

    const row = await rowOf('anna@studio-anna.ru');

    expect(row).toHaveTextContent(`Ошибка: ${REVOKED}`);
    expect(within(row).queryByRole('button', { name: 'Как исправить' })).not.toBeInTheDocument();
  });

  it('FR-26 «The server is down for a while»: «Ошибка: сервер не отвечает» has no «Как исправить»', async () => {
    openList(mailbox({ status: 'failed', error: 'сервер не отвечает', error_code: 'unreachable' }));

    const row = await rowOf('anna@yandex.ru');

    expect(row).toHaveTextContent('Ошибка: сервер не отвечает');
    expect(within(row).queryByRole('button', { name: 'Как исправить' })).not.toBeInTheDocument();
  });

  it('FR-26: a mailbox that is not failed has no «Как исправить»', async () => {
    openList(mailbox({ status: 'read', last_read_at: '2026-10-29T14:05:00Z' }));

    const row = await rowOf('anna@yandex.ru');

    expect(within(row).queryByRole('button', { name: 'Как исправить' })).not.toBeInTheDocument();
  });
});
