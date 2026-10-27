import { fireEvent, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  type Invitation,
  alertWith,
  apiError,
  callsTo,
  json,
  press,
  rowOf,
  type,
} from './test/appHarness';
import {
  ANNA_ROW,
  expectRowShows,
  invitation,
  listRoutes,
  openMembers,
} from './test/membersFixtures';

const BORIS_MAIL = 'boris@romashka.test';
const OPEN_BORIS = invitation('i-boris', BORIS_MAIL, 'sent');

describe('members: invitation statuses', () => {
  it('FR-10: each invitation shows its status label', async () => {
    await openMembers(
      listRoutes(
        () => [ANNA_ROW],
        () => [
          invitation('i-1', 'sent@romashka.test', 'sent'),
          invitation('i-2', 'notsent@romashka.test', 'not_sent'),
          invitation('i-3', 'accepted@romashka.test', 'accepted'),
          invitation('i-4', 'revoked@romashka.test', 'revoked'),
          invitation('i-5', 'expired@romashka.test', 'expired'),
        ],
      ),
    );

    const expected: [string, string][] = [
      ['sent@romashka.test', 'Отправлено'],
      ['notsent@romashka.test', 'Не отправлено'],
      ['accepted@romashka.test', 'Принято'],
      ['revoked@romashka.test', 'Отозвано'],
      ['expired@romashka.test', 'Истекло'],
    ];
    for (const [email, label] of expected) {
      expect(within(await rowOf(email)).getByText(label)).toBeInTheDocument();
    }
  });

  it('FR-10 «Resending»: «Отправить ещё раз» and «Отозвать» are offered for open invitations', async () => {
    await openMembers(
      listRoutes(
        () => [ANNA_ROW],
        () => [
          invitation('i-1', 'sent@romashka.test', 'sent'),
          invitation('i-2', 'notsent@romashka.test', 'not_sent'),
        ],
      ),
    );

    for (const email of ['sent@romashka.test', 'notsent@romashka.test']) {
      const row = await rowOf(email);
      expect(within(row).getByRole('button', { name: 'Отправить ещё раз' })).toBeInTheDocument();
      expect(within(row).getByRole('button', { name: 'Отозвать' })).toBeInTheDocument();
    }
  });

  it('FR-10 «An expired invitation»: the «Истекло» row offers no «Отправить ещё раз»', async () => {
    await openMembers(
      listRoutes(
        () => [ANNA_ROW],
        () => [invitation('i-5', BORIS_MAIL, 'expired')],
      ),
    );

    const row = await rowOf(BORIS_MAIL);
    expect(within(row).getByText('Истекло')).toBeInTheDocument();
    expect(
      within(row).queryByRole('button', { name: 'Отправить ещё раз' }),
    ).not.toBeInTheDocument();
  });

  it('FR-11 «Revoking an accepted invitation»: the «Принято» row stays and offers no «Отозвать»', async () => {
    await openMembers(
      listRoutes(
        () => [ANNA_ROW],
        () => [invitation('i-3', BORIS_MAIL, 'accepted')],
      ),
    );

    const row = await rowOf(BORIS_MAIL);
    expect(within(row).getByText('Принято')).toBeInTheDocument();
    expect(within(row).queryByRole('button', { name: 'Отозвать' })).not.toBeInTheDocument();
  });

  it('FR-11: a revoked invitation offers neither «Отправить ещё раз» nor «Отозвать»', async () => {
    await openMembers(
      listRoutes(
        () => [ANNA_ROW],
        () => [invitation('i-4', BORIS_MAIL, 'revoked')],
      ),
    );

    const row = await rowOf(BORIS_MAIL);
    expect(within(row).getByText('Отозвано')).toBeInTheDocument();
    expect(
      within(row).queryByRole('button', { name: 'Отправить ещё раз' }),
    ).not.toBeInTheDocument();
    expect(within(row).queryByRole('button', { name: 'Отозвать' })).not.toBeInTheDocument();
  });
});

