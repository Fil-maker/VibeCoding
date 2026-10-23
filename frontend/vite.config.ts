import react from '@vitejs/plugin-react';
import { loadEnv } from 'vite';
import { defineConfig } from 'vitest/config';

const DEFAULT_PROXY_TARGET = 'http://localhost:8000';

// Vite requires a default export for its config.
export default defineConfig(({ mode }) => {
  // Tooling reads its own variables here, not the app: the compose service sets both.
  const env = loadEnv(mode, process.cwd(), ['VITE_', 'CHOKIDAR_']);
  return {
    plugins: [react()],
    server: {
      proxy: { '/api': { target: env.VITE_PROXY_TARGET ?? DEFAULT_PROXY_TARGET } },
      // File events do not cross the Windows bind mount of the container.
      watch: { usePolling: env.CHOKIDAR_USEPOLLING === 'true' },
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      include: ['src/**/*.test.{ts,tsx}'],
    },
  };
});
