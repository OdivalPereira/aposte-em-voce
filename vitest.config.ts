import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/unit/**/*.test.ts', 'tests/leitura/**/*.test.ts'],
    testTimeout: 30000,
  },
});