describe('members: inviting', () => {
  it('FR-9 «Successful invitation»: «Пригласить» posts the email and the list shows «Отправлено»', async () => {
    let list: Invitation[] = [];
    const app = await openMembers({
      'GET /members': () => json(200, { items: [ANNA_ROW], next_cursor: null }),
      'GET /invitations': () => json(200, { items: list, next_cursor: null }),
      'POST /invitations': () => {
        list = [OPEN_BORIS];
        return json(201, OPEN_BORIS);
      },
    });

    type('Email', BORIS_MAIL);
    press('Пригласить');

    await expectRowShows(BORIS_MAIL, 'Отправлено');
    expect(callsTo(app, 'POST', '/invitations')[0]?.body).toEqual({ email: BORIS_MAIL });
  });

  it('FR-10 «The mail server is unavailable»: shows «Не отправлено» and the mail-failure text', async () => {
    const notSent = invitation('i-boris', BORIS_MAIL, 'not_sent');
    let list: Invitation[] = [];
    await openMembers({
      'GET /members': () => json(200, { items: [ANNA_ROW], next_cursor: null }),
      'GET /invitations': () => json(200, { items: list, next_cursor: null }),
      'POST /invitations': () => {
        list = [notSent];
        return json(201, notSent);
      },
    });

    type('Email', BORIS_MAIL);
    press('Пригласить');

    expect(
      await screen.findByText('Не удалось отправить письмо. Попробуйте отправить ещё раз'),
    ).toBeInTheDocument();
    await expectRowShows(BORIS_MAIL, 'Не отправлено');
  });

  it('FR-9 «The email is already a user»: shows «Этот email уже зарегистрирован» and the rows stay', async () => {
    await openMembers({
      ...listRoutes(
        () => [ANNA_ROW],
        () => [OPEN_BORIS],
      ),
      'POST /invitations': () => apiError(409, 'email_taken'),
    });

    await rowOf(BORIS_MAIL);
    type('Email', 'vera@lyutik.test');
    press('Пригласить');

    await alertWith('Этот email уже зарегистрирован');
    expect(screen.getAllByText(BORIS_MAIL)).toHaveLength(1);
    expect(screen.queryByText('vera@lyutik.test')).not.toBeInTheDocument();
  });

  it('FR-9 «A repeated invitation»: shows «Приглашение на этот email уже отправлено» and no second row', async () => {
    await openMembers({
      ...listRoutes(
        () => [ANNA_ROW],
        () => [OPEN_BORIS],
      ),
      'POST /invitations': () => apiError(409, 'invitation_exists'),
    });

    await rowOf(BORIS_MAIL);
    type('Email', BORIS_MAIL);
    press('Пригласить');

    await alertWith('Приглашение на этот email уже отправлено');
    expect(screen.getAllByText(BORIS_MAIL)).toHaveLength(1);
  });
});

describe('members: resend and revoke', () => {
  it('FR-10 «Resending»: «Отправить ещё раз» calls the resend route and the status becomes «Отправлено»', async () => {
    let list: Invitation[] = [invitation('i-boris', BORIS_MAIL, 'not_sent')];
    const app = await openMembers({
      ...listRoutes(
        () => [ANNA_ROW],
        () => list,
      ),
      'POST /invitations/i-boris/resend': () => {
        list = [OPEN_BORIS];
        return json(200, OPEN_BORIS);
      },
    });

    fireEvent.click(
      within(await rowOf(BORIS_MAIL)).getByRole('button', { name: 'Отправить ещё раз' }),
    );

    await expectRowShows(BORIS_MAIL, 'Отправлено');
    expect(callsTo(app, 'POST', '/invitations/i-boris/resend')).toHaveLength(1);
  });

  it('FR-11 «Revoking»: «Отозвать» calls the revoke route and the status becomes «Отозвано»', async () => {
    let list: Invitation[] = [OPEN_BORIS];
    const app = await openMembers({
      ...listRoutes(
        () => [ANNA_ROW],
        () => list,
      ),
      'POST /invitations/i-boris/revoke': () => {
        list = [invitation('i-boris', BORIS_MAIL, 'revoked')];
        return json(200, list[0]);
      },
    });

    fireEvent.click(within(await rowOf(BORIS_MAIL)).getByRole('button', { name: 'Отозвать' }));

    await expectRowShows(BORIS_MAIL, 'Отозвано');
    expect(callsTo(app, 'POST', '/invitations/i-boris/revoke')).toHaveLength(1);
  });
});
