import { Response } from 'miragejs';
import Chance from 'chance';
import {
  makeServer,
  createStudyResource,
  createStudyResources,
  createStudyProgressResource,
} from '../../src/server';

const chance = Chance();

describe('Given an authenticated user', () => {
  let server: ReturnType<typeof makeServer>;

  beforeEach(() => {
    server = makeServer({ environment: 'test' });
  });

  afterEach(() => {
    server.shutdown();
  });

  describe("When he hasn't created any Study and visits the home page", () => {
    beforeEach(() => {
      cy.visit('/');
      assertLoaderAppears();
    });

    it('He sees information on how to create a Study', () => {
      cy.contains('Contact info@vlab.digital and create your first Study.');
      cy.contains('info@vlab.digital').should(
        'have.attr',
        'href',
        'mailto:info@vlab.digital?subject=[New Account] Create first Study'
      );
    });
  });

  describe('When he has created one Study and visits the home page', () => {
    beforeEach(() => {
      const study = createStudyResource(server, {
        name: 'Study 1',
        slug: 'study-1',
        createdAt: new Date('Tue, 09 Mar 2021 01:39:09 GMT').getTime(),
      });

      createStudyProgressResource(server, {
        study,
        progress: {
          id: chance.guid({ version: 4 }),
          datetime: new Date('2021-06-19').getTime(),
          currentParticipants: 0,
          expectedParticipants: 0,
          currentAverageDeviation: 0,
          expectedAverageDeviation: 0,
          desiredParticipants: null,
        },
      });

      cy.visit('/');

      assertLoaderAppears();
    });

    it('He sees the name and creation date of the Study', () => {
      cy.get('[data-testid="study-list-item"]')
        .should('contain', 'Study 1')
        .should('contain', 'Created on March 09, 2021');
    });

    it("He's redirected to the Study page when clicking the created Study", () => {
      cy.get('[data-testid="header"]')
        .contains('Studies')
        .should('have.class', 'border-indigo-500 text-gray-900')
        .should('have.attr', 'aria-current', 'page');

      cy.get('[data-testid="study-list-item"]').click();

      cy.url().should('eq', `${Cypress.config().baseUrl}/studies/study-1`);
      cy.get('[data-testid="header"]')
        .contains('Studies')
        .should('have.class', 'border-transparent text-gray-500')
        .should('not.have.attr', 'aria-current');
    });
  });

  describe('When he has created 20 Studies and visits the home page', () => {
    beforeEach(() => {
      createStudyResources(server, 20);

      cy.visit('/');

      assertLoaderAppears();
    });

    it('He sees a list of 10 studies', () => {
      cy.get('[data-testid="study-list-item"]').should('have.length', 10);
    });

    it('He sees the 20 studies after paginating once', () => {
      cy.scrollTo('bottom');
      assertLoaderAppears();
      cy.get('[data-testid="study-list-item"]').should('have.length', 20);
    });
  });

  describe('When he visits the home page and there is an error while fetching the Studies', () => {
    beforeEach(() => {
      server.get(
        '/studies',
        () =>
          new Response(
            500,
            { 'content-type': 'application/json' },
            {
              error:
                "Database is temporarily down. Couldn't retrieve the Studies.",
            }
          )
      );

      cy.visit('/');

      assertLoaderAppears();
    });

    it('He sees an error page with a button to retry fetching the Studies', () => {
      cy.contains(
        "Database is temporarily down. Couldn't retrieve the Studies."
      ).then(() => {
        server.shutdown();
        server = makeServer({ environment: 'test' });
        createStudyResource(server);
      });
      cy.contains('Please try again').click();
      assertLoaderAppears();
      cy.get('[data-testid="study-list-item"]').should('have.length', 1);
    });
  });
});

const assertLoaderAppears = () =>
  cy.get('[data-testid="study-list-skeleton-item"]').should('have.length', 10);
