import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { callsTo, json, press, rowOf, type } from './test/appHarness';
import {
  type MailboxJson,
  mailbox,
  UNKNOWN_HINT,
  connectRoutes,
  openForm,
  field,
  pickService,
  serverSettings,
  settle,
} from './test/mailboxForm';

process.env.TZ = 'UTC';

describe('connect form: pick the service from the address (FR-53)', () => {
  it('FR-53 «A known domain»: anna@yandex.ru picks Яндекс Почта, fills the server, the port and the login', async () => {
    await openForm();

    type('Адрес почты', 'anna@yandex.ru');

    expect(field('Почтовый сервис')).toHaveDisplayValue('Яндекс Почта');
    expect(field('Сервер IMAP')).toHaveDisplayValue('imap.yandex.ru');
    expect(field('Порт')).toHaveDisplayValue('993');
    expect(field('Логин')).toHaveDisplayValue('anna@yandex.ru');
  });

  it('FR-53 «Case and spaces»: « Anna@Mail.RU » picks Mail.ru on imap.mail.ru', async () => {
    await openForm();

    type('Адрес почты', ' Anna@Mail.RU ');

    expect(field('Почтовый сервис')).toHaveDisplayValue('Mail.ru');
    expect(field('Сервер IMAP')).toHaveDisplayValue('imap.mail.ru');
  });

  it('FR-53 «An unknown domain»: «Другой», the settings open, an empty server, the port 993 and the hint', async () => {
    await openForm();

    type('Адрес почты', 'anna@studio-anna.ru');

    expect(field('Почтовый сервис')).toHaveDisplayValue('Другой');
    expect(serverSettings().open).toBe(true);
    expect(field('Сервер IMAP')).toHaveDisplayValue('');
    expect(field('Порт')).toHaveDisplayValue('993');
    expect(screen.getByText(UNKNOWN_HINT)).toBeInTheDocument();
  });

  it.each(['anna@outlook.com', 'anna@rambler.ru'])(
    'FR-53 «A service without password sign-in»: %s picks «Другой» with an empty server',
    async (address) => {
      await openForm();

      type('Адрес почты', address);

      expect(field('Почтовый сервис')).toHaveDisplayValue('Другой');
      expect(field('Сервер IMAP')).toHaveDisplayValue('');
    },
  );

  it('FR-53 «The demo mailbox»: anna@demo.test picks «Демо» on greenmail:3143', async () => {
    await openForm();

    type('Адрес почты', 'anna@demo.test');

    expect(field('Почтовый сервис')).toHaveDisplayValue('Демо');
    expect(field('Сервер IMAP')).toHaveDisplayValue('greenmail');
    expect(field('Порт')).toHaveDisplayValue('3143');
  });

  it('FR-53 «Picking the service by hand»: Gmail fills imap.gmail.com:993 and keeps the login', async () => {
    await openForm();
    type('Адрес почты', 'anna@studio-anna.ru');

    pickService('Gmail');

    expect(field('Почтовый сервис')).toHaveDisplayValue('Gmail');
    expect(field('Сервер IMAP')).toHaveDisplayValue('imap.gmail.com');
    expect(field('Порт')).toHaveDisplayValue('993');
    expect(field('Логин')).toHaveDisplayValue('anna@studio-anna.ru');
  });

  it("FR-53 «The user's own server stays»: the server stays and the login follows the corrected address", async () => {
    await openForm();
    type('Адрес почты', 'anna@yandex.ru');
    type('Сервер IMAP', 'imap.studio-anna.ru');

    type('Адрес почты', 'anna.k@yandex.ru');

    expect(field('Сервер IMAP')).toHaveDisplayValue('imap.studio-anna.ru');
    expect(field('Логин')).toHaveDisplayValue('anna.k@yandex.ru');
  });

  it('FR-53 «A login other than the address»: «anna» under «Настройки сервера» is sent and shown', async () => {
    const boxes: MailboxJson[] = [];
    const app = await openForm({
      'GET /mailboxes': () => json(200, boxes),
      'POST /mailboxes': (body) => {
        const sent = body as { server: string; port: number; login: string };
        const created = mailbox({ server: sent.server, port: sent.port, login: sent.login });
        boxes.push(created);
        return json(201, created);
      },
    });
    type('Адрес почты', 'anna@studio-anna.ru');
    type('Сервер IMAP', 'imap.studio-anna.ru');
    type('Логин', 'anna');
    type('Пароль приложения', 'app-pass-1234');

    press('Подключить');

    expect(await rowOf('anna')).toHaveTextContent('imap.studio-anna.ru');
    expect(callsTo(app, 'POST', '/mailboxes')[0]?.body).toEqual({
      server: 'imap.studio-anna.ru',
      port: 993,
      login: 'anna',
      password: 'app-pass-1234',
    });
  });

  it('FR-53 «Nothing leaves the app while typing»: no request URL or body carries the address or its domain', async () => {
    const app = await openForm();
    const fetchMock = vi.mocked(globalThis.fetch);
    const fetchBefore = fetchMock.mock.calls.length;
    const callsBefore = app.calls.length;

    type('Адрес почты', 'anna@studio-anna.ru');
    await settle();

    expect(fetchMock.mock.calls.length).toBe(fetchBefore);
    expect(app.calls).toHaveLength(callsBefore);
    const carried = [
      ...fetchMock.mock.calls.map(([request]) => (request as Request).url),
      ...app.calls.map((call) => JSON.stringify(call)),
    ].join('\n');
    expect(carried).not.toContain('anna');
    expect(carried).not.toContain('studio-anna.ru');
    expect(callsTo(app, 'POST', '/mailboxes')).toHaveLength(0);
  });

  it("FR-53 «The user's own port stays»: the port stays 143 after the address is corrected and the request carries it", async () => {
    const app = await openForm(connectRoutes(() => json(201, mailbox())));
    type('Адрес почты', 'anna@yandex.ru');
    type('Порт', '143');

    type('Адрес почты', 'anna.k@yandex.ru');

    expect(field('Порт')).toHaveDisplayValue('143');
    type('Пароль приложения', 'app-pass-1234');
    press('Подключить');
    await waitFor(() => {
      expect(callsTo(app, 'POST', '/mailboxes')).toHaveLength(1);
    });
    expect(callsTo(app, 'POST', '/mailboxes')[0]?.body).toMatchObject({ port: 143 });
  });
});
