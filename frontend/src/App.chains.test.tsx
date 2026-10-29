import { fireEvent, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import {
  ANNA,
  apiError,
  json,
  press,
  renderApp,
  rowOf,
  signedIn,
  type,
  type Handler,
} from './test/appHarness';

// Dates are shown in the machine's time zone; the tests pin it to UTC so «14:05» means 14:05 everywhere.
process.env.TZ = 'UTC';

interface AddressJson {
  address: string;
  name: string | null;
}

interface SummaryJson {
  id: string;
  subject: string;
  participants: AddressJson[];
  email_count: number;
  latest_email_at: string;
}

interface EmailJson {
  id: string;
  sender: AddressJson;
  to: AddressJson[];
  cc: AddressJson[];
  sent_at: string;
  subject: string;
  text: string;
  attachment_names: string[];
}

function address(addr: string, name: string | null = null): AddressJson {
  return { address: addr, name };
}

function summary(overrides: Partial<SummaryJson> = {}): SummaryJson {
  return {
    id: 'bbbbbbbb-0000-4000-8000-000000000001',
    subject: 'Договор поставки',
    participants: [address('oleg@stroy.test')],
    email_count: 4,
    latest_email_at: '2026-10-28T12:00:00Z',
    ...overrides,
  };
}

function email(overrides: Partial<EmailJson> = {}): EmailJson {
  return {
    id: 'cccccccc-0000-4000-8000-000000000001',
    sender: address('oleg@stroy.test'),
    to: [address('anna@yandex.ru')],
    cc: [],
    sent_at: '2026-10-20T09:00:00Z',
    subject: 'Договор поставки',
    text: 'Текст письма',
    attachment_names: [],
    ...overrides,
  };
}

// The URLs the stubbed fetch received for one method and path, with their query strings.
function requestUrls(method: string, path: string): URL[] {
  return vi
    .mocked(fetch)
    .mock.calls.map(([request]) => request as Request)
    .filter((request) => request.method === method)
    .map((request) => new URL(request.url))
    .filter((url) => url.pathname === `/api/v1${path}`);
}

const CHAIN_ID = 'bbbbbbbb-0000-4000-8000-000000000001';
const CONTRACT = summary({ id: CHAIN_ID });
const ESTIMATE = summary({
  id: 'bbbbbbbb-0000-4000-8000-000000000002',
  subject: 'Смета',
  participants: [address('ira@design.test')],
  email_count: 2,
  latest_email_at: '2026-10-20T12:00:00Z',
});

function page(items: SummaryJson[], nextCursor: string | null = null): Response {
  return json(200, { items, next_cursor: nextCursor });
}

function chainAnswer(emails: EmailJson[]): Handler {
  return () =>
    json(200, {
      id: CHAIN_ID,
      subject: 'Договор поставки',
      participants: [address('oleg@stroy.test')],
      emails,
    });
}

function follows(a: HTMLElement, b: HTMLElement): boolean {
  return (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}

// The smallest ancestor of the element that holds a «Кому» label; it must hold exactly one, so it is one email.
function emailBlockOf(node: HTMLElement): HTMLElement {
  let current: HTMLElement | null = node;
  while (current) {
    const labels = current.textContent.split('Кому').length - 1;
    if (labels === 1) return current;
    if (labels > 1) throw new Error('The block holds more than one email');
    current = current.parentElement;
  }
  throw new Error('The element is in no email block');
}

describe('start page links', () => {
  it('SPA pages «Start page»: the start page links «Почтовые ящики» to /mailboxes and «Переписка» to /chains', async () => {
    renderApp({ path: '/', me: ANNA });

    await screen.findByText('Анна Петрова');
    expect(screen.getByRole('link', { name: 'Почтовые ящики' })).toHaveAttribute(
      'href',
      '/mailboxes',
    );
    expect(screen.getByRole('link', { name: 'Переписка' })).toHaveAttribute('href', '/chains');
    expect(screen.getByRole('button', { name: 'Выйти' })).toBeInTheDocument();
  });
});

describe('guards of the new pages', () => {
  it('FR-17 «A signed-out visitor opens a protected page»: after signing in the visitor lands on /chains', async () => {
    renderApp({
      path: '/chains',
      routes: {
        'POST /auth/sessions': (_body, session) => signedIn(session, ANNA),
        'GET /reply-chains': () => page([CONTRACT]),
      },
    });

    expect(await screen.findByRole('heading', { level: 1, name: 'Вход' })).toBeInTheDocument();
    type('Email', ANNA.email);
    type('Пароль', 'correct-horse-1');
    press('Войти');

    expect(await rowOf('Договор поставки')).toBeInTheDocument();
    expect(window.location.pathname).toBe('/chains');
  });

  it.each(['/mailboxes', '/chains', `/chains/${CHAIN_ID}`])(
    'FR-17 «A signed-out visitor opens a protected page»: %s shows «Вход» to a visitor',
    async (path) => {
      renderApp({ path });

      expect(await screen.findByRole('heading', { level: 1, name: 'Вход' })).toBeInTheDocument();
    },
  );
});

describe('chains list', () => {
  it('FR-30 «The list of chains»: rows show subject, participants, count and date in the given order', async () => {
    renderApp({
      path: '/chains',
      me: ANNA,
      routes: { 'GET /reply-chains': () => page([CONTRACT, ESTIMATE]) },
    });

    const first = await rowOf('Договор поставки');
    expect(first).toHaveTextContent('oleg@stroy.test');
    expect(first).toHaveTextContent('4 письма');
    expect(first).toHaveTextContent('28.10.2026');
    const second = await rowOf('Смета');
    expect(second).toHaveTextContent('ira@design.test');
    expect(second).toHaveTextContent('2 письма');
    expect(second).toHaveTextContent('20.10.2026');
    expect(follows(first, second)).toBe(true);
  });

  it('FR-30 «The list of chains»: the subject links to the chain page', async () => {
    renderApp({
      path: '/chains',
      me: ANNA,
      routes: { 'GET /reply-chains': () => page([CONTRACT]) },
    });

    const row = await rowOf('Договор поставки');
    expect(within(row).getByRole('link', { name: 'Договор поставки' })).toHaveAttribute(
      'href',
      `/chains/${CHAIN_ID}`,
    );
  });

  it.each([
    [1, '1 письмо'],
    [2, '2 письма'],
    [5, '5 писем'],
    [21, '21 письмо'],
  ])('FR-30 «The list of chains»: %i emails read «%s»', async (emailCount, expected) => {
    renderApp({
      path: '/chains',
      me: ANNA,
      routes: {
        'GET /reply-chains': () =>
          page([summary({ id: CHAIN_ID, subject: 'Счёт', email_count: emailCount })]),
      },
    });

    const row = await rowOf('Счёт');
    expect(row.textContent).toMatch(new RegExp(`(?<![0-9])${expected}(?![а-я])`));
  });

  it('FR-30 «The list of chains»: «Показать ещё» loads the next page with the cursor and then disappears', async () => {
    let served = 0;
    renderApp({
      path: '/chains',
      me: ANNA,
      routes: {
        'GET /reply-chains': () => {
          served += 1;
          return served === 1 ? page([CONTRACT], 'cursor-2') : page([ESTIMATE]);
        },
      },
    });

    await rowOf('Договор поставки');
    expect(screen.queryByText('Смета')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Показать ещё' }));

    await rowOf('Смета');
    expect(screen.getByText('Договор поставки')).toBeInTheDocument();
    const urls = requestUrls('GET', '/reply-chains');
    expect(urls).toHaveLength(2);
    expect(urls[0]?.searchParams.get('cursor')).toBeNull();
    expect(urls[1]?.searchParams.get('cursor')).toBe('cursor-2');
    expect(screen.queryByRole('button', { name: 'Показать ещё' })).not.toBeInTheDocument();
  });

  it('FR-30 «The list of chains»: without a next page there is no «Показать ещё»', async () => {
    renderApp({
      path: '/chains',
      me: ANNA,
      routes: { 'GET /reply-chains': () => page([CONTRACT]) },
    });

    await rowOf('Договор поставки');
    expect(screen.queryByRole('button', { name: 'Показать ещё' })).not.toBeInTheDocument();
  });

  it('FR-30 «No emails yet»: an empty list shows «Писем пока нет: подключите почтовый ящик»', async () => {
    renderApp({ path: '/chains', me: ANNA, routes: { 'GET /reply-chains': () => page([]) } });

    expect(await screen.findByText('Писем пока нет: подключите почтовый ящик')).toBeInTheDocument();
  });
});

describe('chain page', () => {
  const EMAILS = [
    email({
      id: 'cccccccc-0000-4000-8000-000000000001',
      sender: address('oleg@stroy.test'),
      to: [address('anna@yandex.ru')],
      cc: [address('boss@stroy.test')],
      sent_at: '2026-10-20T09:30:00Z',
      subject: 'Договор поставки',
      text: 'Первое письмо цепочки',
      attachment_names: ['договор.pdf'],
    }),
    email({
      id: 'cccccccc-0000-4000-8000-000000000002',
      sender: address('anna@yandex.ru'),
      to: [address('oleg@stroy.test')],
      cc: [address('buh@yandex.ru')],
      sent_at: '2026-10-21T15:45:00Z',
      subject: 'Согласование цены',
      text: 'Второе письмо цепочки',
    }),
    email({
      id: 'cccccccc-0000-4000-8000-000000000003',
      sender: address('oleg@stroy.test'),
      to: [address('anna@yandex.ru')],
      cc: [address('lawyer@stroy.test')],
      sent_at: '2026-10-22T11:10:00Z',
      subject: 'Правки к договору',
      text: 'Третье письмо цепочки',
    }),
    email({
      id: 'cccccccc-0000-4000-8000-000000000004',
      sender: address('anna@yandex.ru'),
      to: [address('oleg@stroy.test')],
      cc: [address('ceo@yandex.ru')],
      sent_at: '2026-10-28T18:05:00Z',
      subject: 'Подписание договора',
      text: 'Четвёртое письмо цепочки',
    }),
  ];
  const EXPECTED = [
    {
      subject: 'Договор поставки',
      text: 'Первое письмо цепочки',
      from: 'oleg@stroy.test',
      to: 'anna@yandex.ru',
      cc: 'boss@stroy.test',
      date: /20\.10\.2026.*09:30/,
    },
    {
      subject: 'Согласование цены',
      text: 'Второе письмо цепочки',
      from: 'anna@yandex.ru',
      to: 'oleg@stroy.test',
      cc: 'buh@yandex.ru',
      date: /21\.10\.2026.*15:45/,
    },
    {
      subject: 'Правки к договору',
      text: 'Третье письмо цепочки',
      from: 'oleg@stroy.test',
      to: 'anna@yandex.ru',
      cc: 'lawyer@stroy.test',
      date: /22\.10\.2026.*11:10/,
    },
    {
      subject: 'Подписание договора',
      text: 'Четвёртое письмо цепочки',
      from: 'anna@yandex.ru',
      to: 'oleg@stroy.test',
      cc: 'ceo@yandex.ru',
      date: /28\.10\.2026.*18:05/,
    },
  ];

  function openChain(emails: EmailJson[]): void {
    renderApp({
      path: `/chains/${CHAIN_ID}`,
      me: ANNA,
      routes: { [`GET /reply-chains/${CHAIN_ID}`]: chainAnswer(emails) },
    });
  }

  // The smallest ancestor of the text that holds a «Кому» label; it must hold exactly one.
  function blockOfText(text: string): HTMLElement {
    return emailBlockOf(screen.getByText(text));
  }

  it('FR-31 «Reading a chain»: shows the 4 emails oldest first, each with subject, sender, recipients, copy, date and time', async () => {
    openChain(EMAILS);

    await screen.findByText('Первое письмо цепочки');
    expect(screen.getAllByText(/Кому/)).toHaveLength(4);
    expect(screen.getAllByText('Договор поставки').length).toBeGreaterThan(0);
    for (const expected of EXPECTED) {
      const block = blockOfText(expected.text);
      expect(block).toHaveTextContent('Тема');
      expect(block).toHaveTextContent(expected.subject);
      expect(block).toHaveTextContent('От');
      expect(block).toHaveTextContent(expected.from);
      expect(block).toHaveTextContent('Кому');
      expect(block).toHaveTextContent(expected.to);
      expect(block).toHaveTextContent('Копия');
      expect(block).toHaveTextContent(expected.cc);
      expect(block.textContent).toMatch(expected.date);
    }
  });

  it('FR-31 «Reading a chain»: the 4 emails stay in the order of the answer, oldest first', async () => {
    openChain(EMAILS);

    await screen.findByText('Первое письмо цепочки');
    const nodes = EXPECTED.map((expected) => screen.getByText(expected.text));
    nodes.slice(1).forEach((node, index) => {
      const previous = nodes[index];
      expect(previous && follows(previous, node)).toBe(true);
    });
  });

  it('FR-31 «Reading a chain»: «Вложения: договор.pdf» is on the email that carried it only', async () => {
    openChain(EMAILS);

    await screen.findByText('Первое письмо цепочки');
    expect(blockOfText('Первое письмо цепочки')).toHaveTextContent('Вложения: договор.pdf');
    for (const expected of EXPECTED.slice(1)) {
      expect(blockOfText(expected.text)).not.toHaveTextContent('Вложения');
    }
  });

  it('FR-31 «Reading a chain»: several attachment names are all listed after «Вложения:»', async () => {
    openChain([email({ text: 'С вложениями', attachment_names: ['договор.pdf', 'смета.xlsx'] })]);

    const block = emailBlockOf(await screen.findByText('С вложениями'));
    expect(block).toHaveTextContent('Вложения:');
    expect(block).toHaveTextContent('договор.pdf');
    expect(block).toHaveTextContent('смета.xlsx');
  });

  it('SPA pages «Chain»: markup characters in the text are shown as text, never as elements', async () => {
    openChain([email({ text: '<b>Срок</b> — пятница<script>alert(1)</script>' })]);

    const text = await screen.findByText(/Срок/);
    expect(text).toHaveTextContent('<b>Срок</b> — пятница<script>alert(1)</script>');
    expect(document.body.querySelector('b, script')).toBeNull();
  });

  it('SPA pages «Chain»: line breaks of the text are kept', async () => {
    openChain([email({ text: ['первая строка', 'вторая строка'].join('\n') })]);

    const text = await screen.findByText(/первая строка/);
    const keepsNewline = text.textContent.includes('\n');
    const hasBreak = text.querySelector('br') !== null;
    expect(keepsNewline || hasBreak).toBe(true);
    expect(text).toHaveTextContent('первая строка');
    expect(text).toHaveTextContent('вторая строка');
  });

  it("FR-31 «Another user's chain»: a chain the API answers «not found» shows «Страница не найдена»", async () => {
    renderApp({
      path: `/chains/${CHAIN_ID}`,
      me: ANNA,
      routes: { [`GET /reply-chains/${CHAIN_ID}`]: () => apiError(404, 'not_found') },
    });

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Страница не найдена' }),
    ).toBeInTheDocument();
  });
});
