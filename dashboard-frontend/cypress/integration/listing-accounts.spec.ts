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
    });

    it('sees a connect button for each unconnected account', () => {
      cy.get('[data-testid="new-account-submit-button"]')
        .should('have.length', 3)
        .contains('Connect');
    });

    it('sees no update buttons because all accounts are unconnected', () => {
      cy.get('[data-testid="new-account-submit-button"]').should(
        'not.contain',
        'update'
      );
    });
  });

  describe('When the user has one connected account and visits the accounts page', () => {
    beforeEach(() => {
      const connectedAccounts = {
        name: 'Some other account',
        authType: 'token',
        connectedAccount: {
          createdAt: Date.now(),
          credentials: {
            token: 'some token',
          },
        },
      };

      createAccountResource(server, connectedAccounts);

      cy.visit('/accounts');
    });

    it('sees the data associated with the connected account', () => {
      cy.get('[data-testid="account-list-item"]')
        .eq(2)
        .should('contain', 'Some other account');

      cy.get('[data-testid="input-token-2"]').should(
        'have.value',
        'some token'
      );
    });

    it('sees an update button for the connected account', () => {
      cy.get('[data-testid="existing-account-submit-button"]')
        .should('have.length', 1)
        .contains('Update');
    });

    it('sees a connect button for each unconnected account', () => {
      cy.get('[data-testid="new-account-submit-button"]')
        .should('have.length', 2)
        .should('contain', 'Connect');
    });
  });

  describe('When the user has two connected accounts of different auth types', () => {
    beforeEach(() => {
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

    it('sees the data associated with the client id/secret account', () => {
      cy.get('[data-testid="input-client-id-0"]').should(
        'have.value',
        '123456'
      );

      cy.get('[data-testid="input-client-secret-0"]').should(
        'have.value',
        'qwertyuiop'
      );

      cy.get('[data-testid="input-token-1"]').should('have.value', '!"·$%&/()');
    });

    it('sees the data associated with the token account', () => {
      cy.get('[data-testid="input-token-1"]').should('have.value', '!"·$%&/()');
    });
  });
});
