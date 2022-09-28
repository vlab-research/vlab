import { makeServer } from '../../src/server';

describe('Given an authenticated user', () => {
  let server: ReturnType<typeof makeServer>;

  beforeEach(() => {
    server = makeServer({ environment: 'test' });
    cy.visit('/accounts');
  });

  afterEach(() => {
    server.shutdown();
  });

  describe('When the user visits the accounts page and connects to an account successfully', () => {
    const clientId = '123456';
    const clientSecret = 'qwertyuiop';
    const token = '!"·$%&/()!';
    const accountName = 'Fly';

    it('sees the credential(s) saved to the list of connected accounts', () => {
      cy.get('[data-testid="input-client-id-0"]').type(clientId);
      cy.get('[data-testid="input-client-secret-0"]').type(clientSecret);
      cy.get('[data-testid="new-account-submit-button-0"]').click();

      cy.contains(`${accountName} account connected!`);

      cy.get('[data-testid="input-client-id-0"]').should(
        'have.value',
        clientId
      );
      cy.get('[data-testid="input-client-secret-0"]').should(
        'have.value',
        clientSecret
      );

      cy.url().should('eq', `${Cypress.config().baseUrl}/accounts`);

      cy.get('[data-testid="new-account-submit-button-0"]').contains('Update');
      cy.get('[data-testid="input-token-2"]').type(token);
      cy.get('[data-testid="new-account-submit-button-2"]').click();
      cy.get('[data-testid="input-token-2"]').should('have.value', token);
      cy.get('[data-testid="input-token-2"]').should(
        'have.class',
        'focus:ring-indigo-500 focus:border-indigo-500 border-gray-300'
      );

      cy.url().should('eq', `${Cypress.config().baseUrl}/accounts`);
      cy.get('[data-testid="new-account-submit-button-2"]').contains('Update');
    });
  });

  describe('When the user clicks the connect button twice when creating a new account', () => {
    const token = '!"·$%&/()!';
    const accountName = 'Test';

    it('simply updates with the same credential(s) again', () => {
      cy.get('[data-testid="input-token-2"]').type(token);
      cy.get('[data-testid="new-account-submit-button-2"]').dblclick();

      cy.contains(`${accountName} account connected!`);
    });
  });

  describe('When the user tries to connect with an empty credential', () => {
    it('sees an error message', () => {
      const errorMessage = 'Field cannot be empty';
      const token = ' ';

      cy.get('[data-testid="input-token-2"]').type(token);
      cy.get('[data-testid="new-account-submit-button-2"]').click();
      cy.get('[data-testid="input-token-2"]').should(
        'have.class',
        'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
      );

      cy.contains(errorMessage);
    });
  });
});
