import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  ANNA,
  alertWith,
  callsTo,
  fieldOf,
  heading,
  json,
  press,
  renderApp,
  rowOf,
  type,
} from './test/appHarness';
import { exactForm } from './test/projectTrees';

interface SummaryJson {
  id: string;
  name: string;
  filled: boolean;
  placed_count: number;
  unassigned_count: number;
}

const PROJECT_ID = 'dddddddd-0000-4000-8000-000000000001';
const DESCRIPTION = 'Ремонт офиса на Лесной: смета, график работ, акты, дизайн переговорной';
const EMPTY_PROJECT = 'Проект пуст: нажмите «Заполнить», чтобы найти его переписку';

function project(overrides: Partial<SummaryJson> = {}): SummaryJson {
  return {
    id: PROJECT_ID,
    name: 'Ремонт офиса',
    filled: true,
    placed_count: 3,
    unassigned_count: 0,
    ...overrides,
  };
}

function openList(projects: SummaryJson[]): ReturnType<typeof renderApp> {
  return renderApp({
    path: '/projects',
    me: ANNA,
    routes: { 'GET /projects': () => json(200, projects) },
  });
}

function follows(a: HTMLElement, b: HTMLElement): boolean {
  return (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}

function errorAnswer(
  status: number,
  code: string,
  message: string,
  fields?: Record<string, string>,
): Response {
  return json(status, { error: { code, message, ...(fields ? { fields } : {}) } });
}

describe('start page link', () => {
  it('SPA pages «Start page»: «Проекты» links to /projects beside «Почтовые ящики» and «Переписка»', async () => {
    renderApp({ path: '/', me: ANNA });

    await screen.findByText('Анна Петрова');
    expect(screen.getByRole('link', { name: 'Проекты' })).toHaveAttribute('href', '/projects');
    expect(screen.getByRole('link', { name: 'Почтовые ящики' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Переписка' })).toBeInTheDocument();
  });
});

describe('projects page: list', () => {
  it('FR-33 «The list of projects»: the projects come in the order of the answer with their counts', async () => {
    openList([
      project({ id: 'dddddddd-0000-4000-8000-000000000002', name: 'Конференция ТехФорум' }),
      project({ unassigned_count: 1 }),
    ]);

    const conference = await rowOf('Конференция ТехФорум');
    const renovation = await rowOf('Ремонт офиса');
    expect(follows(conference, renovation)).toBe(true);
    expect(conference).toHaveTextContent(exactForm('3 цепочки'));
    expect(conference).not.toHaveTextContent('неразобранн');
    expect(renovation).toHaveTextContent(exactForm('3 цепочки'));
    expect(renovation).toHaveTextContent(exactForm('1 неразобранная'));
  });

  it.each([
    [0, '0 цепочек'],
    [1, '1 цепочка'],
    [2, '2 цепочки'],
    [4, '4 цепочки'],
    [5, '5 цепочек'],
    [11, '11 цепочек'],
    [21, '21 цепочка'],
    [22, '22 цепочки'],
  ])('SPA pages «Проекты»: %i chains in threads read «%s»', async (count, text) => {
    openList([project({ placed_count: count })]);

    expect(await rowOf('Ремонт офиса')).toHaveTextContent(exactForm(text));
  });

  it.each([
    [1, '1 неразобранная'],
    [3, '3 неразобранные'],
    [5, '5 неразобранных'],
    [12, '12 неразобранных'],
    [21, '21 неразобранная'],
  ])('SPA pages «Проекты»: %i unassigned chains read «%s»', async (count, text) => {
    openList([project({ unassigned_count: count })]);

    expect(await rowOf('Ремонт офиса')).toHaveTextContent(exactForm(text));
  });

  it('FR-33 «No projects yet»: the empty list invites to create the first project', async () => {
    openList([]);

    expect(await screen.findByText('Проектов пока нет: создайте первый')).toBeInTheDocument();
    const create =
      screen.queryByRole('button', { name: 'Создать проект' }) ??
      screen.queryByRole('link', { name: 'Создать проект' });
    expect(create).toBeInTheDocument();
  });

  it('SPA pages «Проекты»: «Создать проект» opens «Новый проект»', async () => {
    openList([project()]);

    fireEvent.click(await screen.findByText('Создать проект'));

    await heading('Новый проект');
    expect(window.location.pathname).toBe('/projects/new');
  });

  it('FR-17: a signed-out visitor opening /projects sees «Вход»', async () => {
    renderApp({ path: '/projects', routes: { 'GET /projects': () => json(200, []) } });

    await heading('Вход');
  });
});

describe('new project page', () => {
  function openForm(answer: () => Response): ReturnType<typeof renderApp> {
    return renderApp({
      path: '/projects/new',
      me: ANNA,
      routes: {
        'POST /projects': answer,
        'GET /projects': () => json(200, []),
        [`GET /projects/${PROJECT_ID}`]: () =>
          json(200, {
            id: PROJECT_ID,
            name: 'Ремонт офиса',
            description: DESCRIPTION,
            filled: false,
            counterparties: [],
            unassigned: [],
          }),
      },
    });
  }

  it('FR-32 «A new project»: «Создать» sends the fields and opens the empty project', async () => {
    const app = openForm(() => json(201, project({ filled: false, placed_count: 0 })));

    await heading('Новый проект');
    type('Название', 'Ремонт офиса');
    type('Описание', DESCRIPTION);
    press('Создать');

    expect(await screen.findByText(EMPTY_PROJECT)).toBeInTheDocument();
    expect(screen.getByText('Ремонт офиса')).toBeInTheDocument();
    expect(window.location.pathname).toBe(`/projects/${PROJECT_ID}`);
    expect(callsTo(app, 'POST', '/projects').map((call) => call.body)).toEqual([
      { name: 'Ремонт офиса', description: DESCRIPTION },
    ]);
  });

  // Each case enters one invalid value; the server answers with that field's message, and a check on
  // the client may show the same message before any request.
  it.each([
    ['Название', 'only spaces', 'Укажите название проекта', 'name', '   '],
    ['Название', '101 characters', 'Название — не длиннее 100 символов', 'name', 'я'.repeat(101)],
    ['Описание', 'only spaces', 'Опишите проект', 'description', '   '],
    [
      'Описание',
      '2001 characters',
      'Описание — не длиннее 2000 символов',
      'description',
      'я'.repeat(2001),
    ],
  ])(
    'FR-32 «Empty or too long fields»: the field «%s» with %s shows «%s»',
    async (label, _case, message, field, value) => {
      openForm(() =>
        errorAnswer(422, 'validation_failed', 'Проверьте поля формы', { [field]: message }),
      );

      await heading('Новый проект');
      type('Название', label === 'Название' ? value : 'Ремонт офиса');
      type('Описание', label === 'Описание' ? value : DESCRIPTION);
      press('Создать');

      await screen.findByText(message);
      expect(fieldOf(label)).toHaveTextContent(message);
      expect(window.location.pathname).toBe('/projects/new');
    },
  );

  it('FR-32 «Empty or too long fields»: both fields show their own message at once', async () => {
    openForm(() =>
      errorAnswer(422, 'validation_failed', 'Проверьте поля формы', {
        name: 'Укажите название проекта',
        description: 'Описание — не длиннее 2000 символов',
      }),
    );

    await heading('Новый проект');
    type('Название', '   ');
    type('Описание', 'я'.repeat(2001));
    press('Создать');

    await screen.findByText('Укажите название проекта');
    expect(fieldOf('Название')).toHaveTextContent('Укажите название проекта');
    expect(fieldOf('Название')).not.toHaveTextContent('Описание — не длиннее 2000 символов');
    expect(fieldOf('Описание')).toHaveTextContent('Описание — не длиннее 2000 символов');
  });

  it('FR-32 «The same name twice»: the form shows «Проект с таким названием уже есть» and stays', async () => {
    const app = openForm(() =>
      errorAnswer(409, 'project_exists', 'Проект с таким названием уже есть'),
    );

    await heading('Новый проект');
    type('Название', 'ремонт офиса');
    type('Описание', DESCRIPTION);
    press('Создать');

    await alertWith('Проект с таким названием уже есть');
    await waitFor(() => {
      expect(callsTo(app, 'POST', '/projects').map((call) => call.body)).toEqual([
        { name: 'ремонт офиса', description: DESCRIPTION },
      ]);
    });
    expect(window.location.pathname).toBe('/projects/new');
    expect(screen.getByLabelText('Название')).toHaveValue('ремонт офиса');
  });
});
