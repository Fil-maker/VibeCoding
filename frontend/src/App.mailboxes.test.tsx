import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  ANNA,
  alertWith,
  callsTo,
  fieldOf,
  json,
  navigate,
  noContent,
  press,
  renderApp,
  rowOf,
  type,
  type Handler,
  type Me,
} from './test/appHarness';

// Dates are shown in the machine's time zone; the tests pin it to UTC so «14:05» means 14:05 everywhere.
process.env.TZ = 'UTC';

interface MailboxJson {
  id: string;
  server: string;
  port: number;
  login: string;
  status: 'pending' | 'reading' | 'read' | 'failed';
  error: string | null;
  last_read_at: string | null;
}

function mailbox(overrides: Partial<MailboxJson> = {}): MailboxJson {
  return {
    id: 'aaaaaaaa-0000-4000-8000-000000000001',
    server: 'imap.yandex.ru',
    port: 993,
    login: 'anna@yandex.ru',
    status: 'pending',
    error: null,
    last_read_at: null,
    ...overrides,
  };
}

const ANNA_BOX = mailbox();
const VERA: Me = {
  user_id: '22222222-2222-4222-8222-222222222222',
  name: 'Вера Орлова',
  email: 'vera@romashka.test',
};
const SECOND_BOX_ID = 'aaaaaaaa-0000-4000-8000-000000000002';
const CONFIRMATION = 'Отключить ящик anna@yandex.ru? Прочитанные письма останутся.';

function errorAnswer(
  status: number,
  code: string,
  message: string,
  fields?: Record<string, string>,
): Response {
  return json(status, { error: { code, message, ...(fields ? { fields } : {}) } });
}

function openMailboxes(boxes: MailboxJson[]): ReturnType<typeof renderApp> {
  return renderApp({
    path: '/mailboxes',
    me: ANNA,
    routes: { 'GET /mailboxes': () => json(200, boxes) },
  });
}

function fillForm(values: { server: string; login: string; password: string }): void {
  type('Сервер IMAP', values.server);
  type('Логин', values.login);
  type('Пароль приложения', values.password);
}

// The nearest ancestor of the text that also holds the «Отмена» button: the confirmation.
async function confirmationWith(text: string): Promise<HTMLElement> {
  let node: HTMLElement | null = await screen.findByText(text);
  while (node) {
    if (within(node).queryByRole('button', { name: 'Отмена' })) return node;
    node = node.parentElement;
  }
  throw new Error(`No confirmation holds «${text}»`);
}

describe('mailboxes page: list', () => {
  it('FR-23 «The password is never shown»: the list shows the login, the server and the status', async () => {
    openMailboxes([ANNA_BOX]);

    const row = await rowOf('anna@yandex.ru');
    expect(row).toHaveTextContent('imap.yandex.ru');
    expect(row).toHaveTextContent('Ожидает чтения');
  });

  it("FR-23 «Another user's mailboxes»: Вера, who has none, sees «Ящики ещё не подключены»", async () => {
    renderApp({ path: '/mailboxes', me: VERA, routes: { 'GET /mailboxes': () => json(200, []) } });

    expect(await screen.findByText('Ящики ещё не подключены')).toBeInTheDocument();
    expect(screen.queryByText('anna@yandex.ru')).not.toBeInTheDocument();
  });

  it('FR-24 «While a read runs the mailbox SHALL show Читается» (SPA pages): a reading mailbox shows «Читается…»', async () => {
    openMailboxes([mailbox({ status: 'reading' })]);

    expect(await rowOf('anna@yandex.ru')).toHaveTextContent('Читается…');
  });

  it('FR-24 «First read after connecting»: a read mailbox shows «Прочитан» with the date and time', async () => {
    openMailboxes([mailbox({ status: 'read', last_read_at: '2026-10-29T14:05:00Z' })]);

    expect(await rowOf('anna@yandex.ru')).toHaveTextContent('Прочитан 29.10.2026, 14:05');
  });

  it('FR-26 «The app password was revoked»: the mailbox shows «Ошибка: <reason>»', async () => {
    const reason = 'не удалось войти в ящик, подключите его заново с новым паролем приложения';
    openMailboxes([mailbox({ status: 'failed', error: reason })]);

    expect(await rowOf('anna@yandex.ru')).toHaveTextContent(`Ошибка: ${reason}`);
  });

  it('FR-26 «The server is down for a while»: «Ошибка: сервер не отвечает», then «Прочитан» after the next read', async () => {
    let served = 0;
    renderApp({
      path: '/mailboxes',
      me: ANNA,
      routes: {
        'GET /mailboxes': () => {
          served += 1;
          return json(200, [
            served === 1
              ? mailbox({ status: 'failed', error: 'сервер не отвечает' })
              : mailbox({ status: 'read', last_read_at: '2026-10-29T14:10:00Z' }),
          ]);
        },
      },
    });

    expect(await rowOf('anna@yandex.ru')).toHaveTextContent('Ошибка: сервер не отвечает');
    navigate('/');
    await screen.findByText('Анна Петрова');
    navigate('/mailboxes');

    await waitFor(() => {
      expect(screen.getByText('anna@yandex.ru').closest('tr, li')).toHaveTextContent(
        'Прочитан 29.10.2026, 14:10',
      );
    });
    expect(screen.queryByText(/Ошибка/)).not.toBeInTheDocument();
  });
});

