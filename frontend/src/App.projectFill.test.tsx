import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { callsTo, json, press } from './test/appHarness';
import {
  FILL,
  EMPTY_PROJECT,
  FURNITURE,
  NOTHING_FOUND,
  REBUILD,
  chain,
  tree,
  treeOf,
  openProject,
  chainRow,
  confirmationWith,
} from './test/projectTrees';

// Dates are shown in the machine's time zone; the tests pin it to UTC so the day never shifts.
process.env.TZ = 'UTC';

// Lets every pending promise and the requests they start run: a request sent at all is recorded by then.
async function settle(): Promise<void> {
  await act(async () => {
    await new Promise<void>((resolve) => {
      setTimeout(resolve, 0);
    });
  });
}

describe('project page: filling', () => {
  it('FR-35 «Filling a project»: «Заполнить» on an empty project fills it without asking', async () => {
    const state = { tree: tree({ filled: false, counterparties: [], unassigned: [] }) };
    const app = openProject(state, () => {
      state.tree = tree();
      return json(200, state.tree);
    });

    await screen.findByText(EMPTY_PROJECT);
    press('Заполнить');

    await chainRow('Смета на ремонт офиса');
    expect(screen.queryByText(REBUILD)).not.toBeInTheDocument();
    expect(callsTo(app, 'POST', FILL)).toHaveLength(1);
  });

  it('FR-35 «Nothing matches»: a fill that finds nothing shows «Подходящей переписки не нашлось…»', async () => {
    const state = { tree: tree({ filled: false, counterparties: [], unassigned: [] }) };
    const app = openProject(state, () => {
      state.tree = tree({ counterparties: [], unassigned: [] });
      return json(200, state.tree);
    });

    await screen.findByText(EMPTY_PROJECT);
    press('Заполнить');

    expect(await screen.findByText(NOTHING_FOUND)).toBeInTheDocument();
    expect(screen.queryByText(EMPTY_PROJECT)).not.toBeInTheDocument();
    expect(callsTo(app, 'POST', FILL)).toHaveLength(1);
  });

  it('SPA pages «Project»: while filling the button shows «Заполняется…»', async () => {
    const state = { tree: tree({ filled: false, counterparties: [], unassigned: [] }) };
    let answer: (response: Response) => void = () => undefined;
    openProject(
      state,
      () =>
        new Promise<Response>((resolve) => {
          answer = resolve;
        }),
    );

    await screen.findByText(EMPTY_PROJECT);
    press('Заполнить');

    expect(await screen.findByRole('button', { name: 'Заполняется…' })).toBeInTheDocument();
    state.tree = tree();
    await act(async () => {
      answer(json(200, state.tree));
      await Promise.resolve();
    });
    expect(await screen.findByRole('button', { name: 'Заполнить' })).toBeInTheDocument();
    await chainRow('Смета на ремонт офиса');
  });

  it('FR-36 «Filling again»: on a project with chains «Заполнить» asks first and sends nothing yet', async () => {
    const app = openProject({ tree: tree() }, () => json(200, tree()));

    await chainRow('Смета на ремонт офиса');
    press('Заполнить');

    const confirmation = await confirmationWith(REBUILD);
    expect(within(confirmation).getByRole('button', { name: 'Пересобрать' })).toBeInTheDocument();
    expect(callsTo(app, 'POST', FILL)).toHaveLength(0);
  });

  it('FR-36: a filled project whose only chains are in «Неразобранное» also asks first', async () => {
    const app = openProject({ tree: tree({ counterparties: [], unassigned: [FURNITURE] }) }, () =>
      json(200, tree()),
    );

    await chainRow('Офисная мебель');
    press('Заполнить');

    await confirmationWith(REBUILD);
    await settle();
    expect(callsTo(app, 'POST', FILL)).toHaveLength(0);
  });

  it('FR-36 «Filling again»: «Пересобрать» fills the project again and shows the new tree', async () => {
    const state = { tree: tree() };
    const rebuilt = chain(1, {
      subject: 'Смета на ремонт офиса',
      placement: { kind: 'engine', engine_version: 'text-2', similarity: 0.61 },
    });
    const app = openProject(state, () => {
      state.tree = treeOf(rebuilt);
      return json(200, state.tree);
    });

    await chainRow('Смета на ремонт офиса');
    press('Заполнить');
    const confirmation = await confirmationWith(REBUILD);
    fireEvent.click(within(confirmation).getByRole('button', { name: 'Пересобрать' }));

    await waitFor(async () => {
      expect(await chainRow('Смета на ремонт офиса')).toHaveTextContent(
        'Движок text-2 · сходство 61%',
      );
    });
    expect(callsTo(app, 'POST', FILL)).toHaveLength(1);
    expect(screen.queryByText(REBUILD)).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Акт скрытых работ' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Офисная мебель' })).not.toBeInTheDocument();
  });

  it('FR-36 «Cancelled»: «Отмена» closes the question, sends nothing and keeps the tree', async () => {
    const app = openProject({ tree: tree() }, () => json(200, tree()));

    await chainRow('Офисная мебель');
    const before = document.body.textContent;
    press('Заполнить');
    const confirmation = await confirmationWith(REBUILD);
    fireEvent.click(within(confirmation).getByRole('button', { name: 'Отмена' }));
    await settle();

    expect(callsTo(app, 'POST', FILL)).toHaveLength(0);
    expect(screen.queryByText(REBUILD)).not.toBeInTheDocument();
    // The whole page reads as before: counterparty, thread, every chain with its placement line.
    expect(document.body.textContent).toBe(before);
    expect(await chainRow('Смета на ремонт офиса')).toHaveTextContent(
      'Движок text-1 · сходство 43%',
    );
    expect(await chainRow('Акт скрытых работ')).toHaveTextContent('Движок text-1 · сходство 50%');
    expect(await chainRow('Офисная мебель')).toHaveTextContent('Движок text-1 · сходство 20%');
    // Asking again and confirming sends exactly one fill: the cancelled one sent none.
    press('Заполнить');
    const again = await confirmationWith(REBUILD);
    fireEvent.click(within(again).getByRole('button', { name: 'Пересобрать' }));
    await waitFor(() => {
      expect(callsTo(app, 'POST', FILL)).toHaveLength(1);
    });
  });
});
