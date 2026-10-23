import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { HealthStatus } from './HealthStatus';

// Tests of the health page. fetch is stubbed, so no backend runs.
function renderHealthStatus(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <HealthStatus />
    </QueryClientProvider>,
  );
}

function stubFetch(answer: () => Promise<Response>): void {
  vi.stubGlobal('fetch', vi.fn(answer));
}

function answerWith(body: unknown): void {
  stubFetch(() => Promise.resolve(Response.json(body)));
}

describe('HealthStatus', () => {
  it('shows the heading and the loading text while the request is pending', () => {
    stubFetch(() => new Promise<Response>(() => undefined));
    renderHealthStatus();

    expect(screen.getByRole('heading', { name: 'Состояние сервиса' })).toBeInTheDocument();
    expect(screen.getByText('Проверяем…')).toBeInTheDocument();
  });

  it('shows a working server and an available database', async () => {
    answerWith({ status: 'ok', database: 'ok' });
    renderHealthStatus();

    expect(await screen.findByText('Сервер: работает')).toBeInTheDocument();
    expect(screen.getByText('База данных: доступна')).toBeInTheDocument();
    expect(screen.queryByText('Проверяем…')).not.toBeInTheDocument();
  });

  it('shows a working server and an unavailable database', async () => {
    answerWith({ status: 'ok', database: 'unavailable' });
    renderHealthStatus();

    expect(await screen.findByText('Сервер: работает')).toBeInTheDocument();
    expect(screen.getByText('База данных: недоступна')).toBeInTheDocument();
  });

  it('shows that the server does not answer when the request fails', async () => {
    stubFetch(() => Promise.reject(new TypeError('Failed to fetch')));
    renderHealthStatus();

    expect(await screen.findByText('Сервер не отвечает')).toBeInTheDocument();
    expect(screen.queryByText('Сервер: работает')).not.toBeInTheDocument();
  });

  it('shows that the server does not answer on an error status', async () => {
    stubFetch(() => Promise.resolve(new Response('bad gateway', { status: 502 })));
    renderHealthStatus();

    expect(await screen.findByText('Сервер не отвечает')).toBeInTheDocument();
  });
});
