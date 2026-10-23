// Root component: the only provider is QueryClientProvider; the one query client lives for the whole page.
import { QueryClientProvider } from '@tanstack/react-query';

import { createQueryClient } from './api/queryClient';
import { HealthStatus } from './features/health/HealthStatus';

const queryClient = createQueryClient();

export function App(): React.JSX.Element {
  return (
    <QueryClientProvider client={queryClient}>
      <HealthStatus />
    </QueryClientProvider>
  );
}
