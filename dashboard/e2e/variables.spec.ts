import { test, expect } from '@playwright/test';

/**
 * End-to-end test for the Variables → Strata flow.
 *
 * Preconditions:
 *   - Auth0 user is authenticated (via auth.setup.ts)
 *   - A Facebook account is connected (via facebook.setup.ts or manually)
 *   - The connected Facebook account has at least one ad account with a campaign and adset
 *
 * This test exercises the refactor: explicit extraction from Meta, output panels,
 * submit gating, and merge-aware strata regeneration.
 */

test.describe('Variables → Strata flow', () => {
  test('extracts targeting from Meta, displays it, and saves variables and strata', async ({ page }) => {
    const studyName = `playwright-test-${Date.now()}`;

    // 1. Create a new study
    await page.goto('/new-study');
    await page.getByTestId('new-study-name-input').waitFor();
    await page.getByTestId('new-study-name-input').fill(studyName);
    await page.getByTestId('form-submit-button').click();
    await page.waitForURL(/\/studies$/);
    await expect(page.getByText(studyName)).toBeVisible();

    // 2. Open the study configuration and go to General
    await page.getByText(studyName).click();
    await page.waitForURL(/\/studies\//);
    await page.getByRole('link', { name: 'General' }).click();
    await page.waitForURL(/\/studies\/.*\/general/);

    // Select an ad account and save
    await page.locator('select[name="ad_account"]').waitFor();
    await page.locator('select[name="ad_account"]').selectOption({ index: 1 });
    await page.getByTestId('form-submit-button').click();
    await expect(page.getByText('General saved')).toBeVisible();

    // 3. Navigate to Variables
    await page.getByRole('link', { name: 'Variables' }).click();
    await page.waitForURL(/\/studies\/.*\/variables/);

    // 4. Select a template campaign
    await page.getByTestId('template-campaign-select').waitFor();
    await page.getByTestId('template-campaign-select').selectOption({ index: 1 });
    await expect(page.getByTestId('refresh-from-meta-button')).toBeVisible();

    // 5. Fill in the variable
    await page.getByTestId('variable-name-input').fill('gender');

    // Select properties from Meta
    await page.getByTestId('variable-properties-select').selectOption(['genders']);

    // 6. Fill in the level and select an adset
    await page.getByTestId('level-name-input').fill('men');
    await page.getByTestId('level-adset-select').selectOption({ index: 1 });

    // 7. Verify the output panel shows extracted targeting
    await expect(page.getByTestId('level-output-panel')).toBeVisible();
    await expect(page.getByTestId('level-targeting-summary')).not.toHaveText('No targeting data');
    await expect(page.getByText('Last extracted')).toBeVisible();

    // 8. Submit variables
    await page.getByTestId('form-submit-button').click();
    await expect(page.getByText('Variables saved')).toBeVisible();

    // 9. Navigate to Strata
    await page.getByRole('link', { name: 'Strata' }).click();
    await page.waitForURL(/\/studies\/.*\/strata/);

    // 10. Regenerate strata if stale
    const regenerateButton = page.getByTestId('regenerate-strata-button');
    if (await regenerateButton.isVisible()) {
      await regenerateButton.click();
    }

    // 11. Verify stratum output panel shows the merged targeting
    await expect(page.getByTestId('stratum-output-panel').first()).toBeVisible();
    await expect(page.getByTestId('stratum-targeting-summary').first()).not.toHaveText('No targeting data');

    // 12. Submit strata
    await page.getByTestId('form-submit-button').click();
    await expect(page.getByText('Strata saved')).toBeVisible();
  });
});
