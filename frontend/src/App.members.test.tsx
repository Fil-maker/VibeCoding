import { fireEvent, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  ANNA,
  BORIS,
  type Member,
  alertWith,
  apiError,
  callsTo,
  heading,
  json,
  navigate,
  renderApp,
  rowOf,
} from './test/appHarness';
import {
  ANNA_ROW,
  BORIS_ROW,
  DINA_ROW,
  expectRowShows,
  listRoutes,
  openMembers,
} from './test/membersFixtures';

const BORIS_ADMIN: Member = { ...BORIS_ROW, role: 'administrator' };
const SECOND_ADMIN = { ...BORIS, role: 'administrator' } as const;

function follows(first: HTMLElement, second: HTMLElement): boolean {
  return (first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}

describe('members: the list', () => {
  it('FR-13 «The members list»: three rows in name order with email, role and state, none of «Лютик»', async () => {
    await openMembers(
      listRoutes(
        () => [ANNA_ROW, BORIS_ROW, DINA_ROW],
        () => [],
      ),
    );

    const rows = [
      await rowOf('Анна Петрова'),
      await rowOf('Борис Иванов'),
      await rowOf('Дина Орлова'),
    ];
    const expected = [
      ['anna@romashka.test', 'Администратор', 'Активен'],
      ['boris@romashka.test', 'Сотрудник', 'Активен'],
      ['dina@romashka.test', 'Сотрудник', 'Активен'],
    ];
    rows.forEach((row, index) => {
      for (const text of expected[index] ?? []) {
        expect(within(row).getByText(text)).toBeInTheDocument();
      }
    });
    expect(follows(rows[0] ?? document.body, rows[1] ?? document.body)).toBe(true);
    expect(follows(rows[1] ?? document.body, rows[2] ?? document.body)).toBe(true);
    expect(screen.getAllByText(/@/)).toHaveLength(3);
    expect(screen.queryByText(/lyutik|Лютик/i)).not.toBeInTheDocument();
  });

  it('FR-13: a deactivated member is labelled «Отключён»', async () => {
    await openMembers(
      listRoutes(
        () => [ANNA_ROW, { ...DINA_ROW, is_active: false }],
        () => [],
      ),
    );

    const dina = await rowOf('Дина Орлова');
    expect(within(dina).getByText('Отключён')).toBeInTheDocument();
    expect(within(dina).queryByText('Активен')).not.toBeInTheDocument();
  });
});

describe('members: deactivate and reactivate', () => {
  it('FR-14 «Deactivating an employee»: «Отключить» calls the route and the list shows Борис «Отключён»', async () => {
    let members: Member[] = [ANNA_ROW, BORIS_ROW];
    const app = await openMembers({
      ...listRoutes(
        () => members,
        () => [],
      ),
      [`POST /members/${BORIS_ROW.id}/deactivate`]: () => {
        members = [ANNA_ROW, { ...BORIS_ROW, is_active: false }];
        return json(200, members[1]);
      },
    });

    fireEvent.click(within(await rowOf('Борис Иванов')).getByRole('button', { name: 'Отключить' }));

    await expectRowShows('Борис Иванов', 'Отключён');
    expect(callsTo(app, 'POST', `/members/${BORIS_ROW.id}/deactivate`)).toHaveLength(1);
  });

  it('FR-14 «Reactivating»: «Включить» calls the route and Борис shows «Активен»', async () => {
    let members: Member[] = [ANNA_ROW, { ...BORIS_ROW, is_active: false }];
    const app = await openMembers({
      ...listRoutes(
        () => members,
        () => [],
      ),
      [`POST /members/${BORIS_ROW.id}/reactivate`]: () => {
        members = [ANNA_ROW, BORIS_ROW];
        return json(200, BORIS_ROW);
      },
    });

    const boris = await rowOf('Борис Иванов');
    expect(within(boris).queryByRole('button', { name: 'Отключить' })).not.toBeInTheDocument();
    fireEvent.click(within(boris).getByRole('button', { name: 'Включить' }));

    await expectRowShows('Борис Иванов', 'Активен');
    expect(callsTo(app, 'POST', `/members/${BORIS_ROW.id}/reactivate`)).toHaveLength(1);
  });

  it('FR-14 «Deactivating oneself»: shows «Нельзя отключить свою учётную запись», Анна stays «Администратор» and «Активен»', async () => {
    await openMembers({
      ...listRoutes(
        () => [ANNA_ROW, BORIS_ROW],
        () => [],
      ),
      [`POST /members/${ANNA_ROW.id}/deactivate`]: () => apiError(409, 'cannot_deactivate_self'),
    });

    fireEvent.click(within(await rowOf('Анна Петрова')).getByRole('button', { name: 'Отключить' }));

    await alertWith('Нельзя отключить свою учётную запись');
    const anna = await rowOf('Анна Петрова');
    expect(within(anna).getByText('Администратор')).toBeInTheDocument();
    expect(within(anna).getByText('Активен')).toBeInTheDocument();
  });
});

describe('members: roles', () => {
  it('FR-15 «Appointing an administrator»: «Сделать администратором» sends the role and Борис shows «Администратор»', async () => {
    let members: Member[] = [ANNA_ROW, BORIS_ROW];
    const app = await openMembers({
      ...listRoutes(
        () => members,
        () => [],
      ),
      [`PUT /members/${BORIS_ROW.id}/role`]: () => {
        members = [ANNA_ROW, BORIS_ADMIN];
        return json(200, BORIS_ADMIN);
      },
    });

    const boris = await rowOf('Борис Иванов');
    expect(
      within(boris).queryByRole('button', { name: 'Сделать сотрудником' }),
    ).not.toBeInTheDocument();
    fireEvent.click(within(boris).getByRole('button', { name: 'Сделать администратором' }));

    await expectRowShows('Борис Иванов', 'Администратор');
    expect(callsTo(app, 'PUT', `/members/${BORIS_ROW.id}/role`)[0]?.body).toEqual({
      role: 'administrator',
    });
  });

  it('FR-15 «Appointing an administrator»: Борис, now an administrator, sees the list and «Пригласить»', async () => {
    await openMembers(
      listRoutes(
        () => [ANNA_ROW, BORIS_ADMIN],
        () => [],
      ),
      SECOND_ADMIN,
    );

    expect(await rowOf('Анна Петрова')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Пригласить' })).toBeInTheDocument();
  });

  it('FR-15 «Removing the role»: Борис (administrator) makes Анна an employee from her row', async () => {
    let members: Member[] = [ANNA_ROW, BORIS_ADMIN];
    const app = await openMembers(
      {
        ...listRoutes(
          () => members,
          () => [],
        ),
        [`PUT /members/${ANNA_ROW.id}/role`]: () => {
          members = [{ ...ANNA_ROW, role: 'employee' }, BORIS_ADMIN];
          return json(200, members[0]);
        },
      },
      SECOND_ADMIN,
    );

    fireEvent.click(
      within(await rowOf('Анна Петрова')).getByRole('button', { name: 'Сделать сотрудником' }),
    );

    await expectRowShows('Анна Петрова', 'Сотрудник');
    expect(callsTo(app, 'PUT', `/members/${ANNA_ROW.id}/role`)[0]?.body).toEqual({
      role: 'employee',
    });
  });

  it('FR-15 «Removing the role»: Анна, now an employee, has no «Участники» and /members shows «Страница не найдена»', async () => {
    renderApp({ path: '/', me: { ...ANNA, role: 'employee' } });

    await screen.findByText('Анна Петрова');
    expect(screen.queryByText('Участники')).not.toBeInTheDocument();

    navigate('/members');
    await heading('Страница не найдена');
  });

  it('FR-16 «The last administrator removes their own role»: shows the last-administrator message and the role stays', async () => {
    await openMembers({
      ...listRoutes(
        () => [ANNA_ROW, BORIS_ROW],
        () => [],
      ),
      [`PUT /members/${ANNA_ROW.id}/role`]: () => apiError(409, 'last_administrator'),
    });

    fireEvent.click(
      within(await rowOf('Анна Петрова')).getByRole('button', { name: 'Сделать сотрудником' }),
    );

    await alertWith('В организации должен остаться хотя бы один активный администратор');
    expect(within(await rowOf('Анна Петрова')).getByText('Администратор')).toBeInTheDocument();
  });

  it('FR-16 «Two administrators remove each other at once»: a role change answered «not found» shows «Не найдено»', async () => {
    await openMembers({
      ...listRoutes(
        () => [ANNA_ROW, BORIS_ROW],
        () => [],
      ),
      [`PUT /members/${BORIS_ROW.id}/role`]: () => apiError(404, 'not_found'),
    });

    fireEvent.click(
      within(await rowOf('Борис Иванов')).getByRole('button', { name: 'Сделать администратором' }),
    );

    await alertWith('Не найдено');
  });
});
