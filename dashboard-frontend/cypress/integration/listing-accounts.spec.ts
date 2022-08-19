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

    it('sees the data associated with the connected account', () => {
      cy.get('[data-testid="account-list-item"]')
        .eq(0)
        .should('contain', 'Fly');

      cy.get('[data-testid="input-client-id"]').should('have.value', '123456');

      cy.get('[data-testid="input-client-secret"]').should(
        'have.value',
        'qwertyuiop'
      );
    });

    it('sees a button to update the credentials of each connected account', () => {
      cy.get('[data-testid="connect-button-update"]')
        .should('contain', 'update')
        .should('have.length', 1);
    });

    it('sees a button to connect to each unconnected account', () => {
      cy.get('[data-testid="connect-button-connect"]')
        .should('contain', 'connect')
        .should('have.length', 2);
    });
  });

  describe.only('When the user has two connected accounts and visits the accounts page', () => {
    beforeEach(() => {
      const connectedAccounts = [
        {
          name: 'Fly',
          authType: 'secret',
          connectedAccount: {
            createdAt: Date.now(),
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
            createdAt: Date.now() - 24 * 60 * 60 * 1000,
            credentials: {
              token: '!"·$%&/()',
            },
          },
        },
      ];

      connectedAccounts.map(account => createAccountResource(server, account));

      cy.visit('/accounts');
    });

    it('sees the data associated with the connected accounts', () => {
      cy.get('[data-testid="account-list-item"]')
        .eq(1)
        .should('contain', 'Typeform');
      cy.get('[data-testid="input-token"]').should('have.value', '!"·$%&/()');
    });

    it('sees a button to update the credentials of each connected account', () => {
      cy.get('[data-testid="connect-button-update"]')
        .should('contain', 'update')
        .should('have.length', 2);
    });

    it('sees a button to connect to each unconnected account', () => {
      cy.get('[data-testid="connect-button-connect"]')
        .should('contain', 'connect')
        .should('have.length', 1);
    });
  });
});
