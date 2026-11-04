import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  alertWith,
  apiError,
  callsTo,
  fieldOf,
  heading,
  json,
  noContent,
  press,
  type,
  type Rendered,
} from './test/appHarness';
import { listedRules, pressIn } from './test/rulesPage';
import {
  DELETION,
  DESCRIPTION,
  EMPTY_PROJECT,
  HINT,
  PATCH_PROJECT,
  REBUILD,
  confirmationWith,
  openEditableProject,
  tree,
  type EditableRule,
} from './test/projectTrees';

const NEW_DESCRIPTION = 'Ремонт офиса на Лесной: смета и акты';
const STROYMASTER_RULE: EditableRule = {
  id: 'aaaaaaaa-0000-4000-8000-000000000001',
  condition: 'domain',
  value: 'stroymaster.example',
  thread_name: 'Смета',
};
const DESIGN_RULE: EditableRule = {
  id: 'aaaaaaaa-0000-4000-8000-000000000002',
  condition: 'subject',
  value: 'дизайн',
  thread_name: null,
};

function confirmationText(name: string, chains: number, rules: number): string {
  return (
    `Удалить проект «${name}»? Цепочек в проекте: ${String(chains)} — они останутся в «Переписке» ` +
    `как убранные вручную. Правил, ведущих в проект: ${String(rules)} — они будут удалены. ` +
    'Письма не удаляются.'
  );
}

async function openEditForm(): Promise<void> {
  press('Изменить');
  await screen.findByRole('button', { name: 'Сохранить' });
}

function patchBodies(app: Rendered): unknown[] {
  return callsTo(app, 'PATCH', PATCH_PROJECT).map((call) => call.body);
}

function goTo(link: string): void {
  const header = within(screen.getByRole('banner'));
  fireEvent.click(header.getByRole('link', { name: link }));
}

// Every call that is not a read.
function writes(app: Rendered): string[] {
  return app.calls
    .filter((call) => call.method !== 'GET')
    .map((call) => `${call.method} ${call.path}`);
}

