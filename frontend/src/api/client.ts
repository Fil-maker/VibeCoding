import createClient from 'openapi-fetch';

import type { paths } from './generated/schema';

// The only API client of the SPA: typed from the generated schema, same origin (Vite proxies /api).
// The global fetch is looked up on each call so that tests can replace it.
export const apiClient = createClient<paths>({
  baseUrl: window.location.origin,
  fetch: (request) => globalThis.fetch(request),
});
