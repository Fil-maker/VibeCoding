import { screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  ANNA,
  apiError,
  callsTo,
  fieldOf,
  heading,
  json,
  press,
  renderApp,
  START_DATA,
} from './test/appHarness';
import { confirmationWith } from './test/projectTrees';
import {
  BY_ADDRESS,
  BY_DOMAIN,
  BY_SUBJECT,
  CONFIRM_DELETE,
  EXISTS,
  OFFICE,
  TECH,
  chooseIn,
  createForm,
  editForm,
  fillCreate,
  fieldOfIn,
  listedRules,
  openRules,
  rule,
  pressIn,
  ruleRow,
  typeIn,
  writesOtherThan,
  type RuleJson,
} from './test/rulesPage';

describe('header', () => {
  it('SPA «Header»: the link «Правила» leads to /rules beside «Проекты»', async () => {
    renderApp({ path: '/', me: ANNA, routes: START_DATA });

    await screen.findByText('Анна Петрова');
    const header = within(screen.getByRole('banner'));
    expect(header.getByRole('link', { name: 'Правила' })).toHaveAttribute('href', '/rules');
    expect(header.getByRole('link', { name: 'Проекты' })).toBeInTheDocument();
  });
});

describe('rules page: create', () => {
  it('FR-43 «A rule by address»: the rule is sent with the fields and listed as «Адрес отправителя: s.petrov@stroymaster.example → Ремонт офиса → Смета»', async () => {
    const state = { rules: [] as RuleJson[] };
    const app = openRules(state);

    await heading('Правила');
    await fillCreate('Адрес отправителя', 'S.Petrov@StroyMaster.example', 'Ремонт офиса', 'Смета');
    press('Создать правило');

    const row = await ruleRow('s.petrov@stroymaster.example');
    expect(row).toHaveTextContent(
      'Адрес отправителя: s.petrov@stroymaster.example → Ремонт офиса → Смета',
    );
    const posts = callsTo(app, 'POST', '/rules');
    expect(posts).toHaveLength(1);
    expect(posts[0]?.body).toMatchObject({
      condition: 'address',
      value: 'S.Petrov@StroyMaster.example',
      project_id: OFFICE.id,
      thread_name: 'Смета',
    });
  });

  it('FR-43 «A rule into «Неразобранное»»: a domain rule with no thread name is listed «Домен: techsnab.example → Закупка техники → Неразобранное»', async () => {
    const state = { rules: [] as RuleJson[] };
    const app = openRules(state);

    await heading('Правила');
    await fillCreate('Домен', 'techsnab.example', 'Закупка техники', '');
    press('Создать правило');

    expect(await ruleRow('techsnab.example')).toHaveTextContent(
      'Домен: techsnab.example → Закупка техники → Неразобранное',
    );
    expect(callsTo(app, 'POST', '/rules')[0]?.body).toMatchObject({
      condition: 'domain',
      value: 'techsnab.example',
      project_id: TECH.id,
    });
  });

  it('FR-43 «A rule into «Неразобранное»»: a thread name of spaces only is listed as «Неразобранное»', async () => {
    const state = { rules: [] as RuleJson[] };
    openRules(state);

    await heading('Правила');
    await fillCreate('Домен', 'techsnab.example', 'Закупка техники', '   ');
    press('Создать правило');

    expect(await ruleRow('techsnab.example')).toHaveTextContent(
      'Домен: techsnab.example → Закупка техники → Неразобранное',
    );
  });

  it('FR-43: a rule by subject words is listed «Слова темы: акт работ → Ремонт офиса → Акты»', async () => {
    const state = { rules: [] as RuleJson[] };
    const app = openRules(state);

    await heading('Правила');
    await fillCreate('Слова темы', 'акт работ', 'Ремонт офиса', 'Акты');
    press('Создать правило');

    expect(await ruleRow('акт работ')).toHaveTextContent(
      'Слова темы: акт работ → Ремонт офиса → Акты',
    );
    expect(callsTo(app, 'POST', '/rules')[0]?.body).toMatchObject({ condition: 'subject' });
  });

  it.each([
    ['Адрес отправителя', 'petrov', 'Значение', 'value', 'Укажите адрес почты'],
    ['Домен', '@techsnab', 'Значение', 'value', 'Укажите домен, например stroymaster.example'],
    ['Домен', 'techsnab', 'Значение', 'value', 'Укажите домен, например stroymaster.example'],
    ['Слова темы', '   ', 'Значение', 'value', 'Укажите слова темы'],
    ['Слова темы', 'я'.repeat(201), 'Значение', 'value', 'Слова темы — не длиннее 200 символов'],
    [
      'Домен',
      'techsnab.example',
      'Ветка',
      'thread_name',
      'Название ветки — не длиннее 100 символов',
    ],
  ])(
    'FR-43 «Invalid values»: the condition «%s» with %j and the field «%s» (%s) shows «%s» and creates nothing',
    async (condition, value, label, field, message) => {
      const state = { rules: [] as RuleJson[] };
      openRules(state, {
        post: () => apiError(422, 'validation_failed', { [field]: message }),
      });

      await heading('Правила');
      await fillCreate(
        condition,
        label === 'Значение' ? value : 'techsnab.example',
        'Ремонт офиса',
        label === 'Ветка' ? 'я'.repeat(101) : '',
      );
      press('Создать правило');

      await screen.findByText(message);
      expect(fieldOf(label)).toHaveTextContent(message);
      expect(listedRules()).toEqual([]);
    },
  );

  it('FR-43 «No project»: a rule without a project shows «Выберите проект» at «Проект» and creates nothing', async () => {
    const state = { rules: [] as RuleJson[] };
    openRules(state, {
      post: () => apiError(422, 'validation_failed', { project_id: 'Выберите проект' }),
    });

    await heading('Правила');
    await fillCreate('Домен', 'techsnab.example', null, '');
    press('Создать правило');

    const shownError = (): HTMLElement | undefined =>
      screen.getAllByText('Выберите проект').find((node) => node.tagName !== 'OPTION');
    await waitFor(() => {
      expect(shownError()).toBeDefined();
    });
    expect(fieldOf('Проект')).toContainElement(shownError() ?? null);
    expect(listedRules()).toEqual([]);
  });

  it('FR-43 «A repeated rule»: the form shows «Такое правило уже есть» and the list stays', async () => {
    const state = { rules: [BY_DOMAIN] };
    const app = openRules(state, { post: () => apiError(409, 'rule_exists') });

    await heading('Правила');
    await fillCreate('Домен', 'TechSnab.example', 'Ремонт офиса', '');
    press('Создать правило');

    expect(await within(createForm()).findByText(EXISTS)).toBeInTheDocument();
    expect(listedRules()).toHaveLength(1);
    expect(callsTo(app, 'POST', '/rules')[0]?.body).toMatchObject({
      condition: 'domain',
      value: 'TechSnab.example',
    });
  });

  it('FR-43 «Too many rules»: the page shows «Правил не может быть больше 200»', async () => {
    const state = { rules: [BY_DOMAIN] };
    openRules(state, { post: () => apiError(409, 'too_many_rules') });

    await heading('Правила');
    await fillCreate('Домен', 'stroymaster.example', 'Ремонт офиса', '');
    press('Создать правило');

    expect(await screen.findByText('Правил не может быть больше 200')).toBeInTheDocument();
    expect(listedRules()).toHaveLength(1);
  });
});