describe('project page: editing', () => {
  it('FR-55 «Renaming a project»: «Сохранить» sends the fields; «Проекты» and «Правила» then list the new name', async () => {
    const state = { tree: tree(), rules: [STROYMASTER_RULE] };
    const app = openEditableProject(state, {
      edit: () => {
        state.tree = tree({ name: 'Ремонт офиса на Лесной' });
        return json(200, state.tree);
      },
    });

    await screen.findByText('Ремонт офиса');
    await openEditForm();
    expect(screen.getByLabelText('Название')).toHaveValue('Ремонт офиса');
    expect(screen.getByLabelText('Описание')).toHaveValue(DESCRIPTION);
    type('Название', 'Ремонт офиса на Лесной');
    press('Сохранить');

    await screen.findByText('Ремонт офиса на Лесной');
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'Сохранить' })).not.toBeInTheDocument();
    });
    expect(patchBodies(app)).toEqual([
      { name: 'Ремонт офиса на Лесной', description: DESCRIPTION },
    ]);

    goTo('Проекты');
    expect(await screen.findByText('Ремонт офиса на Лесной')).toBeInTheDocument();
    expect(screen.queryByText('Ремонт офиса', { exact: true })).not.toBeInTheDocument();

    goTo('Правила');
    await waitFor(() => {
      expect(listedRules()).toEqual([
        'Домен: stroymaster.example → Ремонт офиса на Лесной → Смета',
      ]);
    });
  });

  it('FR-55: «Отмена» closes the form and sends nothing', async () => {
    const state = { tree: tree() };
    const app = openEditableProject(state, { edit: () => json(200, state.tree) });

    await screen.findByText('Ремонт офиса');
    await openEditForm();
    type('Название', 'Другое имя');
    press('Отмена');

    expect(screen.queryByRole('button', { name: 'Сохранить' })).not.toBeInTheDocument();
    expect(screen.getByText('Ремонт офиса')).toBeInTheDocument();
    expect(screen.queryByText('Другое имя')).not.toBeInTheDocument();
    expect(callsTo(app, 'PATCH', PATCH_PROJECT)).toHaveLength(0);
  });

  it('FR-55 «A name of another project»: renaming «Закупка техники» to «РЕМОНТ ОФИСА» shows «Проект с таким названием уже есть» and stays', async () => {
    const state = { tree: tree({ name: 'Закупка техники' }) };
    const app = openEditableProject(state, {
      edit: () => apiError(409, 'project_exists'),
    });

    await screen.findByText('Закупка техники');
    await openEditForm();
    type('Название', 'РЕМОНТ ОФИСА');
    press('Сохранить');

    await alertWith('Проект с таким названием уже есть');
    expect(patchBodies(app)).toEqual([{ name: 'РЕМОНТ ОФИСА', description: DESCRIPTION }]);
    expect(screen.getByRole('button', { name: 'Сохранить' })).toBeInTheDocument();
    expect(screen.getByLabelText('Название')).toHaveValue('РЕМОНТ ОФИСА');
  });

  it.each([
    ['Название', 'name', 'Укажите название проекта', '   '],
    ['Описание', 'description', 'Описание — не длиннее 2000 символов', 'я'.repeat(2001)],
  ])(
    'FR-55 «Empty or too long fields»: the field «%s» shows «%s» and the form stays',
    async (label, field, message, value) => {
      const state = { tree: tree() };
      const app = openEditableProject(state, {
        edit: () => apiError(422, 'validation_failed', { [field]: message }),
      });

      await screen.findByText('Ремонт офиса');
      await openEditForm();
      type(label, value);
      press('Сохранить');

      await screen.findByText(message);
      expect(fieldOf(label)).toHaveTextContent(message);
      expect(screen.getByRole('button', { name: 'Сохранить' })).toBeInTheDocument();
      // A check on the client may show the message before any request; a request that is sent
      // carries the typed value.
      for (const body of patchBodies(app)) {
        expect(body).toMatchObject({ [field]: value });
      }
    },
  );

  it('FR-55 «A changed description moves nothing»: after saving a new description the page shows the hint and the chains', async () => {
    const state = { tree: tree() };
    const app = openEditableProject(state, {
      edit: () => {
        state.tree = tree({ description: NEW_DESCRIPTION, description_changed: true });
        return json(200, state.tree);
      },
    });

    await screen.findByText('Ремонт офиса');
    expect(screen.queryByText(HINT)).not.toBeInTheDocument();
    await openEditForm();
    type('Описание', NEW_DESCRIPTION);
    press('Сохранить');

    expect(await screen.findByText(HINT)).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Смета на ремонт офиса' })).toHaveLength(1);
    expect(patchBodies(app)).toEqual([{ name: 'Ремонт офиса', description: NEW_DESCRIPTION }]);
    expect(writes(app)).toEqual(['PATCH ' + PATCH_PROJECT]);
  });

  it('FR-55 «The hint goes after filling»: «Заполнить» makes the hint go', async () => {
    const state = { tree: tree({ description_changed: true }) };
    openEditableProject(state, {
      fill: () => {
        state.tree = tree({ description_changed: false });
        return json(200, state.tree);
      },
    });

    await screen.findByText(HINT);
    press('Заполнить');
    pressIn(await confirmationWith(REBUILD), 'Пересобрать');

    await waitFor(() => {
      expect(screen.queryByText(HINT)).not.toBeInTheDocument();
    });
  });

  it('FR-55 «Only the name changed»: renaming a filled project and saving shows no hint', async () => {
    const state = { tree: tree() };
    const app = openEditableProject(state, {
      edit: () => {
        state.tree = tree({ name: 'Ремонт на Лесной', description_changed: false });
        return json(200, state.tree);
      },
    });

    await screen.findByText('Ремонт офиса');
    await openEditForm();
    type('Название', 'Ремонт на Лесной');
    press('Сохранить');

    await screen.findByText('Ремонт на Лесной');
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'Сохранить' })).not.toBeInTheDocument();
    });
    expect(patchBodies(app)).toEqual([{ name: 'Ремонт на Лесной', description: DESCRIPTION }]);
    expect(screen.queryByText(HINT)).not.toBeInTheDocument();
  });

  it('FR-55 «An unfilled project»: a new description of «Отпуск» shows no hint and keeps the empty-project text', async () => {
    const empty = { filled: false, description_changed: false, counterparties: [], unassigned: [] };
    const state = { tree: tree({ ...empty, name: 'Отпуск', description: 'Отпуск в августе' }) };
    const app = openEditableProject(state, {
      edit: () => {
        state.tree = tree({ ...empty, name: 'Отпуск', description: 'Отпуск в сентябре' });
        return json(200, state.tree);
      },
    });

    expect(await screen.findByText(EMPTY_PROJECT)).toBeInTheDocument();
    await openEditForm();
    type('Описание', 'Отпуск в сентябре');
    press('Сохранить');

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'Сохранить' })).not.toBeInTheDocument();
    });
    expect(patchBodies(app)).toEqual([{ name: 'Отпуск', description: 'Отпуск в сентябре' }]);
    expect(screen.getByText(EMPTY_PROJECT)).toBeInTheDocument();
    expect(screen.queryByText(HINT)).not.toBeInTheDocument();
  });
});

