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
 * Otherwise, the test waits for the user to authenticate in the browser window.
 *
 * The resulting state is reused for subsequent runs. Delete the state file or set
 * FORCE_FACEBOOK_SETUP=1 to re-authenticate.
 */
const facebookUsername = process.env.FACEBOOK_USERNAME;
const facebookPassword = process.env.FACEBOOK_PASSWORD;

function isStateFresh(filePath: string, maxAgeMs: number): boolean {
  try {
    const stats = fs.statSync(filePath);
    return Date.now() - stats.mtimeMs < maxAgeMs;
  } catch {
    return false;
  }
}

const FACEBOOK_STATE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000; // 7 days
const forceSetup = process.env.FORCE_FACEBOOK_SETUP === '1';

setup.skip(
  !forceSetup && isStateFresh(facebookAuthFile, FACEBOOK_STATE_MAX_AGE_MS),
  'Facebook state already exists and is fresh. Delete playwright/.auth/facebook-state.json or set FORCE_FACEBOOK_SETUP=1 to re-authenticate.'
);

setup('connect Facebook account', async ({ page }) => {
  setup.setTimeout(600_000);
  fs.mkdirSync(path.dirname(facebookAuthFile), { recursive: true });

  await page.goto('/accounts');
  await expect(page.getByRole('heading', { name: 'Connected Accounts' })).toBeVisible();

  // Click the new-account button.
  await page.getByTestId('new-account-button').click();

  // Select Facebook from the modal's listbox.
  await page.getByRole('button', { name: 'Account type Typeform' }).click();
  await page.getByRole('option', { name: 'Facebook' }).click();

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
  }

  // Wait for redirect back to the dashboard with a connected Facebook account.
  await page.waitForURL(/\/accounts\?type=facebook/, { timeout: 600_000 });
  await expect(page.getByRole('heading', { name: 'Connected Accounts' })).toBeVisible();

  // Save the combined state (Auth0 + Facebook cookies).
  await page.context().storageState({ path: facebookAuthFile });
});
