import { screen, within } from '@testing-library/react';

import { ANNA, json, renderApp, type Rendered } from './appHarness';

// Fixtures of the project page tests: the JSON of «Schemas» («ProjectTree» and its nodes), a sample
// tree of «Ремонт офиса», and lookups of chain rows and of the confirmation.

export interface PlacedChainJson {
  id: string;
  subject: string;
  email_count: number;
  latest_email_at: string;
  placement:
    | { kind: 'engine'; engine_version: string; similarity: number }
    | { kind: 'manual'; engine_version: null; similarity: null };
}

export interface ThreadJson {
  id: string;
  name: string;
  chains: PlacedChainJson[];
}

export interface CounterpartyJson {
  address: string | null;
  name: string;
  threads: ThreadJson[];
}

export interface TreeJson {
  id: string;
  name: string;
  description: string;
  filled: boolean;
  counterparties: CounterpartyJson[];
  unassigned: PlacedChainJson[];
}

export const PROJECT_ID = 'dddddddd-0000-4000-8000-000000000001';
export const FILL = `/projects/${PROJECT_ID}/fill`;
export const DESCRIPTION = 'Ремонт офиса на Лесной: смета, график работ, акты, дизайн переговорной';
export const EMPTY_PROJECT = 'Проект пуст: нажмите «Заполнить», чтобы найти его переписку';
export const NOTHING_FOUND = 'Подходящей переписки не нашлось: уточните описание';
export const REBUILD =
  'Пересобрать проект? Движок разложит его переписку заново, а цепочки, размещённые вручную, останутся на месте';
export const PETROV = 's.petrov@stroymaster.example';

export function chain(n: number, overrides: Partial<PlacedChainJson> = {}): PlacedChainJson {
  return {
    id: `eeeeeeee-0000-4000-8000-00000000000${String(n)}`,
    subject: `Цепочка ${String(n)}`,
    email_count: 1,
    latest_email_at: '2026-03-05T12:00:00Z',
    placement: { kind: 'engine', engine_version: 'text-1', similarity: 0.5 },
    ...overrides,
  };
}

export const ESTIMATE = chain(1, {
  subject: 'Смета на ремонт офиса',
  email_count: 3,
  latest_email_at: '2026-03-05T12:00:00Z',
  placement: { kind: 'engine', engine_version: 'text-1', similarity: 0.4271 },
});
export const ACT = chain(2, {
  subject: 'Акт скрытых работ',
  latest_email_at: '2026-03-12T09:00:00Z',
});
export const FURNITURE = chain(3, {
  subject: 'Офисная мебель',
  email_count: 5,
  placement: { kind: 'engine', engine_version: 'text-1', similarity: 0.195 },
});

export function thread(name: string, chains: PlacedChainJson[]): ThreadJson {
  return { id: 'ffffffff-0000-4000-8000-000000000001', name, chains };
}

export function tree(overrides: Partial<TreeJson> = {}): TreeJson {
  return {
    id: PROJECT_ID,
    name: 'Ремонт офиса',
    description: DESCRIPTION,
    filled: true,
    counterparties: [
      {
        address: PETROV,
        name: 'Сергей Петров',
        threads: [thread('Смета на ремонт офиса', [ESTIMATE, ACT])],
      },
    ],
    unassigned: [FURNITURE],
    ...overrides,
  };
}

// Single-chain tree: the chain under one counterparty.
export function treeOf(placed: PlacedChainJson): TreeJson {
  return tree({
    counterparties: [
      { address: PETROV, name: 'Сергей Петров', threads: [thread('Тред', [placed])] },
    ],
    unassigned: [],
  });
}

// The project page; GET answers `state.tree`, which a fill answer may replace.
export function openProject(
  state: { tree: TreeJson },
  fill?: () => Response | Promise<Response>,
): Rendered {
  return renderApp({
    path: `/projects/${PROJECT_ID}`,
    me: ANNA,
    routes: {
      [`GET /projects/${PROJECT_ID}`]: () => json(200, state.tree),
      ...(fill ? { [`POST ${FILL}`]: fill } : {}),
    },
  });
}

// The row (table row or list item) of the n-th link to a chain.
export async function chainRow(subject: string, index = 0): Promise<HTMLElement> {
  const links = await screen.findAllByRole('link', { name: subject });
  const row = links[index]?.closest<HTMLElement>('tr, li');
  if (!row) throw new Error(`No row holds the chain «${subject}»`);
  return row;
}

// The block of a tree node (a counterparty or a thread): the nearest ancestor of its name, shown outside
// any link, that holds a chain link. It must hold none of `others` (sibling names, other chains), so it
// is the block of that node alone.
export function blockOf(name: string, others: string[] = []): HTMLElement {
  const label = screen.getAllByText(name).find((node) => node.closest('a') === null);
  if (!label) throw new Error(`«${name}» is not shown outside a link`);
  let block: HTMLElement | null = label;
  while (block && within(block).queryAllByRole('link').length === 0) block = block.parentElement;
  if (!block) throw new Error(`No block of «${name}» holds a chain`);
  for (const other of others) {
    if (within(block).queryAllByText(other).length > 0) {
      throw new Error(`The block of «${name}» also holds «${other}»`);
    }
  }
  return block;
}

// A count with its word, matched whole: «1 письмо» does not match inside «11 письмо» or «1 письмом».
export function exactForm(text: string): RegExp {
  return new RegExp(`(?<![0-9])${text}(?![а-яё])`);
}

export function follows(a: HTMLElement, b: HTMLElement): boolean {
  return (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}

// The nearest ancestor of the text that also holds the «Отмена» button: the confirmation.
export async function confirmationWith(text: string): Promise<HTMLElement> {
  let node: HTMLElement | null = await screen.findByText(text);
  while (node) {
    if (within(node).queryByRole('button', { name: 'Отмена' })) return node;
    node = node.parentElement;
  }
  throw new Error(`No confirmation holds «${text}»`);
}
