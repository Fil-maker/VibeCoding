import { QueryClient } from '@tanstack/react-query';

// One retry: a missing backend is reported within seconds instead of after the default backoff.
const QUERY_RETRIES = 1;

export function createQueryClient(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: QUERY_RETRIES } } });
}
