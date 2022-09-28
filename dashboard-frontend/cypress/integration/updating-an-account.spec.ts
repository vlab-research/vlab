import { createAccountResource, makeServer } from '../../src/server';

describe('Given an authenticated user', () => {
  let server: ReturnType<typeof makeServer>;

  beforeEach(() => {
    server = makeServer({ environment: 'test' });

    const today = Date.now();
    const yesterday = Date.now() - 24 * 60 * 60 * 1000;

    const connectedAccounts = [
      {
        name: 'Fly',
        authType: 'secret',
        connectedAccount: {
          createdAt: today,
          credentials: {
            clientId: '123456',
            clientSecret: 'qwertyuiop',
          },
        },
      },
      {
        name: 'Typeform',
        authType: 'token',
        connectedAccount: {
          createdAt: yesterday,
          credentials: {
            token: '!"·$%&/()',
          },
        },
      },
    ];

    connectedAccounts.map(account => createAccountResource(server, account));

    cy.visit('/accounts');
  });

  afterEach(() => {
    server.shutdown();
  });

  describe('When the user visits the accounts page and updates an account successfully', () => {
    const accountName = 'Fly';
    it('sees the updated credential(s) saved to the connected accounts list', () => {
      const clientId = 'test client id';

      cy.get('[data-testid="input-client-id-0"]').clear();
      cy.get('[data-testid="input-client-id-0"]').type(clientId);
      cy.get('[data-testid="existing-account-submit-button-0"]').click();
      cy.contains(`${accountName} account updated!`);

      cy.get('[data-testid="input-client-id-0"]').should(
        'have.value',
        clientId
      );

      cy.url().should('eq', `${Cypress.config().baseUrl}/accounts`);
      cy.get('[data-testid="existing-account-submit-button-0"]').contains(
        'Update'
      );

      const token = 'test token';

      cy.get('[data-testid="input-token-1"]').clear();
      cy.get('[data-testid="input-token-1"]').type(token);
      cy.get('[data-testid="existing-account-submit-button-1"]').click();
      cy.contains(`${accountName} account updated!`);

      cy.get('[data-testid="input-token-1"]').should('have.value', token);

      cy.url().should('eq', `${Cypress.config().baseUrl}/accounts`);
      cy.get('[data-testid="existing-account-submit-button-1"]').contains(
        'Update'
      );

      cy.visit('/');
      cy.visit('/accounts');

      cy.get('[data-testid="input-client-id-0"]').should(
        'have.value',
        clientId
      );

      cy.get('[data-testid="input-token-1"]').should('have.value', token);
      cy.get('[data-testid="input-token-2"]').should(
        'have.class',
        'focus:ring-indigo-500 focus:border-indigo-500 border-gray-300'
      );
    });

    it('is able to update the same account again', () => {
      const clientId = 'test client id 2';

      cy.get('[data-testid="input-client-id-0"]').clear();
      cy.get('[data-testid="input-client-id-0"]').type(clientId);
      cy.get('[data-testid="existing-account-submit-button-0"]').click();
      cy.contains(`${accountName} account updated!`);

      cy.get('[data-testid="input-client-id-0"]').should(
        'have.value',
        clientId
      );

      cy.url().should('eq', `${Cypress.config().baseUrl}/accounts`);
      cy.get('[data-testid="existing-account-submit-button-0"]').contains(
        'Update'
      );
    });

    it('is able to update an account with the same credentials', () => {
      const clientId = 'test client id 2';

      cy.get('[data-testid="input-client-id-0"]').clear();
      cy.get('[data-testid="input-client-id-0"]').type(clientId);
      cy.get('[data-testid="existing-account-submit-button-0"]').dblclick();

      cy.get('[data-testid="input-client-id-0"]').should(
        'have.value',
        clientId
      );

      cy.contains(`${accountName} account updated!`);
    });
  });

  describe('When the user tries to update an account with an empty credential', () => {
    it('sees an error message', () => {
      const errorMessage = 'Field cannot be empty';
      const clientId = ' ';

      cy.get('[data-testid="input-client-id-0"]').clear();
      cy.get('[data-testid="input-client-id-0"]').type(clientId);
      cy.get('[data-testid="input-client-id-0"]').should(
        'have.value',
        clientId
      );
      cy.get('[data-testid="existing-account-submit-button-0"]').click();

      cy.get('[data-testid="input-client-id-0"]').should(
        'have.class',
        'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
      );

      cy.contains(errorMessage);
    });
  });
});