describe('project page: deleting', () => {
  it('FR-56 «Deleting a project»: «Удалить проект» asks with the counts, «Удалить» deletes, lands on «Проекты» and the project and its rules are gone', async () => {
    const state = { tree: tree(), rules: [STROYMASTER_RULE, DESIGN_RULE] };
    const app = openEditableProject(state, {
      counts: () => json(200, { chain_count: 5, rule_count: 2 }),
      remove: () => noContent(),
    });

    await screen.findByText('Ремонт офиса');
    press('Удалить проект');
    const confirmation = await confirmationWith(confirmationText('Ремонт офиса', 5, 2));
    expect(callsTo(app, 'DELETE', PATCH_PROJECT)).toHaveLength(0);
    expect(callsTo(app, 'GET', DELETION)).toHaveLength(1);
    pressIn(confirmation, 'Удалить');

    await heading('Проекты');
    expect(window.location.pathname).toBe('/projects');
    expect(callsTo(app, 'DELETE', PATCH_PROJECT)).toHaveLength(1);
    expect(await screen.findByText('Проектов пока нет: создайте первый')).toBeInTheDocument();
    expect(screen.queryByText('Ремонт офиса')).not.toBeInTheDocument();

    goTo('Правила');
    await waitFor(() => {
      expect(callsTo(app, 'GET', '/rules').length).toBeGreaterThan(0);
    });
    expect(listedRules()).toEqual([]);
    expect(screen.queryByText(/stroymaster\.example/)).not.toBeInTheDocument();
  });

  it('FR-56 «An empty project»: «Отпуск» is asked with 0 and 0, and after «Удалить» it is no longer listed', async () => {
    const state = {
      tree: tree({ name: 'Отпуск', filled: false, counterparties: [], unassigned: [] }),
    };
    const app = openEditableProject(state, {
      counts: () => json(200, { chain_count: 0, rule_count: 0 }),
      remove: () => noContent(),
    });

    await screen.findByText('Отпуск');
    press('Удалить проект');
    const confirmation = await confirmationWith(confirmationText('Отпуск', 0, 0));
    pressIn(confirmation, 'Удалить');

    await heading('Проекты');
    expect(callsTo(app, 'DELETE', PATCH_PROJECT)).toHaveLength(1);
    expect(await screen.findByText('Проектов пока нет: создайте первый')).toBeInTheDocument();
    expect(screen.queryByText('Отпуск')).not.toBeInTheDocument();
  });

  it('FR-56 «Deleting cancelled»: «Отмена» closes the confirmation, changes nothing and sends no write', async () => {
    const state = { tree: tree(), rules: [STROYMASTER_RULE, DESIGN_RULE] };
    const app = openEditableProject(state, {
      counts: () => json(200, { chain_count: 5, rule_count: 2 }),
      remove: () => noContent(),
    });

    await screen.findByText('Ремонт офиса');
    press('Удалить проект');
    const confirmation = await confirmationWith(confirmationText('Ремонт офиса', 5, 2));
    pressIn(confirmation, 'Отмена');

    await waitFor(() => {
      expect(screen.queryByText(confirmationText('Ремонт офиса', 5, 2))).not.toBeInTheDocument();
    });
    expect(window.location.pathname).toBe(`/projects/${state.tree.id}`);
    expect(screen.getAllByRole('link', { name: 'Смета на ремонт офиса' })).toHaveLength(1);
    expect(screen.getByRole('button', { name: 'Удалить проект' })).toBeInTheDocument();
    expect(writes(app)).toEqual([]);
  });

  it('FR-56 «A deleted project»: opening a project the API no longer knows shows «Страница не найдена»', async () => {
    const state = { tree: tree(), deleted: true };
    openEditableProject(state);

    expect(await heading('Страница не найдена')).toBeInTheDocument();
  });
});
