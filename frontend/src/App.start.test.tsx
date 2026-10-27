import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ANNA, BORIS, callsTo, heading, navigate, press, renderApp } from './test/appHarness';

describe('start page', () => {
  it('SPA pages «/»: the administrator sees name, organization, «Участники» and «Выйти»', async () => {
    renderApp({ path: '/', me: ANNA });

    expect(await screen.findByText('Анна Петрова')).toBeInTheDocument();
    expect(screen.getByText('ООО Ромашка')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Участники' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Выйти' })).toBeInTheDocument();
  });

  it('FR-19 «An employee opens the members page»: the employee start page has name, organization, «Выйти» and no «Участники»', async () => {
    renderApp({ path: '/', me: BORIS });

    expect(await screen.findByText('Борис Иванов')).toBeInTheDocument();
    expect(screen.getByText('ООО Ромашка')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Выйти' })).toBeInTheDocument();
    expect(screen.queryByText('Участники')).not.toBeInTheDocument();
  });

  it('FR-6 «Sign-out»: «Выйти» ends the session and opening «Участники» shows «Вход»', async () => {
    const app = renderApp({ path: '/', me: ANNA });

    await screen.findByText('Анна Петрова');
    press('Выйти');

    await heading('Вход');
    expect(callsTo(app, 'DELETE', '/auth/sessions/current')).toHaveLength(1);

    navigate('/members');
    await heading('Вход');
    expect(screen.queryByRole('heading', { level: 1, name: 'Участники' })).not.toBeInTheDocument();
  });
});
