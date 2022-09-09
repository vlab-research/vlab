import { createAccountResource, makeServer } from '../../src/server';

describe('Given an authenticated user', () => {
  let server: ReturnType<typeof makeServer>;

  beforeEach(() => {
    server = makeServer({ environment: 'test' });
  });

  afterEach(() => {
    server.shutdown();
  });

  describe('When the user visits the accounts page and connects to an account successfully using a client id and secret', () => {
    const clientId = '123456';
    const clientSecret = 'qwertyuiop';

    it('sees the client id and client secret saved to the list of connected accounts', () => {
      cy.visit('/accounts');

      cy.get('[data-testid="input-client-id-0"]').type(clientId);
      cy.get('[data-testid="input-client-secret-0"]').type(clientSecret);
      cy.get('[data-testid="new-account-submit-button-0"]').click();

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
    });
  });

  describe('When the user visits the accounts page and connects an account successfully using a token', () => {
    const token = '!"·$%&/()!';

    it('sees the token saved to the list of connected accounts', () => {
      cy.visit('/accounts');

      cy.get('[data-testid="input-token-2"]').type(token);
      cy.get('[data-testid="new-account-submit-button-2"]').click();

      cy.get('[data-testid="input-token-2"]').should('have.value', token);

      cy.url().should('eq', `${Cypress.config().baseUrl}/accounts`);
      cy.get('[data-testid="new-account-submit-button-2"]').contains('Update');
    });
  });

  describe('When the user clicks the connect button twice when connecting a new account', () => {
    const token = '!"·$%&/()!';

    it('sees an error message', () => {
      cy.visit('/accounts');

      cy.get('[data-testid="input-token-2"]').type(token);
      cy.get('[data-testid="new-account-submit-button-2"]').click();
      cy.get('[data-testid="input-token-2"]').should('have.value', token);

      cy.get('[data-testid="existing-account-submit-button-2"]').click();
      cy.get('[data-testid="error-message-2"]').contains(
        'This account is already connected'
      );
    });
  });

  describe('When the user clicks the connect button on an already connected account', () => {
    beforeEach(() => {
      const connectedAccounts = {
        name: 'Fly',
        authType: 'secret',
        connectedAccount: {
          createdAt: Date.now(),
          credentials: {
            clientId: '123456',
            clientSecret: 'qwertyuiop',
          },
        },
      };

      createAccountResource(server, connectedAccounts);

      cy.visit('/accounts');
    });

    it('sees an error message', () => {
      cy.get('[data-testid="existing-account-submit-button-0"]').click();
      cy.get('[data-testid="error-message-0"]').contains(
        'This account is already connected'
      );
    });
  });
});
