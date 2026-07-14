import { test, expect, Page } from '@playwright/test';

/**
 * End-to-end test for the Variables → Strata flow.
 *
 * Preconditions:
 *   - Auth0 user is authenticated (via auth.setup.ts)
 *   - A Facebook account is connected (via facebook.setup.ts or manually)
 *
 * The Facebook Graph API responses are mocked so the test does not depend on the
 * connected account having real ad accounts, campaigns, or adsets. The OAuth
 * connection itself is real.
 */

const MOCK_AD_ACCOUNT = { id: 'act_123456789', account_id: '123456789', name: 'Mock Ad Account' };
const MOCK_CAMPAIGN = { id: 'mock-campaign-1', name: 'Mock Campaign' };
const MOCK_ADSET = {
  id: 'mock-adset-1',
  name: 'Mock Adset',
  targeting: {
    genders: [1],
    age_min: 18,
    age_max: 65,
  },
};

function mockFacebookApi(page: Page) {
  return page.route('https://graph.facebook.com/**', async route => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const paginated = (data: any[]) => ({ data, paging: { before: '', after: '' } });

    if (path.endsWith('/me/adaccounts')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(paginated([MOCK_AD_ACCOUNT])) });
      return;
    }
    if (path.endsWith('/campaigns')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(paginated([MOCK_CAMPAIGN])) });
      return;
    }
    if (path.endsWith('/adsets')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(paginated([MOCK_ADSET])) });
      return;
    }

    await route.continue();
  });
}

function mockConfsApi(page: Page) {
  return page.route(/\/confs$/, async route => {
    const response = await route.fetch();
    const body = await response.json();
    const confs = body.data || body;
    if (!confs.creatives) {
      confs.creatives = [];
    }
    await route.fulfill({
      status: response.status(),
      contentType: response.headers()['content-type'] || 'application/json',
      body: JSON.stringify(body),
    });
  });
}

test.describe('Variables → Strata flow', () => {
  test('extracts targeting from Meta, displays it, and saves variables and strata', async ({ page }) => {
    await mockFacebookApi(page);
    await mockConfsApi(page);
    const studyName = `playwright-test-${Date.now()}`;

    // 1. Create a new study
    await page.goto('/new-study');
    await page.getByTestId('new-study-name-input').waitFor();
    await page.getByTestId('new-study-name-input').fill(studyName);
    await page.getByTestId('form-submit-button').click();
    // Creating a study redirects to its initialization page.
    await page.waitForURL(/\/studies\/[^/]+\/initialize/);

    // 2. Navigate to General
    await page.getByRole('link', { name: 'General' }).click();
    await page.waitForURL(/\/studies\/.*\/general/);

    // Select an ad account and save
    await page.locator('select[name="ad_account"]').waitFor();
    await page.locator('select[name="ad_account"]').selectOption({ index: 1 });
    await page.getByTestId('form-submit-button').click();
    await expect(page.getByText('General settings saved').first()).toBeVisible();

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

    // 6. Add a level, fill in its name, and select an adset
    await page.getByText('Add level').click();
    await page.getByTestId('level-name-input').fill('men');
    await page.getByTestId('level-adset-select').selectOption(MOCK_ADSET.id);

    // 7. Verify the output panel shows extracted targeting
    await expect(page.getByTestId('level-output-panel')).toBeVisible();
    await expect(page.getByTestId('level-targeting-summary')).not.toHaveText('No targeting data');
    await expect(page.getByText('Last extracted')).toBeVisible();

    // 8. Submit variables
    await page.getByTestId('form-submit-button').click();
    await expect(page.getByText('Variables saved').first()).toBeVisible();

    // 9. Navigate to Strata
    await page.getByRole('link', { name: 'Strata' }).click();
    await page.waitForURL(/\/studies\/.*\/strata/);

    // 10. Fill finish question ref and regenerate strata
    await page.locator('input[name="finishQuestionRef"]').fill('finish');
    const regenerateButton = page.getByTestId('regenerate-strata-button');
    await expect(regenerateButton).toBeVisible();
    await regenerateButton.click();

    // 11. Verify stratum output panel shows the merged targeting
    await expect(page.getByTestId('stratum-output-panel').first()).toBeVisible();
    await expect(page.getByTestId('stratum-targeting-summary').first()).not.toHaveText('No targeting data');

    // 12. Submit strata
    await page.getByTestId('form-submit-button').click();
    await expect(page.getByText('Strata saved').first()).toBeVisible();
  });
});
