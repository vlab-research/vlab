import { test as setup, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const authFile = path.join(__dirname, '../playwright/.auth/state.json');

const username = process.env.AUTH0_USERNAME;
const password = process.env.AUTH0_PASSWORD;

function isStateFresh(filePath: string, maxAgeMs: number): boolean {
  try {
    const stats = fs.statSync(filePath);
    return Date.now() - stats.mtimeMs < maxAgeMs;
  } catch {
    return false;
  }
}

const AUTH_STATE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000; // 7 days
const forceSetup = process.env.FORCE_AUTH_SETUP === '1';

setup.skip(
  !forceSetup && isStateFresh(authFile, AUTH_STATE_MAX_AGE_MS),
  'Auth0 state already exists and is fresh. Delete playwright/.auth/state.json or set FORCE_AUTH_SETUP=1 to re-authenticate.'
);

setup('authenticate via Auth0', async ({ page }) => {
  if (!username || !password) {
    throw new Error(
      'AUTH0_USERNAME and AUTH0_PASSWORD must be set. ' +
      'Create a user in the Auth0 dev tenant and export the credentials.'
    );
  }

  // Ensure the auth directory exists
  fs.mkdirSync(path.dirname(authFile), { recursive: true });

  // Dashboard landing page redirects to Auth0.
  await page.goto('/');
  await page.locator('.loginbtn').click();

  // Wait for the Auth0 universal login page.
  await page.waitForURL(/vlab-dev\.us\.auth0\.com/);
  await page.locator('input#username, input[name="username"]').waitFor();
  await page.locator('input#username, input[name="username"]').fill(username);
  await page.locator('input#password, input[name="password"]').fill(password);
  await page.locator('button[value=default], button[type="submit"]').click();

  // Wait for redirect back to the dashboard.
  await page.waitForURL(/https:\/\/localhost:3000\//);
  // The app creates the user on first login; wait for the authenticated header.
  await expect(page.getByTestId('user-avatar')).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId('header')).toContainText('Studies');

  // Save cookies / local storage so other tests skip the login flow.
  await page.context().storageState({ path: authFile });
});
