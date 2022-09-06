describe('Given an authenticated user', () => {
  beforeEach(() => {
    cy.loginToAuth0(
      Cypress.env('auth0_username'),
      Cypress.env('auth0_password')
    );
    cy.visit('/accounts');
  });

  describe('When no accounts are connected and the user visits the homepage', () => {
    it('shows three possible accounts to connect to', () => {
      cy.get('[data-testid="header"]').contains('Connected Accounts');
      cy.get('[data-testid="account-list-item"]').should('exist');
      cy.get('[data-testid="account-list-item"]').should(
        'have.length.greaterThan',
        2
      );

      cy.get('[data-testid="existing-account-submit-button-0"]').contains(
        'Update'
      );
      cy.get('[data-testid="existing-account-submit-button-1"]').contains(
        'Update'
      );
    });
  });
});
