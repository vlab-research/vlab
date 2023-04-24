describe('Given an authenticated user', () => {
  beforeEach(() => {
    cy.loginToAuth0(
      Cypress.env('auth0_username'),
      Cypress.env('auth0_password')
    );
    cy.visit('/accounts');
  });

  describe('When the user visits the accounts page and creates a new account', () => {
    it('clicks on the add connected account vbutton and creates an account', () => {
      cy.get('[data-testid="create-account"]').should('exist');
      cy.get('[data-testid="create-account"]').click();
      cy.get('[data-testid="account-name"]').should('exist');
      cy.get('[data-testid="account-name"]').type('New Test Account');
      cy.get('[data-testid="add-account-modal"]').should('exist');
      cy.get('[data-testid="add-account-modal"]').click();
      cy.get('[data-testid="input-fly-label-0"]').should('exist');
      cy.get('[data-testid="input-fly-label-0"]')
        .invoke('val')
        .should('eq', 'New Test Account');
      cy.get('[data-testid="input-fly-0"]').should('exist');
      cy.get('[data-testid="input-fly-0"]').type('supersecret');
      cy.get('[data-testid="existing-account-submit-button-0"]').should(
        'exist'
      );
      cy.get('[data-testid="existing-account-submit-button-0"]').click();
      cy.get('[data-testid="input-fly-label-0"]').should('exist');
      cy.get('[data-testid="input-fly-0"]')
        .invoke('val')
        .should('eq', 'supersecret');
    });
  });
});
