import { defineConfig, devices } from '@playwright/test';

// O Chromium vem de PLAYWRIGHT_BROWSERS_PATH (no CI, de `playwright install`); nada é baixado aqui.
export default defineConfig({
  testDir: 'tests/e2e',
  timeout: 60_000,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: [['list']],
  use: {
    ...devices['Pixel 7'],
    baseURL: 'http://127.0.0.1:4173',
    serviceWorkers: 'block',
  },
  webServer: {
    command: 'npx vite build && npx vite preview',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
