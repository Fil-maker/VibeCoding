import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  ANNA,
  callsTo,
  heading,
  json,
  noContent,
  press,
  renderApp,
  rowOf,
  START_DATA,
} from './test/appHarness';
import {
  ENGINE_PLACEMENT,
  ESTIMATE_THREAD,
  MANUAL_PLACEMENT,
  NONE,
  OFFICE as CHAIN_OFFICE,
  openChain,
  placed,
  type PlacementJson,
} from './test/chainPlacement';
import {
  ESTIMATE,
  FILL,
  REBUILD,
  chain,
  chainRow,
  confirmationWith,
  openProject,
  thread,
  tree,
} from './test/projectTrees';
import { BY_ADDRESS, CONFIRM_DELETE, openRules, pressIn, ruleRow } from './test/rulesPage';

// Tasks 2.1 and 2.2 of 1-8-visual-system: button kinds, folding, badges, one «Создать проект», «На главную».

process.env.TZ = 'UTC';

const MAILBOX = {
  id: 'aaaaaaaa-0000-4000-8000-000000000001',
  server: 'imap.yandex.ru',
  port: 993,
  login: 'anna@yandex.ru',
  status: 'pending',
  error: null,
  last_read_at: null,
};
const DISCONNECT = 'Отключить ящик anna@yandex.ru? Прочитанные письма останутся.';

function openMailboxes(): ReturnType<typeof renderApp> {
  return renderApp({
    path: '/mailboxes',
    me: ANNA,
    routes: {
      'GET /mailboxes': () => json(200, [MAILBOX]),
      [`DELETE /mailboxes/${MAILBOX.id}`]: () => noContent(),
    },
  });
}

