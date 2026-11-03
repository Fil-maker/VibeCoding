import { screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { callsTo, heading, press, type Handler } from './test/appHarness';
import {
  CHAIN_A,
  CHAIN_B,
  NOT_PLACED,
  NOTHING,
  PANEL_TITLE,
  appliedAnswer,
  idsOf,
  move,
  moveRoutes,
  movesPath,
  panel,
  placedIn,
  textOf,
  textShown,
  type MoveJson,
} from './test/ruleMoves';
import {
  BY_DOMAIN,
  NEW_RULE_ID,
  OFFICE,
  TECH,
  chooseIn,
  editForm,
  fillCreate,
  openRules,
  pressIn,
  ruleRow,
  typeIn,
  writesOtherThan,
  type RuleJson,
} from './test/rulesPage';

const MONITORS = 'Счёт на мониторы';
const CONTRACT = 'Договор поставки';
const ESTIMATE = { id: 'eeeeeeee-0000-4000-8000-000000000001', name: 'Смета на ремонт офиса' };
const TO_TECH = { project: TECH, thread_name: null };

function open(
  state: { rules: RuleJson[] },
  ruleId: string,
  moves: MoveJson[],
  apply?: Handler,
): ReturnType<typeof openRules> {
  return openRules(state, { extraRoutes: moveRoutes(ruleId, moves, apply) });
}

async function createDomainRule(): Promise<void> {
  await heading('Правила');
  await fillCreate('Домен', 'techsnab.example', 'Закупка техники', '');
  press('Создать правило');
}

describe('rules page: apply a rule now', () => {
  it('FR-47 «A chain in no project»: after «Создать правило» the panel lists «Счёт на мониторы: Вне проектов → Закупка техники → Неразобранное»', async () => {
    const state = { rules: [] as RuleJson[] };
    const app = open(state, NEW_RULE_ID, [move(CHAIN_A, MONITORS, NOT_PLACED, TO_TECH)]);

    await createDomainRule();

    const shown = await panel();
    expect(textOf(shown)).toContain(
      'Счёт на мониторы: Вне проектов → Закупка техники → Неразобранное',
    );
    within(shown).getByRole('button', { name: 'Применить' });
    within(shown).getByRole('button', { name: 'Не сейчас' });
    expect(callsTo(app, 'GET', movesPath(NEW_RULE_ID)).length).toBeGreaterThanOrEqual(1);
    expect(callsTo(app, 'POST', movesPath(NEW_RULE_ID))).toHaveLength(0);
  });

  it('FR-47 «A chain of the engine»: a chain in a thread is listed «<проект> → <ветка> → <проект> → <ветка правила>»', async () => {
    const state = { rules: [] as RuleJson[] };
    open(state, NEW_RULE_ID, [
      move(CHAIN_A, MONITORS, placedIn(OFFICE, ESTIMATE), {
        project: TECH,
        thread_name: 'Мониторы',
      }),
    ]);

    await createDomainRule();

    expect(textOf(await panel())).toContain(
      'Счёт на мониторы: Ремонт офиса → Смета на ремонт офиса → Закупка техники → Мониторы',
    );
  });

  it('FR-47: a chain in «Неразобранное» of a project is listed «<проект> → Неразобранное → …»', async () => {
    const state = { rules: [] as RuleJson[] };
    open(state, NEW_RULE_ID, [move(CHAIN_A, MONITORS, placedIn(OFFICE, null), TO_TECH)]);

    await createDomainRule();

    expect(textOf(await panel())).toContain(
      'Счёт на мониторы: Ремонт офиса → Неразобранное → Закупка техники → Неразобранное',
    );
  });

  it('FR-47 «A chain of the engine»: «Применить» sends exactly the listed ids, then shows «Перемещено цепочек: 2»', async () => {
    const state = { rules: [] as RuleJson[] };
    const app = open(state, NEW_RULE_ID, [
      move(CHAIN_A, MONITORS, NOT_PLACED, TO_TECH),
      move(CHAIN_B, CONTRACT, placedIn(OFFICE, ESTIMATE), TO_TECH),
    ]);

    await createDomainRule();
    pressIn(await panel(), 'Применить');

    await textShown('Перемещено цепочек: 2');
    const posts = callsTo(app, 'POST', movesPath(NEW_RULE_ID));
    expect(posts).toHaveLength(1);
    expect(idsOf(posts[0]?.body)).toEqual([CHAIN_A, CHAIN_B]);
    expect(writesOtherThan(app, ['POST /rules', `POST ${movesPath(NEW_RULE_ID)}`])).toEqual([]);
  });

  it('FR-47 «Changed before «Применить»»: the count shown is the one the server answered, not the listed one', async () => {
    const state = { rules: [] as RuleJson[] };
    open(
      state,
      NEW_RULE_ID,
      [move(CHAIN_A, MONITORS, NOT_PLACED, TO_TECH), move(CHAIN_B, CONTRACT, NOT_PLACED, TO_TECH)],
      () => appliedAnswer(1),
    );

    await createDomainRule();
    pressIn(await panel(), 'Применить');

    await textShown('Перемещено цепочек: 1');
  });

  it('FR-47 «Not now»: «Не сейчас» closes the panel and sends nothing', async () => {
    const state = { rules: [] as RuleJson[] };
    const app = open(state, NEW_RULE_ID, [
      move(CHAIN_A, MONITORS, placedIn(OFFICE, ESTIMATE), TO_TECH),
    ]);

    await createDomainRule();
    pressIn(await panel(), 'Не сейчас');

    await waitFor(() => {
      expect(screen.queryByText(PANEL_TITLE)).not.toBeInTheDocument();
    });
    expect(callsTo(app, 'POST', movesPath(NEW_RULE_ID))).toHaveLength(0);
    expect(writesOtherThan(app, ['POST /rules'])).toEqual([]);
  });

  it('FR-47 «Nothing to move»: with no moves the panel shows «Подходящих цепочек нет» and «Понятно», and no «Применить»', async () => {
    const state = { rules: [] as RuleJson[] };
    const app = open(state, NEW_RULE_ID, []);

    await createDomainRule();

    const shown = await panel(NOTHING);
    expect(within(shown).queryByRole('button', { name: 'Применить' })).not.toBeInTheDocument();
    pressIn(shown, 'Понятно');
    await waitFor(() => {
      expect(screen.queryByText(NOTHING)).not.toBeInTheDocument();
    });
    expect(callsTo(app, 'POST', movesPath(NEW_RULE_ID))).toHaveLength(0);
  });

  it('FR-47 (Interface «While a request runs, the buttons are disabled»): «Применить» and «Не сейчас» are enabled before the press and disabled while the apply request runs', async () => {
    const state = { rules: [] as RuleJson[] };
    const pending = new Promise<Response>(() => undefined);
    const app = open(
      state,
      NEW_RULE_ID,
      [move(CHAIN_A, MONITORS, NOT_PLACED, TO_TECH)],
      () => pending,
    );

    await createDomainRule();
    const shown = await panel();
    expect(within(shown).getByRole('button', { name: 'Применить' })).toBeEnabled();
    expect(within(shown).getByRole('button', { name: 'Не сейчас' })).toBeEnabled();
    pressIn(shown, 'Применить');

    await waitFor(() => {
      expect(within(shown).getByRole('button', { name: 'Применить' })).toBeDisabled();
    });
    expect(within(shown).getByRole('button', { name: 'Не сейчас' })).toBeDisabled();
    expect(callsTo(app, 'POST', movesPath(NEW_RULE_ID))).toHaveLength(1);
  });

  it('FR-45 «Editing a rule»: after «Сохранить» the page offers to apply the edited rule and «Применить» sends its ids', async () => {
    const state = { rules: [BY_DOMAIN] };
    const to = { project: OFFICE, thread_name: 'Поставки' };
    const app = open(state, BY_DOMAIN.id, [
      move(CHAIN_A, MONITORS, placedIn(TECH, null), to),
      move(CHAIN_B, CONTRACT, placedIn(TECH, null), to),
    ]);

    pressIn(await ruleRow('techsnab.example'), 'Изменить');
    const form = await editForm();
    chooseIn(form, 'Проект', 'Ремонт офиса');
    typeIn(form, 'Ветка', 'Поставки');
    pressIn(form, 'Сохранить');

    const shown = await panel();
    const text = textOf(shown);
    expect(text).toContain(
      'Счёт на мониторы: Закупка техники → Неразобранное → Ремонт офиса → Поставки',
    );
    expect(text).toContain(
      'Договор поставки: Закупка техники → Неразобранное → Ремонт офиса → Поставки',
    );
    expect(callsTo(app, 'GET', movesPath(BY_DOMAIN.id)).length).toBeGreaterThanOrEqual(1);
    const puts = callsTo(app, 'PUT', `/rules/${BY_DOMAIN.id}`);
    expect(puts).toHaveLength(1);
    expect(puts[0]?.body).toMatchObject({ project_id: OFFICE.id, thread_name: 'Поставки' });
    expect(callsTo(app, 'POST', movesPath(BY_DOMAIN.id))).toHaveLength(0);

    pressIn(shown, 'Применить');
    await textShown('Перемещено цепочек: 2');
    expect(idsOf(callsTo(app, 'POST', movesPath(BY_DOMAIN.id))[0]?.body)).toEqual([
      CHAIN_A,
      CHAIN_B,
    ]);
  });

  it('FR-47 (after editing): after «Сохранить» with nothing to move the panel shows «Подходящих цепочек нет» and «Понятно», no «Применить» and sends no apply', async () => {
    const state = { rules: [BY_DOMAIN] };
    const app = open(state, BY_DOMAIN.id, []);

    pressIn(await ruleRow('techsnab.example'), 'Изменить');
    pressIn(await editForm(), 'Сохранить');

    const shown = await panel(NOTHING);
    within(shown).getByRole('button', { name: 'Понятно' });
    expect(within(shown).queryByRole('button', { name: 'Применить' })).not.toBeInTheDocument();
    expect(callsTo(app, 'POST', movesPath(BY_DOMAIN.id))).toHaveLength(0);
  });
});