describe('mailboxes page: refresh', () => {
  it('FR-24 «A new email after Обновить»: «Обновить» calls refresh for that mailbox only', async () => {
    const second = mailbox({ id: SECOND_BOX_ID, login: 'anna@mail.ru', server: 'imap.mail.ru' });
    const app = renderApp({
      path: '/mailboxes',
      me: ANNA,
      routes: {
        'GET /mailboxes': () => json(200, [ANNA_BOX, second]),
        [`POST /mailboxes/${SECOND_BOX_ID}/refresh`]: () => json(202, second),
      },
    });

    const row = await rowOf('anna@mail.ru');
    fireEvent.click(within(row).getByRole('button', { name: 'Обновить' }));

    await waitFor(() => {
      expect(callsTo(app, 'POST', `/mailboxes/${SECOND_BOX_ID}/refresh`)).toHaveLength(1);
    });
    expect(callsTo(app, 'POST', `/mailboxes/${ANNA_BOX.id}/refresh`)).toHaveLength(0);
  });
});

describe('mailboxes page: disconnect', () => {
  function disconnectRoutes(boxes: MailboxJson[]): Record<string, Handler> {
    return {
      'GET /mailboxes': () => json(200, boxes),
      [`POST /mailboxes/${ANNA_BOX.id}/refresh`]: () => json(202, ANNA_BOX),
      [`DELETE /mailboxes/${ANNA_BOX.id}`]: () => {
        boxes.splice(0, boxes.length);
        return noContent();
      },
    };
  }

  async function askToDisconnect(): Promise<HTMLElement> {
    const row = await rowOf('anna@yandex.ru');
    fireEvent.click(within(row).getByRole('button', { name: 'Отключить' }));
    return confirmationWith(CONFIRMATION);
  }

  // Calls are recorded in order, so once a later request is recorded, an earlier DELETE would be too.
  async function settle(app: ReturnType<typeof renderApp>): Promise<void> {
    const row = await rowOf('anna@yandex.ru');
    fireEvent.click(within(row).getByRole('button', { name: 'Обновить' }));
    await waitFor(() => {
      expect(callsTo(app, 'POST', `/mailboxes/${ANNA_BOX.id}/refresh`)).toHaveLength(1);
    });
  }

  it('FR-27 «Disconnecting keeps the emails»: «Отключить» asks for the confirmation and sends nothing yet', async () => {
    const app = renderApp({ path: '/mailboxes', me: ANNA, routes: disconnectRoutes([ANNA_BOX]) });

    await askToDisconnect();
    fireEvent.click(screen.getByRole('button', { name: 'Отмена' }));
    await settle(app);

    expect(callsTo(app, 'DELETE', `/mailboxes/${ANNA_BOX.id}`)).toHaveLength(0);
  });

  it('FR-27 «Disconnecting keeps the emails»: confirming calls DELETE and the mailbox disappears', async () => {
    const app = renderApp({ path: '/mailboxes', me: ANNA, routes: disconnectRoutes([ANNA_BOX]) });

    const confirmation = await askToDisconnect();
    fireEvent.click(within(confirmation).getByRole('button', { name: 'Отключить' }));

    expect(await screen.findByText('Ящики ещё не подключены')).toBeInTheDocument();
    expect(callsTo(app, 'DELETE', `/mailboxes/${ANNA_BOX.id}`)).toHaveLength(1);
    expect(screen.queryByText('anna@yandex.ru')).not.toBeInTheDocument();
  });

  it('FR-27 «Disconnecting keeps the emails»: «Отмена» sends no DELETE and keeps the mailbox', async () => {
    const app = renderApp({ path: '/mailboxes', me: ANNA, routes: disconnectRoutes([ANNA_BOX]) });

    const confirmation = await askToDisconnect();
    fireEvent.click(within(confirmation).getByRole('button', { name: 'Отмена' }));
    await settle(app);

    expect(screen.queryByText(CONFIRMATION)).not.toBeInTheDocument();
    expect(screen.getByText('anna@yandex.ru')).toBeInTheDocument();
    expect(callsTo(app, 'DELETE', `/mailboxes/${ANNA_BOX.id}`)).toHaveLength(0);
  });
});

