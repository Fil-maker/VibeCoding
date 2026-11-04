import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  alertWith,
  callsTo,
  fieldOf,
  json,
  press,
  rowOf,
  type,
  type Handler,
} from './test/appHarness';
import {
  type MailboxJson,
  mailbox,
  REFUSED,
  connectRoutes,
  openForm,
  field,
  pickService,
  serverSettings,
} from './test/mailboxForm';

process.env.TZ = 'UTC';

describe('connect form: connecting (FR-22)', () => {
  it('FR-22 «Successful connection»: anna@yandex.ru sends the filled server, 993, the login and the password', async () => {
    const boxes: MailboxJson[] = [];
    const app = await openForm({
      'GET /mailboxes': () => json(200, boxes),
      'POST /mailboxes': () => {
        const created = mailbox();
        boxes.push(created);
        return json(201, created);
      },
    });
    type('Адрес почты', 'anna@yandex.ru');
    type('Пароль приложения', 'app-pass-1234');

    press('Подключить');

    expect(await rowOf('anna@yandex.ru')).toHaveTextContent('Ожидает чтения');
    expect(callsTo(app, 'POST', '/mailboxes')[0]?.body).toEqual({
      server: 'imap.yandex.ru',
      port: 993,
      login: 'anna@yandex.ru',
      password: 'app-pass-1234',
    });
  });

  it('FR-22 «Successful connection» (hand-picked service): the request carries imap.gmail.com and the address as login', async () => {
    const app = await openForm(connectRoutes(() => json(201, mailbox())));
    type('Адрес почты', 'anna@studio-anna.ru');
    pickService('Gmail');
    type('Пароль приложения', 'app-pass-1234');

    press('Подключить');

    await waitFor(() => {
      expect(callsTo(app, 'POST', '/mailboxes')).toHaveLength(1);
    });
    expect(callsTo(app, 'POST', '/mailboxes')[0]?.body).toEqual({
      server: 'imap.gmail.com',
      port: 993,
      login: 'anna@studio-anna.ru',
      password: 'app-pass-1234',
    });
  });

  it('FR-22 «Wrong password»: the refusal shows, the steps and the link stay, the address and the server stay filled', async () => {
    const app = await openForm(
      connectRoutes(() =>
        json(422, { error: { code: 'mailbox_sign_in_failed', message: REFUSED } }),
      ),
    );
    type('Адрес почты', 'anna@yandex.ru');
    type('Пароль приложения', 'wrong-pass-1');

    press('Подключить');

    await alertWith(REFUSED);
    expect(callsTo(app, 'POST', '/mailboxes')).toHaveLength(1);
    expect(screen.getByText('Ящики ещё не подключены')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Как подключить Яндекс Почту' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Справка Яндекс Почты' })).toBeInTheDocument();
    expect(field('Адрес почты')).toHaveDisplayValue('anna@yandex.ru');
    expect(field('Сервер IMAP')).toHaveDisplayValue('imap.yandex.ru');
  });

  it('FR-22 «Unreachable server»: nothing is saved and the form shows «Не удалось подключиться к серверу imap.nowhere.test»', async () => {
    const message = 'Не удалось подключиться к серверу imap.nowhere.test';
    const app = await openForm(
      connectRoutes(() => json(422, { error: { code: 'mailbox_unreachable', message } })),
    );
    type('Адрес почты', 'anna@studio-anna.ru');
    type('Сервер IMAP', 'imap.nowhere.test');
    type('Пароль приложения', 'app-pass-1234');

    press('Подключить');

    await alertWith(message);
    expect(callsTo(app, 'POST', '/mailboxes')).toHaveLength(1);
    expect(callsTo(app, 'POST', '/mailboxes')[0]?.body).toMatchObject({
      server: 'imap.nowhere.test',
    });
    expect(screen.getByText('Ящики ещё не подключены')).toBeInTheDocument();
  });

  it('FR-22 «The same mailbox twice»: with the mailbox already listed, nothing is saved and the form shows «Этот ящик уже подключён»', async () => {
    const app = await openForm({
      'GET /mailboxes': () => json(200, [mailbox()]),
      'POST /mailboxes': () =>
        json(409, { error: { code: 'mailbox_exists', message: 'Этот ящик уже подключён' } }),
    });
    type('Адрес почты', 'anna@yandex.ru');
    type('Пароль приложения', 'app-pass-1234');

    press('Подключить');

    await alertWith('Этот ящик уже подключён');
    expect(callsTo(app, 'POST', '/mailboxes')[0]?.body).toMatchObject({
      server: 'imap.yandex.ru',
      login: 'anna@yandex.ru',
    });
    expect(screen.getAllByText('anna@yandex.ru')).toHaveLength(1);
    expect(
      screen.getAllByRole('row').filter((row) => row.textContent.includes('anna@yandex.ru')),
    ).toHaveLength(1);
  });

  // The answer of the app to a body with an empty field, by the messages the spec gives.
  function validating(): Record<string, Handler> {
    return connectRoutes((body) => {
      const sent = body as { server: string; port: number; login: string; password: string };
      const fields: Record<string, string> = {};
      if (sent.login === '') fields.login = 'Укажите адрес почты';
      if (sent.server === '') fields.server = 'Укажите сервер IMAP';
      if (sent.password === '') fields.password = 'Укажите пароль приложения';
      if (sent.port < 1 || sent.port > 65535) fields.port = 'Порт должен быть от 1 до 65535';
      return json(422, {
        error: { code: 'validation_failed', message: 'Проверьте поля формы', fields },
      });
    });
  }

  const EMPTY_ADDRESS = 'Укажите адрес почты';
  const EMPTY_SERVER = 'Укажите сервер IMAP';
  const EMPTY_PASSWORD = 'Укажите пароль приложения';
  const BAD_PORT = 'Порт должен быть от 1 до 65535';

  it('FR-22 «Empty fields»: an empty address is named on «Адрес почты» only and nothing is saved', async () => {
    await openForm(validating());
    type('Сервер IMAP', 'imap.studio-anna.ru');
    type('Пароль приложения', 'app-pass-1234');

    press('Подключить');

    expect(await screen.findByText(EMPTY_ADDRESS)).toBeInTheDocument();
    expect(fieldOf('Адрес почты')).toHaveTextContent(EMPTY_ADDRESS);
    expect(screen.queryByText(EMPTY_SERVER)).not.toBeInTheDocument();
    expect(screen.queryByText(EMPTY_PASSWORD)).not.toBeInTheDocument();
    expect(screen.getByText('Ящики ещё не подключены')).toBeInTheDocument();
  });

  it('FR-22 «Empty fields»: an empty server of «Другой» is named on «Сервер IMAP» with the settings open', async () => {
    const app = await openForm(validating());
    type('Адрес почты', 'anna@studio-anna.ru');
    type('Пароль приложения', 'app-pass-1234');

    press('Подключить');

    expect(await screen.findByText(EMPTY_SERVER)).toBeInTheDocument();
    expect(fieldOf('Сервер IMAP')).toHaveTextContent(EMPTY_SERVER);
    expect(callsTo(app, 'POST', '/mailboxes')[0]?.body).toMatchObject({ server: '' });
    expect(serverSettings().open).toBe(true);
  });

  it('FR-22 «Empty fields»: an emptied server under a known address opens the closed settings', async () => {
    await openForm(validating());
    type('Адрес почты', 'anna@yandex.ru');
    type('Пароль приложения', 'app-pass-1234');
    type('Сервер IMAP', '');
    expect(serverSettings().open).toBe(false);

    press('Подключить');

    expect(await screen.findByText(EMPTY_SERVER)).toBeInTheDocument();
    expect(fieldOf('Сервер IMAP')).toHaveTextContent(EMPTY_SERVER);
    expect(serverSettings().open).toBe(true);
  });

  it('FR-22 «Empty fields»: the port 0 is sent, named on «Порт» and opens the closed settings', async () => {
    const app = await openForm(validating());
    type('Адрес почты', 'anna@yandex.ru');
    type('Пароль приложения', 'app-pass-1234');
    type('Порт', '0');
    expect(serverSettings().open).toBe(false);

    press('Подключить');

    expect(await screen.findByText(BAD_PORT)).toBeInTheDocument();
    expect(fieldOf('Порт')).toHaveTextContent(BAD_PORT);
    expect(callsTo(app, 'POST', '/mailboxes')[0]?.body).toMatchObject({ port: 0 });
    expect(serverSettings().open).toBe(true);
    expect(screen.queryByText(EMPTY_SERVER)).not.toBeInTheDocument();
  });

  it('FR-22 «Empty fields»: an empty app password is named on «Пароль приложения»', async () => {
    const app = await openForm(validating());
    type('Адрес почты', 'anna@yandex.ru');

    press('Подключить');

    expect(await screen.findByText(EMPTY_PASSWORD)).toBeInTheDocument();
    expect(fieldOf('Пароль приложения')).toHaveTextContent(EMPTY_PASSWORD);
    expect(callsTo(app, 'POST', '/mailboxes')[0]?.body).toMatchObject({ password: '' });
    expect(screen.queryByText(EMPTY_ADDRESS)).not.toBeInTheDocument();
    expect(screen.getByText('Ящики ещё не подключены')).toBeInTheDocument();
  });
});
