import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ANNA, apiError, callsTo, heading, json, renderApp } from './test/appHarness';
import {
  PROJECT_ID,
  DESCRIPTION,
  EMPTY_PROJECT,
  NOTHING_FOUND,
  PETROV,
  ACT,
  chain,
  thread,
  tree,
  treeOf,
  openProject,
  chainRow,
  blockOf,
  exactForm,
  follows,
} from './test/projectTrees';

// Dates are shown in the machine's time zone; the tests pin it to UTC so the day never shifts.
process.env.TZ = 'UTC';

const SMIRNOVA = 'o.smirnova@interior-studio.example';

describe('project page: the tree', () => {
  it('FR-34 «The tree of a project»: name, description, the counterparty, its thread and both chains in it', async () => {
    openProject({ tree: tree() });

    const estimate = await chainRow('Смета на ремонт офиса');
    expect(screen.getByText('Ремонт офиса')).toBeInTheDocument();
    expect(screen.getByText(DESCRIPTION)).toBeInTheDocument();
    const counterparty = blockOf('Сергей Петров', ['Неразобранное', 'Офисная мебель']);
    expect(within(counterparty).getByText(PETROV)).toBeInTheDocument();
    const threadBlock = blockOf('Смета на ремонт офиса', ['Неразобранное', 'Офисная мебель']);
    expect(counterparty).toContainElement(threadBlock);
    const act = await chainRow('Акт скрытых работ');
    expect(threadBlock).toContainElement(estimate);
    expect(threadBlock).toContainElement(act);
    expect(estimate).toHaveTextContent(exactForm('3 письма'));
    expect(estimate).toHaveTextContent('05.03.2026');
    expect(act).toHaveTextContent(exactForm('1 письмо'));
    expect(act).toHaveTextContent('12.03.2026');
  });

  it('FR-34 «Opening a chain from the tree»: clicking the chain opens it with its emails', async () => {
    renderApp({
      path: `/projects/${PROJECT_ID}`,
      me: ANNA,
      routes: {
        [`GET /projects/${PROJECT_ID}`]: () => json(200, tree()),
        [`GET /reply-chains/${ACT.id}`]: () =>
          json(200, {
            id: ACT.id,
            subject: 'Акт скрытых работ',
            participants: [{ address: PETROV, name: 'Сергей Петров' }],
            emails: [
              {
                id: 'cccccccc-0000-4000-8000-000000000001',
                sender: { address: PETROV, name: 'Сергей Петров' },
                to: [{ address: 'anna@yandex.ru', name: null }],
                cc: [],
                sent_at: '2026-03-12T09:00:00Z',
                subject: 'Акт скрытых работ',
                text: 'Акт по объекту на Лесной',
                attachment_names: [],
              },
            ],
          }),
      },
    });

    const [link] = await screen.findAllByRole('link', { name: 'Акт скрытых работ' });
    if (!link) throw new Error('No link to the chain');
    expect(link).toHaveAttribute('href', `/chains/${ACT.id}`);
    fireEvent.click(link);

    expect(await screen.findByText('Акт по объекту на Лесной')).toBeInTheDocument();
    expect(window.location.pathname).toBe(`/chains/${ACT.id}`);
  });

  it('FR-37 «A chain placed by the engine»: the chain shows «Движок text-1 · сходство 43%»', async () => {
    openProject({ tree: tree() });

    expect(await chainRow('Смета на ремонт офиса')).toHaveTextContent(
      'Движок text-1 · сходство 43%',
    );
  });

  it('FR-37 «A chain placed by hand»: the chain shows «Вручную» and no similarity', async () => {
    openProject({
      tree: tree({
        counterparties: [
          {
            address: PETROV,
            name: 'Сергей Петров',
            threads: [
              thread('Акты', [
                chain(4, {
                  subject: 'Акт скрытых работ',
                  placement: { kind: 'manual', engine_version: null, similarity: null },
                }),
              ]),
            ],
          },
        ],
        unassigned: [],
      }),
    });

    const row = await chainRow('Акт скрытых работ');
    expect(row).toHaveTextContent('Вручную');
    expect(row).not.toHaveTextContent('Движок');
    expect(row).not.toHaveTextContent('сходство');
  });

  it('FR-37 «A chain placed by hand»: a chain of «Неразобранное» placed by hand shows «Вручную»', async () => {
    openProject({
      tree: tree({
        counterparties: [],
        unassigned: [
          chain(4, {
            subject: 'Выбор дизайна переговорной',
            placement: { kind: 'manual', engine_version: null, similarity: null },
          }),
        ],
      }),
    });

    const row = await chainRow('Выбор дизайна переговорной');
    expect(row).toHaveTextContent('Вручную');
    expect(row).not.toHaveTextContent('сходство');
  });

  it('FR-37 «An unsure chain»: a chain of «Неразобранное» shows «Движок text-1 · сходство 20%» after the tree', async () => {
    openProject({ tree: tree() });

    const unsure = await chainRow('Офисная мебель');
    expect(unsure).toHaveTextContent('Движок text-1 · сходство 20%');
    expect(unsure).toHaveTextContent(exactForm('5 писем'));
    const section = screen.getByText('Неразобранное');
    expect(follows(section, unsure)).toBe(true);
    expect(follows(await chainRow('Акт скрытых работ'), section)).toBe(true);
  });

  it.each([
    [0.4271, '43%'],
    [0.195, '20%'],
    [0.3049, '30%'],
    [1, '100%'],
  ])(
    'SPA pages «Project»: the similarity %f shows as «сходство %s»',
    async (similarity, percent) => {
      openProject({
        tree: treeOf(
          chain(4, { placement: { kind: 'engine', engine_version: 'text-2', similarity } }),
        ),
      });

      expect(await chainRow('Цепочка 4')).toHaveTextContent(`Движок text-2 · сходство ${percent}`);
    },
  );

  it.each([
    [1, '1 письмо'],
    [2, '2 письма'],
    [5, '5 писем'],
    [11, '11 писем'],
    [21, '21 письмо'],
    [24, '24 письма'],
  ])('SPA pages «Project»: a chain of %i emails reads «%s»', async (count, text) => {
    openProject({ tree: treeOf(chain(4, { email_count: count })) });

    expect(await chainRow('Цепочка 4')).toHaveTextContent(exactForm(text));
  });

  it('FR-34 «A chain with two counterparties»: the chain is under each counterparty, in a thread of the same name', async () => {
    const shared = thread('Дизайн переговорной', [chain(5, { subject: 'Дизайн переговорной' })]);
    openProject({
      tree: tree({
        counterparties: [
          { address: SMIRNOVA, name: 'Ольга Смирнова', threads: [shared] },
          { address: PETROV, name: 'Сергей Петров', threads: [shared] },
        ],
        unassigned: [],
      }),
    });

    expect(await screen.findAllByRole('link', { name: 'Дизайн переговорной' })).toHaveLength(2);
    for (const [name, other] of [
      ['Ольга Смирнова', 'Сергей Петров'],
      ['Сергей Петров', 'Ольга Смирнова'],
    ] as const) {
      const block = blockOf(name, [other]);
      expect(within(block).getAllByRole('link', { name: 'Дизайн переговорной' })).toHaveLength(1);
      const threadNames = within(block)
        .getAllByText('Дизайн переговорной')
        .filter((node) => node.closest('a') === null);
      expect(threadNames).toHaveLength(1);
    }
  });

  it('FR-34 «A chain without counterparties»: it is shown inside the «Без контрагента» block', async () => {
    openProject({
      tree: tree({
        counterparties: [
          { address: null, name: 'Без контрагента', threads: [thread('Заметки', [chain(6)])] },
        ],
        unassigned: [],
      }),
    });

    const row = await chainRow('Цепочка 6');
    expect(blockOf('Без контрагента')).toContainElement(row);
  });

  it('FR-32 «A new project»: a project never filled shows its name and «Проект пуст…»', async () => {
    openProject({ tree: tree({ filled: false, counterparties: [], unassigned: [] }) });

    expect(await screen.findByText(EMPTY_PROJECT)).toBeInTheDocument();
    expect(screen.getByText('Ремонт офиса')).toBeInTheDocument();
    expect(screen.queryByText(NOTHING_FOUND)).not.toBeInTheDocument();
  });

  it('SPA pages «Project»: a project with chains shows neither empty text', async () => {
    openProject({ tree: tree() });

    await chainRow('Смета на ремонт офиса');
    expect(screen.queryByText(EMPTY_PROJECT)).not.toBeInTheDocument();
    expect(screen.queryByText(NOTHING_FOUND)).not.toBeInTheDocument();
  });

  it("FR-34 «Another user's project»: a project the API answers «not found» shows «Страница не найдена»", async () => {
    const app = renderApp({
      path: `/projects/${PROJECT_ID}`,
      me: ANNA,
      routes: { [`GET /projects/${PROJECT_ID}`]: () => apiError(404, 'not_found') },
    });

    // The page asked for the project: the answer, not an unknown route, gives the text.
    await waitFor(() => {
      expect(callsTo(app, 'GET', `/projects/${PROJECT_ID}`)).toHaveLength(1);
    });
    await heading('Страница не найдена');
  });
});
