import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { apiClient } from '../../api/client';
import type { components } from '../../api/generated/schema';

export type HealthResponse = components['schemas']['HealthStatus'];

// How often the page re-reads the state, so a database that goes down shows without a reload.
const REFRESH_INTERVAL_MS = 10_000;

// Reads GET /api/v1/health through the generated client; the query is cached under ['health'].
export function useHealth(): UseQueryResult<HealthResponse> {
  return useQuery({
    queryKey: ['health'],
    queryFn: async (): Promise<HealthResponse> => {
      const { data, error } = await apiClient.GET('/api/v1/health');
      if (data === undefined) {
        throw new Error('The health request failed', { cause: error });
      }
      return data;
    },
    refetchInterval: REFRESH_INTERVAL_MS,
  });
}