describe('danger confirmations', () => {
  it('«Отключить» of a mailbox: the confirming button is danger, shown only after the first press, «Отмена» keeps the mailbox', async () => {
    const app = openMailboxes();
    const row = await rowOf('anna@yandex.ru');
    expect(screen.queryByText(DISCONNECT)).not.toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Отключить' })).toHaveLength(1);

    fireEvent.click(within(row).getByRole('button', { name: 'Отключить' }));
    const confirmation = await confirmationWith(DISCONNECT);
    expect(within(confirmation).getByRole('button', { name: 'Отключить' })).toHaveAttribute(
      'data-kind',
      'danger',
    );
    fireEvent.click(within(confirmation).getByRole('button', { name: 'Отмена' }));

    await waitFor(() => {
      expect(screen.queryByText(DISCONNECT)).not.toBeInTheDocument();
    });
    expect(screen.getByText('anna@yandex.ru')).toBeInTheDocument();
    expect(callsTo(app, 'DELETE', `/mailboxes/${MAILBOX.id}`)).toHaveLength(0);
  });

  it('«Удалить» of a rule: the confirming button is danger, shown only after the first press, «Отмена» keeps the rule', async () => {
    const app = openRules({ rules: [BY_ADDRESS] });
    const row = await ruleRow('s.petrov@stroymaster.example');
    expect(screen.queryByText(CONFIRM_DELETE)).not.toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Удалить' })).toHaveLength(1);

    pressIn(row, 'Удалить');
    const confirmation = await confirmationWith(CONFIRM_DELETE);
    expect(within(confirmation).getByRole('button', { name: 'Удалить' })).toHaveAttribute(
      'data-kind',
      'danger',
    );
    pressIn(confirmation, 'Отмена');

    await waitFor(() => {
      expect(screen.queryByText(CONFIRM_DELETE)).not.toBeInTheDocument();
    });
    expect(await ruleRow('s.petrov@stroymaster.example')).toBeInTheDocument();
    expect(callsTo(app, 'DELETE', `/rules/${BY_ADDRESS.id}`)).toHaveLength(0);
  });

  it('refill of a project: «Пересобрать» is danger, shown only after the first press, «Отмена» leaves the tree', async () => {
    const app = openProject({ tree: tree() }, () => json(200, tree()));
    await chainRow('Смета на ремонт офиса');
    expect(screen.queryByText(REBUILD)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Пересобрать' })).not.toBeInTheDocument();

    press('Заполнить');
    const confirmation = await confirmationWith(REBUILD);
    expect(within(confirmation).getByRole('button', { name: 'Пересобрать' })).toHaveAttribute(
      'data-kind',
      'danger',
    );
    fireEvent.click(within(confirmation).getByRole('button', { name: 'Отмена' }));

    await waitFor(() => {
      expect(screen.queryByText(REBUILD)).not.toBeInTheDocument();
    });
    await chainRow('Смета на ремонт офиса');
    expect(callsTo(app, 'POST', FILL)).toHaveLength(0);
  });
});

describe('project tree: folding', () => {
  function summaryOf(name: string): HTMLElement {
    const summary = screen
      .getAllByText(name)
      .map((node) => node.closest<HTMLElement>('summary'))
      .find((found) => found !== null);
    if (!summary) throw new Error(`«${name}» is not in a <summary>`);
    return summary;
  }

  it('a counterparty is a <details> open at first, its <summary> folds and unfolds its chains', async () => {
    openProject({ tree: tree() });

    const estimate = await chainRow('Смета на ремонт офиса');
    const summary = summaryOf('Сергей Петров');
    const details = summary.closest('details');
    expect(details).not.toBeNull();
    expect(details?.open).toBe(true);
    expect(estimate).toBeVisible();

    fireEvent.click(summary);
    expect(details?.open).toBe(false);
    expect(estimate).not.toBeVisible();

    fireEvent.click(summary);
    expect(details?.open).toBe(true);
    expect(estimate).toBeVisible();
  });

  it('«Неразобранное» is a <details> open at first, its <summary> folds and unfolds its chains', async () => {
    openProject({ tree: tree() });

    const furniture = await chainRow('Офисная мебель');
    const summary = summaryOf('Неразобранное');
    const details = summary.closest('details');
    expect(details).not.toBeNull();
    expect(details?.open).toBe(true);
    expect(furniture).toBeVisible();

    fireEvent.click(summary);
    expect(details?.open).toBe(false);
    expect(furniture).not.toBeVisible();

    fireEvent.click(summary);
    expect(details?.open).toBe(true);
    expect(furniture).toBeVisible();
  });

  it('every counterparty is open at first and each folds and unfolds on its own', async () => {
    const other = {
      address: 'o.smirnova@interior-studio.example',
      name: 'Ольга Смирнова',
      threads: [
        {
          id: 'ffffffff-0000-4000-8000-000000000002',
          name: 'Дизайн',
          chains: [chain(4, { subject: 'Эскиз переговорной' })],
        },
      ],
    };
    const base = tree();
    openProject({ tree: { ...base, counterparties: [...base.counterparties, other] } });

    const estimate = await chainRow('Смета на ремонт офиса');
    const sketch = await chainRow('Эскиз переговорной');
    const first = summaryOf('Сергей Петров').closest('details');
    const second = summaryOf('Ольга Смирнова').closest('details');
    expect(first?.open).toBe(true);
    expect(second?.open).toBe(true);

    fireEvent.click(summaryOf('Сергей Петров'));
    expect(first?.open).toBe(false);
    expect(second?.open).toBe(true);
    expect(estimate).not.toBeVisible();
    expect(sketch).toBeVisible();

    fireEvent.click(summaryOf('Ольга Смирнова'));
    expect(second?.open).toBe(false);
    expect(sketch).not.toBeVisible();

    fireEvent.click(summaryOf('Ольга Смирнова'));
    expect(second?.open).toBe(true);
    expect(sketch).toBeVisible();
    expect(first?.open).toBe(false);
  });
});

describe('the placement reason is a badge', () => {
  const RULE_LABEL = 'Правило · адрес s.petrov@stroymaster.example';
  const ENGINE_LABEL = 'Движок text-1 · сходство 43%';
  const RULE_PLACEMENT: PlacementJson = {
    kind: 'rule',
    engine_version: null,
    similarity: null,
    rule: { condition: 'address', value: 's.petrov@stroymaster.example' },
  };

  it('in a project tree each chain shows its reason as an element with data-kind', async () => {
    const manual = chain(5, {
      subject: 'Ручная',
      placement: { kind: 'manual', engine_version: null, similarity: null },
    });
    const ruled = chain(6, { subject: 'По правилу', placement: RULE_PLACEMENT });
    const base = tree();
    const first = base.counterparties[0];
    if (!first) throw new Error('the sample tree has a counterparty');
    openProject({
      tree: {
        ...base,
        counterparties: [{ ...first, threads: [thread('Тред', [ESTIMATE, manual, ruled])] }],
      },
    });

    await chainRow('Ручная');
    expect(screen.getByText('Вручную')).toHaveAttribute('data-kind', 'manual');
    expect(screen.getByText(RULE_LABEL)).toHaveAttribute('data-kind', 'rule');
    expect(screen.getByText(ENGINE_LABEL)).toHaveAttribute('data-kind', 'engine');
  });

  it.each([
    ['engine', ENGINE_PLACEMENT, ENGINE_LABEL],
    ['manual', MANUAL_PLACEMENT, 'Вручную'],
    ['rule', RULE_PLACEMENT, RULE_LABEL],
  ])(
    'in the chain «Проект» block a %s reason is an element with data-kind',
    async (kind, placement, label) => {
      openChain({ location: placed(CHAIN_OFFICE, ESTIMATE_THREAD, placement) });

      const link = await screen.findByRole('link', { name: 'Ремонт офиса' });
      const block = link.parentElement;
      if (!block) throw new Error('the project link has no block');
      expect(within(block).getByText(label)).toHaveAttribute('data-kind', kind);
    },
  );
});

describe('«Создать проект»', () => {
  it('the empty «Проекты» shows it exactly once, inside its empty state, and it opens «Новый проект»', async () => {
    renderApp({ path: '/projects', me: ANNA, routes: { 'GET /projects': () => json(200, []) } });

    const empty = await screen.findByText('Проектов пока нет: создайте первый');
    expect(screen.getAllByText('Создать проект')).toHaveLength(1);
    expect(
      [...screen.queryAllByRole('link'), ...screen.queryAllByRole('button')].filter(
        (node) => node.textContent === 'Создать проект',
      ),
    ).toHaveLength(1);
    const control = screen.getByText('Создать проект');
    expect(empty).toContainElement(control);
    fireEvent.click(control);

    await heading('Новый проект');
    expect(window.location.pathname).toBe('/projects/new');
  });

  it('a listed «Проекты» keeps the button «Создать проект» under the whole list', async () => {
    const project = (n: number, name: string): unknown => ({
      id: `dddddddd-0000-4000-8000-00000000000${String(n)}`,
      name,
      filled: true,
      placed_count: 2,
      unassigned_count: 0,
    });
    renderApp({
      path: '/projects',
      me: ANNA,
      routes: {
        'GET /projects': () =>
          json(200, [project(1, 'Ремонт офиса'), project(2, 'Закупка техники')]),
      },
    });

    const firstLink = await screen.findByRole('link', { name: 'Ремонт офиса' });
    const lastLink = screen.getByRole('link', { name: 'Закупка техники' });
    const list = lastLink.closest('table, ul, ol');
    if (!list) throw new Error('the projects are not in a list or a table');
    const button = screen.getByRole('button', { name: 'Создать проект' });
    expect(list).toContainElement(firstLink);
    expect(list).not.toContainElement(button);
    expect(list.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
    expect(screen.getAllByText('Создать проект')).toHaveLength(1);
  });
});

describe('«На главную»', () => {
  const FRAME_DATA = {
    ...START_DATA,
    'GET /rules': () => json(200, []),
    'GET /reply-chains': () => json(200, { items: [], next_cursor: null }),
  };

  it.each([
    ['Проекты', '/projects'],
    ['Правила', '/rules'],
    ['Почтовые ящики', '/mailboxes'],
    ['Переписка', '/chains'],
    ['Новый проект', '/projects/new'],
  ])('the page «%s» inside the app frame has no «На главную»', async (title, path) => {
    renderApp({ path, me: ANNA, routes: FRAME_DATA });

    await heading(title);
    await screen.findByText('Анна Петрова');

    expect(screen.queryByText('На главную')).not.toBeInTheDocument();
  });

  it('the start page has no «На главную»', async () => {
    renderApp({ path: '/', me: ANNA, routes: FRAME_DATA });

    await screen.findByText('Анна Петрова');
    await waitFor(() => {
      expect(screen.queryByText('Загрузка…')).not.toBeInTheDocument();
    });

    expect(screen.queryByText('На главную')).not.toBeInTheDocument();
  });

  it("a project's tree has no «На главную»", async () => {
    openProject({ tree: tree() });

    await chainRow('Смета на ремонт офиса');

    expect(screen.queryByText('На главную')).not.toBeInTheDocument();
  });

  it('a chain page has no «На главную»', async () => {
    openChain({ location: NONE });

    await screen.findByRole('heading', { level: 1, name: 'Счёт на мониторы' });

    expect(screen.queryByText('На главную')).not.toBeInTheDocument();
  });

  it('«Страница не найдена» keeps «На главную» and it leads to /', async () => {
    renderApp({ path: '/no-such-page', me: ANNA, routes: START_DATA });

    await heading('Страница не найдена');
    fireEvent.click(screen.getByRole('link', { name: 'На главную' }));

    await waitFor(() => {
      expect(window.location.pathname).toBe('/');
    });
  });
});