describe('mailboxes page: connect form', () => {
  it('FR-22 «Successful connection»: the form «Подключить ящик» has its four fields, the port is 993', async () => {
    openMailboxes([]);

    await screen.findByText('Ящики ещё не подключены');
    expect(screen.getByText('Подключить ящик')).toBeInTheDocument();
    expect(screen.getByLabelText('Сервер IMAP')).toBeInTheDocument();
    expect(screen.getByLabelText('Порт')).toHaveDisplayValue('993');
    expect(screen.getByLabelText('Логин')).toBeInTheDocument();
    expect(screen.getByLabelText('Пароль приложения')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Подключить' })).toBeInTheDocument();
  });

  it('FR-22 «Successful connection»: the form posts the four values and the mailbox appears as «Ожидает чтения»', async () => {
    const boxes: MailboxJson[] = [];
    const app = renderApp({
      path: '/mailboxes',
      me: ANNA,
      routes: {
        'GET /mailboxes': () => json(200, boxes),
        'POST /mailboxes': () => {
          boxes.push(ANNA_BOX);
          return json(201, ANNA_BOX);
        },
      },
    });

    await screen.findByText('Ящики ещё не подключены');
    fillForm({ server: 'imap.yandex.ru', login: 'anna@yandex.ru', password: 'app-pass-1234' });
    press('Подключить');

    const row = await rowOf('anna@yandex.ru');
    expect(row).toHaveTextContent('Ожидает чтения');
    expect(callsTo(app, 'POST', '/mailboxes')).toHaveLength(1);
    expect(callsTo(app, 'POST', '/mailboxes')[0]?.body).toEqual({
      server: 'imap.yandex.ru',
      port: 993,
      login: 'anna@yandex.ru',
      password: 'app-pass-1234',
    });
  });

  async function submitRefused(
    initial: MailboxJson[],
    server: string,
    status: number,
    code: string,
    text: string,
  ): Promise<void> {
    const app = renderApp({
      path: '/mailboxes',
      me: ANNA,
      routes: {
        'GET /mailboxes': () => json(200, initial),
        'POST /mailboxes': () => errorAnswer(status, code, text),
      },
    });

    await screen.findByText(
      initial.length === 0 ? 'Ящики ещё не подключены' : (initial[0]?.login ?? ''),
    );
    fillForm({ server, login: 'anna@yandex.ru', password: 'wrong-pass-1' });
    press('Подключить');

    await alertWith(text);
    expect(callsTo(app, 'POST', '/mailboxes')).toHaveLength(1);
    if (initial.length === 0) {
      expect(screen.getByText('Ящики ещё не подключены')).toBeInTheDocument();
    } else {
      expect(screen.getAllByText('anna@yandex.ru')).toHaveLength(1);
    }
  }

  it('FR-22 «Wrong password»: nothing is saved and the form shows the sign-in refusal', async () => {
    await submitRefused(
      [],
      'imap.yandex.ru',
      422,
      'mailbox_sign_in_failed',
      'Не удалось войти в ящик: проверьте логин и пароль приложения',
    );
  });

  it('FR-22 «Unreachable server»: nothing is saved and the form shows the unreachable refusal', async () => {
    await submitRefused(
      [],
      'imap.nowhere.test',
      422,
      'mailbox_unreachable',
      'Не удалось подключиться к серверу imap.nowhere.test',
    );
  });

  it('FR-22 «The same mailbox twice»: the list already holds the mailbox, nothing is saved and the form shows «Этот ящик уже подключён»', async () => {
    await submitRefused(
      [ANNA_BOX],
      'imap.yandex.ru',
      409,
      'mailbox_exists',
      'Этот ящик уже подключён',
    );
  });

  it('FR-22 «Empty fields»: every invalid field shows its own message next to it', async () => {
    renderApp({
      path: '/mailboxes',
      me: ANNA,
      routes: {
        'GET /mailboxes': () => json(200, []),
        'POST /mailboxes': () =>
          errorAnswer(422, 'validation_failed', 'Проверьте поля формы', {
            server: 'Укажите сервер IMAP',
            port: 'Порт должен быть от 1 до 65535',
            login: 'Укажите логин',
            password: 'Укажите пароль приложения',
          }),
      },
    });

    await screen.findByText('Ящики ещё не подключены');
    type('Порт', '0');
    press('Подключить');

    await screen.findByText('Укажите сервер IMAP');
    expect(fieldOf('Сервер IMAP')).toHaveTextContent('Укажите сервер IMAP');
    expect(fieldOf('Порт')).toHaveTextContent('Порт должен быть от 1 до 65535');
    expect(fieldOf('Логин')).toHaveTextContent('Укажите логин');
    expect(fieldOf('Пароль приложения')).toHaveTextContent('Укажите пароль приложения');
    expect(screen.getByText('Ящики ещё не подключены')).toBeInTheDocument();
  });
});
