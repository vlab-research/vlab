import { createAccountResource, makeServer } from '../../src/server';

describe('Given an authenticated user', () => {
  beforeEach(() => {
    cy.loginToAuth0(
      Cypress.env('auth0_username'),
      Cypress.env('auth0_password')
    );
    cy.visit('/accounts');
  });
  describe('When the user visits the accounts page', () => {
    it('they update an account succesfully', () => {
      cy.get('[data-testid="input-fly-0"]').should('exist');
      cy.get('[data-testid="input-fly-0"]').clear().type('newsupersecret');
      cy.get('[data-testid="existing-account-submit-button-0"]').click();
      cy.get('[data-testid="input-fly-0"]')
        .invoke('val')
        .should('eq', 'newsupersecret');
    });
  });
});
