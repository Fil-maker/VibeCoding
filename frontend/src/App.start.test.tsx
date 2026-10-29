import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ANNA, callsTo, heading, navigate, press, renderApp } from './test/appHarness';

describe('start page', () => {
  it('FR-2 «Confirmation by a valid link»: the start page shows «Анна Петрова» and «Выйти» and no organization', async () => {
    renderApp({ path: '/', me: ANNA });

    expect(await screen.findByText('Анна Петрова')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Выйти' })).toBeInTheDocument();
    expect(screen.queryByText('ООО Ромашка')).not.toBeInTheDocument();
    expect(screen.queryByText('Участники')).not.toBeInTheDocument();
  });

  it('FR-6 «Sign-out»: «Выйти» ends the session and the start page shows «Вход»', async () => {
    const app = renderApp({ path: '/', me: ANNA });

    await screen.findByText('Анна Петрова');
    press('Выйти');

    await heading('Вход');
    expect(callsTo(app, 'DELETE', '/auth/sessions/current')).toHaveLength(1);

    navigate('/');
    await heading('Вход');
    expect(screen.queryByRole('button', { name: 'Выйти' })).not.toBeInTheDocument();
  });
});
