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
  beforeEach(() => {
    cy.loginToAuth0(
      Cypress.env('auth0_username'),
      Cypress.env('auth0_password')
    );
  });

  describe('When they visit the home page the the studies are listed', () => {
    it('They see information on how to create a Study', () => {
      cy.visit('/');
      cy.get('[data-testid="header"]').contains('Studies');
      cy.get('[data-testid="studies-list"]').should('exist');
      cy.wait(500);
      cy.get('[data-testid="study-list-item"]').should(
        'have.length.greaterThan',
        2
      );
    });
  });
});
