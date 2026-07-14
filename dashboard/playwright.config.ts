import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for local end-to-end testing of the VLAB dashboard.
 *
 * Assumes:
 *   - API dev server is running at http://localhost:8080 (see api/Makefile)
 *   - Dashboard dev server is running at https://localhost:3000 (npm start)
 *   - HTTPS cert is self-signed (ignoreHTTPSErrors is enabled)
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'https://localhost:3000',
    ignoreHTTPSErrors: true,
    trace: 'on-first-retry',
    video: 'on-first-retry',
  },

  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: process.env.SKIP_FACEBOOK_SETUP
          ? 'playwright/.auth/state.json'
          : 'playwright/.auth/facebook-state.json',
      },
      dependencies: ['setup'],
    },
  ],

  expect: {
    timeout: 10000,
  },
});
