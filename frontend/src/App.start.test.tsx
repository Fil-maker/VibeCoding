import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ANNA, START_DATA, callsTo, heading, navigate, press, renderApp } from './test/appHarness';

describe('start page', () => {
  it('FR-2 «Confirmation by a valid link»: the page shows «Анна Петрова» and «Выйти» in the header and no organization', async () => {
    renderApp({ path: '/', me: ANNA, routes: START_DATA });

    await screen.findByText('Анна Петрова');
    const header = within(screen.getByRole('banner'));
    expect(header.getByText('Анна Петрова')).toBeInTheDocument();
    expect(header.getByRole('button', { name: 'Выйти' })).toBeInTheDocument();
    expect(screen.queryByText('ООО Ромашка')).not.toBeInTheDocument();
    expect(screen.queryByText('Участники')).not.toBeInTheDocument();
  });

  it('FR-6 «Sign-out»: «Выйти» ends the session, «/» shows the landing page and «Проекты» then shows «Вход»', async () => {
    const app = renderApp({ path: '/', me: ANNA, routes: START_DATA });

    await screen.findByText('Анна Петрова');
    press('Выйти');

    await heading('Переписка по проектам — в одном дереве');
    expect(callsTo(app, 'DELETE', '/auth/sessions/current')).toHaveLength(1);

    navigate('/projects');
    await heading('Вход');
    expect(screen.queryByRole('button', { name: 'Выйти' })).not.toBeInTheDocument();
  });
});
