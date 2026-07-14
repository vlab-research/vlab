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
    // Creates playwright/.auth/state.json
    { name: 'setup', testMatch: /auth\.setup\.ts/ },
    // Uses the Auth0 state and creates playwright/.auth/facebook-state.json
    {
      name: 'facebook-setup',
      testMatch: /facebook\.setup\.ts/,
      dependencies: ['setup'],
      use: { storageState: 'playwright/.auth/state.json' },
    },
    // Runs the end-to-end tests using the combined state.
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: process.env.SKIP_FACEBOOK_SETUP
          ? 'playwright/.auth/state.json'
          : 'playwright/.auth/facebook-state.json',
      },
      dependencies: ['facebook-setup'],
    },
  ],

  expect: {
    timeout: 10000,
  },
});
