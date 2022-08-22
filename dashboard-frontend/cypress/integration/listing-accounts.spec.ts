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
      cy.get('[data-testid="connect-button-connect"]')
        .should('contain', 'connect')
        .should('have.length', 3);
    });

    it('sees no update buttons because all accounts are unconnected', () => {
      cy.get('[data-testid="connect-button-connect"]').should(
        'not.contain',
        'update'
      );
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
      cy.get('[data-testid="input-client-id-0"]').should(
        'have.value',
        '123456'
      );
      cy.get('[data-testid="input-client-secret-0"]').should(
        'have.value',
        'qwertyuiop'
      );
    });

    it('sees an update button for the connected account', () => {
      cy.get('[data-testid="connect-button-update"]')
        .should('contain', 'update')
        .should('have.length', 1);
    });

    it('sees a connect button for each unconnected account', () => {
      cy.get('[data-testid="connect-button-connect"]')
        .should('contain', 'connect')
        .should('have.length', 2);
    });
  });

  describe('When the user has two connected accounts and visits the accounts page', () => {
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
      cy.get('[data-testid="input-token-1"]').should('have.value', '!"·$%&/()');
    });

    it('sees an update button for each connected account', () => {
      cy.get('[data-testid="connect-button-update"]')
        .should('contain', 'update')
        .should('have.length', 2);
    });

    it('sees a connect button for the unconnected account', () => {
      cy.get('[data-testid="connect-button-connect"]')
        .should('contain', 'connect')
        .should('have.length', 1);
    });
  });

  describe('When all accounts are connected and the user visits the homepage', () => {
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
        {
          name: 'Some other account',
          authType: 'token',
          connectedAccount: {
            createdAt: new Date('20/08/2021').getTime(),
            credentials: {
              token: '=)(/&%$·"!',
            },
          },
        },
      ];

      connectedAccounts.map(account => createAccountResource(server, account));

      cy.visit('/accounts');
    });

    it('sees the data associated with the connected accounts', () => {
      cy.get('[data-testid="account-list-item"]')
        .eq(2)
        .should('contain', 'Some other account');
      cy.get('[data-testid="input-token-2"]').should(
        'have.value',
        '=)(/&%$·"!'
      );
    });

    it('sees an update button for each connected account', () => {
      cy.get('[data-testid="connect-button-update"]')
        .should('contain', 'update')
        .should('have.length', 3);
    });

    it('sees no connect buttons because all accounts are connected', () => {
      cy.get('[data-testid="connect-button-update"]').should(
        'not.contain',
        'connect'
      );
    });
  });
});