describe('rules page: list', () => {
  it('FR-44 «The order of rules»: the rules show in the order of the answer, whatever their kinds and values', async () => {
    const later = rule(4, 'address', 'a.ivanov@stroymaster.example', OFFICE, null);
    openRules({ rules: [BY_SUBJECT, BY_ADDRESS, BY_DOMAIN, later] });

    await ruleRow('акт работ');
    expect(listedRules()).toEqual([
      'Слова темы: акт работ → Ремонт офиса → Акты',
      'Адрес отправителя: s.petrov@stroymaster.example → Ремонт офиса → Смета',
      'Домен: techsnab.example → Закупка техники → Неразобранное',
      'Адрес отправителя: a.ivanov@stroymaster.example → Ремонт офиса → Неразобранное',
    ]);
  });

  it('FR-44 «No rules»: «Правил пока нет» and the form to create a rule', async () => {
    openRules({ rules: [] });

    expect(await screen.findByText('Правил пока нет')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Создать правило' })).toBeInTheDocument();
    expect(screen.getByLabelText('Условие')).toBeInTheDocument();
    expect(screen.getByLabelText('Значение')).toBeInTheDocument();
    expect(screen.getByLabelText('Проект')).toBeInTheDocument();
    expect(screen.getByLabelText('Ветка')).toHaveAttribute('placeholder', 'Неразобранное');
  });

  it('FR-44: with rules «Правил пока нет» is not shown', async () => {
    openRules({ rules: [BY_DOMAIN] });

    await ruleRow('techsnab.example');
    expect(screen.queryByText('Правил пока нет')).not.toBeInTheDocument();
  });

  it('SPA pages «Правила»: the select «Проект» starts with «Выберите проект» and lists the projects', async () => {
    openRules({ rules: [] });

    await screen.findByRole('option', { name: 'Закупка техники' });
    const select = screen.getByLabelText<HTMLSelectElement>('Проект');
    expect(select.options[0]?.textContent).toBe('Выберите проект');
    expect(select.selectedOptions[0]?.textContent).toBe('Выберите проект');
    expect(within(select).getByRole('option', { name: 'Ремонт офиса' })).toBeInTheDocument();
  });

  it('SPA pages «Правила»: with no projects the form is replaced by «Сначала создайте проект» and the link «Создать проект» to /projects/new', async () => {
    openRules({ rules: [] }, { projects: [] });

    expect(await screen.findByText('Сначала создайте проект')).toBeInTheDocument();
    const link = screen.getByRole('link', { name: 'Создать проект' });
    expect(link).toHaveAttribute('href', '/projects/new');
    expect(screen.queryByRole('button', { name: 'Создать правило' })).not.toBeInTheDocument();
    for (const label of ['Условие', 'Значение', 'Проект', 'Ветка']) {
      expect(screen.queryByLabelText(label)).not.toBeInTheDocument();
    }
  });

  it('FR-17: a signed-out visitor opening /rules sees «Вход»', async () => {
    renderApp({ path: '/rules', routes: { 'GET /rules': () => json(200, []) } });

    await heading('Вход');
  });
});

describe('rules page: edit', () => {
  it('FR-45 «Editing a rule»: «Изменить» opens the form in place, «Сохранить» sends the change and lists «Домен: techsnab.example → Ремонт офиса → Поставки»', async () => {
    const state = { rules: [BY_DOMAIN] };
    const app = openRules(state);

    pressIn(await ruleRow('techsnab.example'), 'Изменить');
    const form = await editForm();
    expect(within(form).getByLabelText('Значение')).toHaveValue('techsnab.example');
    chooseIn(form, 'Проект', 'Ремонт офиса');
    typeIn(form, 'Ветка', 'Поставки');
    pressIn(form, 'Сохранить');

    expect(await ruleRow('techsnab.example')).toHaveTextContent(
      'Домен: techsnab.example → Ремонт офиса → Поставки',
    );
    expect(screen.queryByRole('button', { name: 'Сохранить' })).not.toBeInTheDocument();
    const puts = callsTo(app, 'PUT', `/rules/${BY_DOMAIN.id}`);
    expect(puts).toHaveLength(1);
    expect(puts[0]?.body).toMatchObject({
      condition: 'domain',
      value: 'techsnab.example',
      project_id: OFFICE.id,
      thread_name: 'Поставки',
    });
    expect(writesOtherThan(app, [`PUT /rules/${BY_DOMAIN.id}`])).toEqual([]);
  });

  it('FR-45 «Editing a rule»: «Отмена» closes the form and changes nothing', async () => {
    const app = openRules({ rules: [BY_DOMAIN] });

    pressIn(await ruleRow('techsnab.example'), 'Изменить');
    const form = await editForm();
    typeIn(form, 'Значение', 'other.example');
    pressIn(form, 'Отмена');

    expect(screen.queryByRole('button', { name: 'Сохранить' })).not.toBeInTheDocument();
    expect(await ruleRow('techsnab.example')).toHaveTextContent(
      'Домен: techsnab.example → Закупка техники → Неразобранное',
    );
    expect(callsTo(app, 'PUT', `/rules/${BY_DOMAIN.id}`)).toHaveLength(0);
  });

  it('FR-45 «An edit that repeats another rule»: the form shows «Такое правило уже есть» and the list stays as it was', async () => {
    const second = rule(4, 'domain', 'stroymaster.example', OFFICE, null);
    const app = openRules(
      { rules: [BY_DOMAIN, second] },
      { put: () => apiError(409, 'rule_exists') },
    );

    await ruleRow('techsnab.example');
    const before = listedRules();
    pressIn(await ruleRow('stroymaster.example'), 'Изменить');
    const form = await editForm();
    typeIn(form, 'Значение', 'techsnab.example');
    pressIn(form, 'Сохранить');

    expect(await within(await editForm()).findByText(EXISTS)).toBeInTheDocument();
    const puts = callsTo(app, 'PUT', `/rules/${second.id}`);
    expect(puts).toHaveLength(1);
    expect(puts[0]?.body).toMatchObject({ condition: 'domain', value: 'techsnab.example' });
    expect(callsTo(app, 'PUT', `/rules/${BY_DOMAIN.id}`)).toHaveLength(0);
    pressIn(await editForm(), 'Отмена');
    expect(listedRules()).toEqual(before);
  });

  it('FR-45: a server field error of an edit shows at its field of the form in place', async () => {
    const message = 'Укажите домен, например stroymaster.example';
    openRules(
      { rules: [BY_DOMAIN] },
      { put: () => apiError(422, 'validation_failed', { value: message }) },
    );

    pressIn(await ruleRow('techsnab.example'), 'Изменить');
    const form = await editForm();
    typeIn(form, 'Значение', 'techsnab');
    pressIn(form, 'Сохранить');

    await within(await editForm()).findByText(message);
    expect(fieldOfIn(await editForm(), 'Значение')).toHaveTextContent(message);
  });
});

describe('rules page: delete', () => {
  it('FR-45 «Deleting a rule»: «Удалить» asks first, the confirmation sends the delete and the rule is no longer listed', async () => {
    const state = { rules: [BY_ADDRESS, BY_DOMAIN] };
    const app = openRules(state);

    pressIn(await ruleRow('s.petrov@stroymaster.example'), 'Удалить');
    const confirmation = await confirmationWith(CONFIRM_DELETE);
    expect(callsTo(app, 'DELETE', `/rules/${BY_ADDRESS.id}`)).toHaveLength(0);
    pressIn(confirmation, 'Удалить');

    await waitFor(() => {
      expect(screen.queryByText(/s\.petrov@stroymaster\.example/)).not.toBeInTheDocument();
    });
    expect(callsTo(app, 'DELETE', `/rules/${BY_ADDRESS.id}`)).toHaveLength(1);
    expect(writesOtherThan(app, [`DELETE /rules/${BY_ADDRESS.id}`])).toEqual([]);
    expect(await ruleRow('techsnab.example')).toBeInTheDocument();
    expect(screen.queryByText(CONFIRM_DELETE)).not.toBeInTheDocument();
  });

  it('FR-45 «Deleting cancelled»: «Отмена» closes the confirmation and the rule is still listed', async () => {
    const app = openRules({ rules: [BY_ADDRESS] });

    pressIn(await ruleRow('s.petrov@stroymaster.example'), 'Удалить');
    const confirmation = await confirmationWith(CONFIRM_DELETE);
    pressIn(confirmation, 'Отмена');

    await waitFor(() => {
      expect(screen.queryByText(CONFIRM_DELETE)).not.toBeInTheDocument();
    });
    expect(await ruleRow('s.petrov@stroymaster.example')).toHaveTextContent(
      'Адрес отправителя: s.petrov@stroymaster.example → Ремонт офиса → Смета',
    );
    expect(callsTo(app, 'DELETE', `/rules/${BY_ADDRESS.id}`)).toHaveLength(0);
  });
});
