import { createAccountResource, makeServer } from '../../src/server';

describe('Given an authenticated user', () => {
  let server: ReturnType<typeof makeServer>;

  beforeEach(() => {
    server = makeServer({ environment: 'test' });
  });

  afterEach(() => {
    server.shutdown();
  });

  describe('When no accounts are connected and the user visits the homepage', () => {
    it('shows three possible accounts to connect to', () => {
      cy.visit('/accounts');
      cy.get('[data-testid="header"]').contains('Connected Accounts');
      cy.get('[data-testid="account-list-item"]').should('have.length', 3);
      cy.contains('Fly');
      cy.contains('Typeform');
      cy.contains('Some other account');
    });
  });

  describe('When the user has one connected account and visits the accounts page', () => {
    beforeEach(() => {
      const account = {
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

      createAccountResource(server, account);

      cy.visit('/accounts');
    });

    it('sees the data associated with the connected account', () => {
      cy.get('[data-testid="account-list-item"]').should('contain', 'Fly');
      // TODO test for credentials
    });

    it('sees a button to update the credential(s) of the connected account', () => {
      cy.get('[data-testid="account-list-item"]').should('contain', 'Update');
    });

    it('sees a button to connect to the unconnected accounts', () => {
      cy.get('[data-testid="account-list-item"]').should('contain', 'Connect');
    });
  });
});
