import { screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { callsTo, fieldOf, press, type } from './test/appHarness';
import {
  ENGINE_PLACEMENT,
  ESTIMATE_THREAD,
  EXCLUDED,
  MANUAL_PLACEMENT,
  MONITORS_THREAD,
  NONE,
  OFFICE,
  PLACEMENT,
  TECH,
  choose,
  locationAround,
  openChain,
  placed,
  rejectedName,
  type ChainState,
} from './test/chainPlacement';

// Dates are shown in the machine's time zone; the tests pin it to UTC so the day never shifts.
process.env.TZ = 'UTC';

const TOO_LONG = 'Название ветки — не длиннее 100 символов';
const EMPTY_NAME = 'Укажите название ветки';

describe('chain page: where the chain is', () => {
  it('FR-37 «A chain placed by the engine»: a chain of the engine shows «<project> → <thread> · Движок <version> · сходство <N>%»', async () => {
    openChain({
      subject: 'Смета на ремонт офиса',
      location: placed(OFFICE, ESTIMATE_THREAD, ENGINE_PLACEMENT),
    });

    const block = await locationAround('Ремонт офиса');
    expect(block).toHaveTextContent(
      'Ремонт офиса → Смета на ремонт офиса · Движок text-1 · сходство 43%',
    );
  });

  it('FR-40: the project name links to the project page', async () => {
    openChain({
      subject: 'Смета на ремонт офиса',
      location: placed(OFFICE, ESTIMATE_THREAD, ENGINE_PLACEMENT),
    });

    expect(await screen.findByRole('link', { name: 'Ремонт офиса' })).toHaveAttribute(
      'href',
      `/projects/${OFFICE.id}`,
    );
  });

  it('FR-37 «A chain placed by hand»: a chain by hand in «Неразобранное» shows «<project> → Неразобранное · Вручную»', async () => {
    openChain({
      subject: 'Выбор дизайна переговорной',
      location: placed(OFFICE, null, MANUAL_PLACEMENT),
    });

    const block = await locationAround('Ремонт офиса');
    expect(block).toHaveTextContent('Ремонт офиса → Неразобранное · Вручную');
    expect(block).not.toHaveTextContent('Движок');
    expect(block).not.toHaveTextContent('сходство');
  });

  it('FR-37 «An unsure chain»: «Неразобранное» of the engine shows «Движок text-1 · сходство 20%»', async () => {
    openChain({
      subject: 'Выбор дизайна переговорной',
      location: placed(OFFICE, null, {
        kind: 'engine',
        engine_version: 'text-1',
        similarity: 0.195,
      }),
    });

    expect(await locationAround('Ремонт офиса')).toHaveTextContent(
      'Ремонт офиса → Неразобранное · Движок text-1 · сходство 20%',
    );
  });

  it('FR-40: a chain of no project shows «Вне проектов» and no «Убрать из проекта»', async () => {
    openChain({ subject: 'Выбор дизайна переговорной', location: NONE });

    expect(await screen.findByText('Вне проектов')).toBeInTheDocument();
    expect(screen.queryByText(/убрана вручную/)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Убрать из проекта' })).not.toBeInTheDocument();
  });

  it('FR-41 «Taking a chain out»: a chain taken out shows «Вне проектов · убрана вручную» and no «Убрать из проекта»', async () => {
    openChain({ subject: 'Скидка на абонемент в фитнес-клуб', location: EXCLUDED });

    expect(await screen.findByText('Вне проектов · убрана вручную')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Убрать из проекта' })).not.toBeInTheDocument();
  });

  it('FR-41: a placed chain offers «Убрать из проекта»', async () => {
    openChain({
      subject: 'Скидка на абонемент в фитнес-клуб',
      location: placed(OFFICE, null, ENGINE_PLACEMENT),
    });

    expect(await screen.findByRole('button', { name: 'Убрать из проекта' })).toBeInTheDocument();
  });
});

describe('chain page: «Перенести»', () => {
  it('FR-40 «Moving a chain to another project»: into a thread of another project sends the move and shows «Закупка техники → Закупка мониторов · Вручную»', async () => {
    const state: ChainState = {
      subject: 'Акт скрытых работ',
      location: placed(OFFICE, ESTIMATE_THREAD, ENGINE_PLACEMENT),
    };
    const app = openChain(state);

    await locationAround('Ремонт офиса');
    await choose('Проект', 'Закупка техники');
    await choose('Ветка', 'Закупка мониторов');
    press('Перенести');

    const block = await locationAround('Закупка техники');
    expect(block).toHaveTextContent('Закупка техники → Закупка мониторов · Вручную');
    expect(screen.queryByRole('link', { name: 'Ремонт офиса' })).not.toBeInTheDocument();
    const puts = callsTo(app, 'PUT', PLACEMENT);
    expect(puts).toHaveLength(1);
    expect(puts[0]?.body).toEqual({
      project_id: TECH.id,
      thread_id: MONITORS_THREAD.id,
      new_thread_name: null,
    });
  });

  it('FR-40 «Placing a chain of no project»: into «Неразобранное» sends no thread and shows «Ремонт офиса → Неразобранное · Вручную»', async () => {
    const app = openChain({ subject: 'Выбор дизайна переговорной', location: NONE });

    await screen.findByText('Вне проектов');
    await choose('Проект', 'Ремонт офиса');
    await choose('Ветка', 'Неразобранное');
    press('Перенести');

    const block = await locationAround('Ремонт офиса');
    expect(block).toHaveTextContent('Ремонт офиса → Неразобранное · Вручную');
    const puts = callsTo(app, 'PUT', PLACEMENT);
    expect(puts).toHaveLength(1);
    expect(puts[0]?.body).toEqual({
      project_id: OFFICE.id,
      thread_id: null,
      new_thread_name: null,
    });
  });

  it('FR-40 «A new thread»: «Новая ветка…» with a «Название ветки» sends the name and shows the new thread', async () => {
    const app = openChain({
      subject: 'Акт скрытых работ',
      location: placed(OFFICE, ESTIMATE_THREAD, ENGINE_PLACEMENT),
    });

    await locationAround('Ремонт офиса');
    await choose('Проект', 'Ремонт офиса');
    await choose('Ветка', 'Новая ветка…');
    type('Название ветки', 'Акты');
    press('Перенести');

    await waitFor(() => {
      expect(screen.getByRole('link', { name: 'Ремонт офиса' }).parentElement).toHaveTextContent(
        'Ремонт офиса → Акты · Вручную',
      );
    });
    const puts = callsTo(app, 'PUT', PLACEMENT);
    expect(puts).toHaveLength(1);
    expect(puts[0]?.body).toEqual({
      project_id: OFFICE.id,
      thread_id: null,
      new_thread_name: 'Акты',
    });
  });

  it("FR-40 «Pinning the engine's place»: moving into the same thread shows «Вручную» in it", async () => {
    const app = openChain({
      subject: 'Смета на ремонт офиса',
      location: placed(OFFICE, ESTIMATE_THREAD, ENGINE_PLACEMENT),
    });

    await locationAround('Ремонт офиса');
    await choose('Проект', 'Ремонт офиса');
    await choose('Ветка', 'Смета на ремонт офиса');
    press('Перенести');

    await waitFor(() => {
      expect(screen.getByRole('link', { name: 'Ремонт офиса' }).parentElement).toHaveTextContent(
        'Ремонт офиса → Смета на ремонт офиса · Вручную',
      );
    });
    expect(callsTo(app, 'PUT', PLACEMENT)[0]?.body).toEqual({
      project_id: OFFICE.id,
      thread_id: ESTIMATE_THREAD.id,
      new_thread_name: null,
    });
  });

  it("FR-40: «Ветка» starts at the chain's current thread and resets to «Неразобранное» for another project", async () => {
    const app = openChain({
      subject: 'Смета на ремонт офиса',
      location: placed(OFFICE, ESTIMATE_THREAD, ENGINE_PLACEMENT),
    });

    await locationAround('Ремонт офиса');
    const select = screen.getByLabelText<HTMLSelectElement>('Ветка');
    await waitFor(() => {
      expect(select.selectedOptions[0]?.textContent).toBe('Смета на ремонт офиса');
    });
    await choose('Проект', 'Закупка техники');
    expect(select.selectedOptions[0]?.textContent).toBe('Неразобранное');
    expect(callsTo(app, 'PUT', PLACEMENT)).toHaveLength(0);
  });

  it('FR-40: the field «Название ветки» is there only for «Новая ветка…»', async () => {
    openChain({
      subject: 'Смета на ремонт офиса',
      location: placed(OFFICE, ESTIMATE_THREAD, ENGINE_PLACEMENT),
    });

    await locationAround('Ремонт офиса');
    await choose('Проект', 'Ремонт офиса');
    await choose('Ветка', 'Смета на ремонт офиса');
    expect(screen.queryByLabelText('Название ветки')).not.toBeInTheDocument();
    await choose('Ветка', 'Новая ветка…');
    expect(screen.getByLabelText('Название ветки')).toBeInTheDocument();
  });

  it.each([
    ['   ', EMPTY_NAME],
    ['я'.repeat(101), TOO_LONG],
  ])(
    'FR-40 «An empty or too long thread name»: a name of %j fails with «%s» on the form and the location stays',
    async (name, message) => {
      const state: ChainState = {
        subject: 'Акт скрытых работ',
        location: placed(OFFICE, ESTIMATE_THREAD, ENGINE_PLACEMENT),
      };
      openChain(state, { put: rejectedName(message) });

      await locationAround('Ремонт офиса');
      await choose('Проект', 'Ремонт офиса');
      await choose('Ветка', 'Новая ветка…');
      type('Название ветки', name);
      press('Перенести');

      expect(await within(fieldOf('Название ветки')).findByText(message)).toBeInTheDocument();
      expect(screen.getByRole('link', { name: 'Ремонт офиса' }).parentElement).toHaveTextContent(
        'Ремонт офиса → Смета на ремонт офиса · Движок text-1 · сходство 43%',
      );
    },
  );
});

describe('chain page: «Убрать из проекта»', () => {
  it('FR-41 «Taking a chain out»: pressing it sends DELETE and shows «Вне проектов · убрана вручную»', async () => {
    const app = openChain({
      subject: 'Скидка на абонемент в фитнес-клуб',
      location: placed(OFFICE, null, ENGINE_PLACEMENT),
    });

    await locationAround('Ремонт офиса');
    press('Убрать из проекта');

    expect(await screen.findByText('Вне проектов · убрана вручную')).toBeInTheDocument();
    expect(callsTo(app, 'DELETE', PLACEMENT)).toHaveLength(1);
    expect(screen.queryByRole('link', { name: 'Ремонт офиса' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Убрать из проекта' })).not.toBeInTheDocument();
  });

  it('FR-41 «Placing it back by hand»: a taken-out chain moved into «Неразобранное» shows «Вручную»', async () => {
    openChain({ subject: 'Скидка на абонемент в фитнес-клуб', location: EXCLUDED });

    await screen.findByText('Вне проектов · убрана вручную');
    await choose('Проект', 'Ремонт офиса');
    await choose('Ветка', 'Неразобранное');
    press('Перенести');

    expect(await locationAround('Ремонт офиса')).toHaveTextContent(
      'Ремонт офиса → Неразобранное · Вручную',
    );
    expect(screen.queryByText(/убрана вручную/)).not.toBeInTheDocument();
  });
});
