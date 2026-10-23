import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// Setup file of Vitest (setupFiles in vite.config.ts). Vitest globals are off, so Testing Library
// does not unmount between tests by itself.
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
