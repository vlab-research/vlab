import Chance from 'chance';

import { makeServer } from '../../src/server';
import { getConfig } from './../../src/pages/NewStudyPage/getConfig';
import { baseConfig } from './../../src/pages/NewStudyPage/baseConfig';

const chance = Chance();

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
      const objs = getConfig(baseConfig);

      const getOptions = (index: number) => {
        return objs[index].options;
      };

      cy.visit('/new-study');

      const name = 'Example Study';
      const objective =
        getOptions(1)[Math.floor(Math.random() * getOptions(1).length)];
      const optimization_goal =
        getOptions(2)[Math.floor(Math.random() * getOptions(2).length)];
      const destination_type =
        getOptions(3)[Math.floor(Math.random() * getOptions(3).length)];
      const page_id = chance.guid();
      const instagram_id = chance.fbid();
      const min_budget = chance.floating({ min: 1, max: 10000 });
      const opt_window = chance.floating({ min: 0, max: 14 });
      const ad_account = chance.fbid();
      const country = chance.country({ full: true });

      const responses: any = {
        name,
        objective,
        optimization_goal,
        destination_type,
        page_id,
        instagram_id,
        min_budget,
        opt_window,
        ad_account,
        country,
      };

      const text = (obj: any, response: any) => {
        cy.get(`[data-testid="new-study-${obj.name}-input"]`).type(response);
      };

      const select = (obj: any, response: any) => {
        cy.get(`[data-testid="new-study-${obj.name}-input"]`).select(response);
      };

      for (let i = 0; i < objs.length; i++) {
        objs[i].type === 'text'
          ? text(objs[i], responses[objs[i].name])
          : select(
              objs[i],
              responses[objs[i].name].name || responses[objs[i].name]
            );
      }

      cy.get('[data-testid="new-study-submit-button"]').click();

      cy.url().should('eq', `${Cypress.config().baseUrl}/`);
      cy.contains(name);
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
