import { test as setup, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const facebookAuthFile = path.join(__dirname, '../playwright/.auth/facebook-state.json');

/**
 * Facebook connection setup.
 *
 * Run this once before the variables/strata tests if the test Auth0 user does not
 * already have a Facebook account connected.
 *
 * If FACEBOOK_USERNAME and FACEBOOK_PASSWORD are set, the OAuth flow is automated.
 * Otherwise, the test pauses for manual authentication.
 */
const facebookUsername = process.env.FACEBOOK_USERNAME;
const facebookPassword = process.env.FACEBOOK_PASSWORD;

setup('connect Facebook account', async ({ page }) => {
  fs.mkdirSync(path.dirname(facebookAuthFile), { recursive: true });

  // Reuse the Auth0 login state.
  const authStateFile = path.join(__dirname, '../playwright/.auth/state.json');
  if (!fs.existsSync(authStateFile)) {
    throw new Error('Auth0 state not found. Run `npx playwright test e2e/auth.setup.ts` first.');
  }

  await page.goto('/accounts');
  await expect(page.getByText('Connected Accounts')).toBeVisible();

  // Click the new-account button.
  await page.getByTestId('new-account-button').click();

  // Select Facebook from the modal.
  await page.locator('select[name="authType"]').selectOption('facebook');

  // Click Connect and wait for Facebook OAuth redirect.
  await page.getByRole('button', { name: /connect/i }).click();
  await page.waitForURL(/facebook\.com/);

  if (facebookUsername && facebookPassword) {
    await page.locator('input[name="email"]').fill(facebookUsername);
    await page.locator('input[name="pass"]').fill(facebookPassword);
    await page.locator('button[name="login"]').click();

    // Accept any permissions prompt if it appears.
    const continueButton = page.locator('button[name="__CONFIRM__"], [role="button"]:has-text("Continue")');
    if (await continueButton.isVisible().catch(() => false)) {
      await continueButton.click();
    }
  } else {
    // Pause for manual authentication. The user can log in and approve the app.
    await page.pause();
  }

  // Wait for redirect back to the dashboard with a connected Facebook account.
  await page.waitForURL(/\/accounts\?type=facebook/);
  await expect(page.getByText('Facebook')).toBeVisible();

  // Save the combined state (Auth0 + Facebook cookies).
  await page.context().storageState({ path: facebookAuthFile });
});
