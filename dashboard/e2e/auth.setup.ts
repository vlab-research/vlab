import { test as setup, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const authFile = path.join(__dirname, '../playwright/.auth/state.json');

const username = process.env.AUTH0_USERNAME;
const password = process.env.AUTH0_PASSWORD;

setup('authenticate via Auth0', async ({ page, baseURL }) => {
  if (!username || !password) {
    throw new Error(
      'AUTH0_USERNAME and AUTH0_PASSWORD must be set. ' +
      'Create a user in the Auth0 dev tenant and export the credentials.'
    );
  }

  // Ensure the auth directory exists
  fs.mkdirSync(path.dirname(authFile), { recursive: true });

  await page.goto(`${baseURL}/login`);

  // The Auth0 React SDK redirects to the universal login page.
  // Wait for the login form and fill it.
  await page.waitForSelector('input[name="username"], input[name="email"], input[name="password"]', {
    timeout: 10000,
  });

  const emailField = page.locator('input[name="username"], input[name="email"]').first();
  const passwordField = page.locator('input[name="password"]').first();

  await emailField.fill(username);
  await passwordField.fill(password);
  await page.locator('button[type="submit"]').first().click();

  // Wait for the dashboard to load after redirect.
  await expect(page).toHaveURL(/studies/);
  await expect(page.locator('text=Studies')).toBeVisible();

  // Save cookies / local storage so other tests skip the login flow.
  await page.context().storageState({ path: authFile });
});
