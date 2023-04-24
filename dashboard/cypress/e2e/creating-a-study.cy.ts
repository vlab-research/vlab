describe('Given an authenticated user', () => {
  beforeEach(() => {
    cy.loginToAuth0(
      Cypress.env('auth0_username'),
      Cypress.env('auth0_password')
    );
  });

  describe('When he visits New Study page and creates a Study successfully', () => {
    it("He's redirected to the Studies page which lists the created Study", () => {
      const newStudyName = 'Example Study';
      cy.visit('/new-study');

      cy.get('[data-testid="new-study-name-input"]').type(newStudyName);
      cy.get('[data-testid="form-submit-button"]').click();

      cy.url().should('eq', `${Cypress.config().baseUrl}/studies`);
      cy.contains(newStudyName);
    });
  });

  describe('When he visits New Study page and clicks the back button', () => {
    it("He's redirected to the Studies page", () => {
      cy.visit('/new-study');

      cy.get('[data-testid="back-button"]').click();

      cy.url().should('eq', `${Cypress.config().baseUrl}/studies`);
    });
  });
});
