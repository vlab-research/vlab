import { Response } from 'miragejs';
import Chance from 'chance';
import { createFakeStudy } from '../../src/fixtures/study';
import {
  makeServer,
  createStudyResource,
  createStudyProgressResource,
  createSegmentProgressResource,
} from '../../src/server';
import {
  StudyProgressResource,
  StudyResource,
  StudySegmentProgressResource,
} from '../../src/types/study';
import { parseNumber } from '../../src/helpers/numbers';

const chance = Chance();

describe('Given an authenticated user', () => {
  beforeEach(() => {
    cy.loginToAuth0(
      Cypress.env('auth0_username'),
      Cypress.env('auth0_password')
    );
    cy.visit('/studies/most-used-programming-language-for-api-development');
  });

  describe('When he visits a specific Study page', () => {
    it('They see the name of the Study', () => {
      cy.contains('Most used programming language for api development');
    });

    it('They see an overview of the current Study progress', () => {
      cy.contains('Current Participants');
      cy.contains('0');

      cy.contains('Expected Participants');
      cy.contains('32');

      cy.contains('Current Avg. Deviation');
      cy.contains('0.02 %');

      cy.contains('Expected Avg. Deviation');
      cy.contains('0 %');
    });

    it('They see current avg. deviation data over time in the areachart after clicking the related stat card', () => {
      assertStudyProgressChartAppears({
        numDataPoints: 6,
      });

      cy.get('[data-testid="study-page-stats"]')
        .contains('Current Avg. Deviation')
        .click();

      assertStudyProgressChartAppears({
        numDataPoints: 6,
      });
    });

    it("They's redirected to the Studies page when clicking the back button", () => {
      cy.get('[data-testid="back-button"]').click();

      cy.url().should('eq', `${Cypress.config().baseUrl}/studies`);
    });
  });

  it('They see that by default the Segments are ordered by current percentage of participants in ascending order', () => {
    cy.contains('%Current').within(() => {
      cy.get('[data-testid="selected-column-ascending-indicator"]').should(
        'be.visible'
      );
      cy.get('[data-testid="selected-column-descending-indicator"]').should(
        'not.be.visible'
      );
    });
  });

  it('They see that when clicking the "%Deviation column", the Segments are ordered by the percentage of deviation in descending order', () => {
    cy.contains('%Deviation').within(() => {
      cy.get('[data-testid="selected-column-ascending-indicator"]').should(
        'not.be.visible'
      );
      cy.get('[data-testid="selected-column-descending-indicator"]').should(
        'not.be.visible'
      );
    });

    cy.contains('%Deviation').click();

    cy.contains('%Deviation').within(() => {
      cy.get('[data-testid="selected-column-ascending-indicator"]').should(
        'not.be.visible'
      );
      cy.get('[data-testid="selected-column-descending-indicator"]').should(
        'be.visible'
      );
    });
  });

  describe('When he visits a specific Study page and clicks the Studies link in the header', () => {
    it('they are redirected to the Studies page', () => {
      cy.get('[data-testid="header"]')
        .contains('Studies')
        .should('have.class', 'border-transparent text-gray-500')
        .should('not.have.attr', 'aria-current');

      cy.get('[data-testid="header"]').contains('Studies').click();

      cy.url().should('eq', `${Cypress.config().baseUrl}/studies`);
      cy.get('[data-testid="header"]')
        .contains('Studies')
        .should('have.class', 'border-indigo-500 text-gray-900')
        .should('have.attr', 'aria-current', 'page');
    });
  });
});

const assertStudyProgressChartAppears = ({
  numDataPoints,
}: {
  numDataPoints: number;
}) =>
  cy
    .get('[data-testid="study-progress-chart"]')
    .get('.Series')
    .find('circle')
    .should('have.length', numDataPoints);

const assertLoadersAppear = () => {
  cy.contains('Loading...');
  cy.get('[data-testid="study-current-progress-card-skeleton"]').should(
    'have.length',
    4
  );
  cy.get('[data-testid="study-progress-chart-skeleton"]').should(
    'have.length',
    1
  );
  cy.get(
    '[data-testid="participants-acquired-per-segment-table-skeleton"]'
  ).should('have.length', 1);
};
