import { makeServer } from '../../src/server';

describe('Given an authenticated user', () => {
  let server: ReturnType<typeof makeServer>;

  beforeEach(() => {
    server = makeServer({ environment: 'test' });
  });

  afterEach(() => {
    server.shutdown();
  });

  describe('When he visits New Study page and creates a Study successfully', () => {
    it("He's redirected to the Studies page which lists the created Study", () => {
      const newStudyName = 'Example Study';
      cy.visit('/new-study');

      cy.get('[data-testid="new-study-name-input"]').type(newStudyName);
      cy.get('[data-testid="new-study-submit-button"]').click();

      cy.url().should('eq', `${Cypress.config().baseUrl}/`);
      cy.contains(newStudyName);
    });
  });

  describe('When he visits New Study page and clicks the back button', () => {
    it("He's redirected to the Studies page", () => {
      cy.visit('/new-study');

      cy.get('[data-testid="back-button"]').click();

      cy.url().should('eq', `${Cypress.config().baseUrl}/`);
    });
  });
});
