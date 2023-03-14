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
  let server: ReturnType<typeof makeServer>;

  beforeEach(() => {
    cy.loginToAuth0(
      Cypress.env('auth0_username'),
      Cypress.env('auth0_password')
    )
    server = makeServer({ environment: 'test' });
  });

  afterEach(() => {
    server.shutdown();
  });

  describe('When he visits a specific Study page', () => {
    beforeEach(() => {
      const study = createStudyResource(server, {
        name: 'Weekly consume of meat',
        slug: 'weekly-consume-of-meat',
      });

      createSegmentProgressResource(server, {
        study,
        segmentProgress: {
          ...getFakeStudySegmentProgress(),
          name: '64-spain',
          datetime: new Date('2021-06-19').getTime(),
        },
      });
      createSegmentProgressResource(server, {
        study,
        segmentProgress: {
          ...getFakeStudySegmentProgress(),
          name: '64-france',
          datetime: new Date('2021-06-19').getTime(),
        },
      });

      createSegmentProgressResource(server, {
        study,
        segmentProgress: {
          ...getFakeStudySegmentProgress(),
          name: '64-spain',
          datetime: new Date('2021-06-20').getTime(),
        },
      });
      createSegmentProgressResource(server, {
        study,
        segmentProgress: {
          ...getFakeStudySegmentProgress(),
          name: '64-france',
          datetime: new Date('2021-06-20').getTime(),
        },
      });

      createSegmentProgressResource(server, {
        study,
        segmentProgress: {
          ...getFakeStudySegmentProgress(),
          name: '64-spain',
          datetime: new Date('2021-06-21').getTime(),
          currentParticipants: 7137,
          expectedParticipants: 7750,
          desiredPercentage: 10,
          currentPercentage: 3.2,
          expectedPercentage: 3.4,
          percentageDeviationFromGoal: 6.8,
        },
      });
      createSegmentProgressResource(server, {
        study,
        segmentProgress: {
          ...getFakeStudySegmentProgress(),
          name: '64-france',
          datetime: new Date('2021-06-21').getTime(),
          currentParticipants: 13000,
          expectedParticipants: 13500,
          desiredPercentage: 10,
          currentPercentage: 6.2,
          expectedPercentage: 6.8,
          percentageDeviationFromGoal: 3.8,
        },
      });

      cy.visit('/studies/weekly-consume-of-meat');

      assertLoadersAppear();
    });

    it('They see the name of the Study', () => {
      cy.contains('Weekly consume of meat');
    });

    it('They see an overview of the current Study progress', () => {
      cy.contains('Current Participants');
      cy.contains('20,137');

      cy.contains('Expected Participants');
      cy.contains('21,250');

      cy.contains('Current Avg. Deviation');
      cy.contains('5.3 %');

      cy.contains('Expected Avg. Deviation');
      cy.contains('4.9 %');
    });

    it('They see an areachart with current participants data over time', () => {
      assertStudyProgressChartAppears({
        numDataPoints: 3,
      });
    });

    it('They see current avg. deviation data over time in the areachart after clicking the related stat card', () => {
      assertStudyProgressChartAppears({
        numDataPoints: 3,
      });
      cy.get('[data-testid="study-progress-chart"]').contains('20,000');

      cy.get('[data-testid="study-page-stats"]')
        .contains('Current Avg. Deviation')
        .click();

      assertStudyProgressChartAppears({
        numDataPoints: 3,
      });
      cy.get('[data-testid="study-progress-chart"]')
        .contains('20,000')
        .should('not.exist');
      cy.get('[data-testid="study-progress-chart"]').contains('5.0');
    });

    it("They's redirected to the Studies page when clicking the back button", () => {
      cy.get('[data-testid="back-button"]').click();

      cy.url().should('eq', `${Cypress.config().baseUrl}/`);
    });
  });

  describe('When he has created a Study with one Segment and visits the Study page', () => {
    beforeEach(() => {
      const study = createStudyResource(server, {
        name: 'Weekly consume of meat',
        slug: 'weekly-consume-of-meat',
      });

      createSegmentProgressResource(server, {
        study,
        segmentProgress: {
          id: 'e1912f80-d9ff-4680-8bbd-bdefd1834b38',
          name: '64-spain',
          currentBudget: 7200,
          desiredPercentage: 10,
          currentPercentage: 5.95,
          expectedPercentage: 6.55,
          desiredParticipants: null,
          currentParticipants: 1429,
          expectedParticipants: 1571,
          datetime: Date.now(),
          currentPricePerParticipant: 2,
          percentageDeviationFromGoal: 4.05,
        },
      });

      cy.visit(`/studies/${study.slug}`);

      assertLoadersAppear();
    });

    it('They see a table that displays the current progress of acquiring participants for each Segment', () => {
      cy.contains('Participants acquired per segment');

      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('Name');
      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('%Deviation');
      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('%Desired');
      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('%Current');
      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('%Expected');
      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('Desired');
      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('Current');
      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('Expected');
      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('Budget');
      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('Price');

      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('64-spain');
      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('4.05');
      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('10');
      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('5.95');
      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('6.55');
      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('1,429');
      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('1,571');
      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('7,200');
    });
  });

  describe('When he has created a Study with 12 Segments and visits the Study page', () => {
    beforeEach(() => {
      const study = createStudyResource(server, {
        name: 'Weekly consume of meat',
        slug: 'weekly-consume-of-meat',
      });

      createStudySegments(server, {
        study,
        numOfSegments: 12,
      });

      cy.visit(`/studies/${study.slug}`);

      assertLoadersAppear();
    });

    it('They see 10 Segments in the "Participants acquired per segment" table', () => {
      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('Showing 1 to 10 of 12 results');
      cy.get('[data-testid="participants-acquired-per-segment-table"]')
        .find('tbody')
        .find('tr')
        .should('have.length', 10);
    });
    it('They see the remaining 2 Segments after clicking the Next button', () => {
      cy.contains('Previous').should('have.attr', 'disabled', 'disabled');
      cy.contains('Next').should('not.have.attr', 'disabled');

      cy.contains('Next').click();

      cy.get(
        '[data-testid="participants-acquired-per-segment-table"]'
      ).contains('Showing 11 to 12 of 12 results');
      cy.get('[data-testid="participants-acquired-per-segment-table"]')
        .find('tbody')
        .find('tr')
        .should('have.length', 2);

      cy.contains('Previous').should('not.have.attr', 'disabled');
      cy.contains('Next').should('have.attr', 'disabled', 'disabled');
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

      cy.get('[data-testid="%current-column-value"]').then(
        firstPageOfColumnValues => {
          cy.contains('Next').click();
          cy.get('[data-testid="%current-column-value"]').then(
            secondPageOfColumnValues => {
              const allCurrentPercentageColumnValues = [
                ...Array.from(firstPageOfColumnValues),
                ...Array.from(secondPageOfColumnValues),
              ].map(({ innerText }) => parseNumber(innerText));

              assertValuesAreOrdered(allCurrentPercentageColumnValues, 'asc');
            }
          );
        }
      );
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

      cy.get('[data-testid="%deviation-column-value"]').then(
        firstPageOfColumnValues => {
          cy.contains('Next').click();
          cy.get('[data-testid="%deviation-column-value"]').then(
            secondPageOfColumnValues => {
              const allDeviationPercentageColumnValues = [
                ...Array.from(firstPageOfColumnValues),
                ...Array.from(secondPageOfColumnValues),
              ].map(({ innerText }) => parseNumber(innerText));

              assertValuesAreOrdered(
                allDeviationPercentageColumnValues,
                'desc'
              );
            }
          );
        }
      );
    });
  });

  describe('When he visits a specific Study page and clicks the Studies link in the header', () => {
    beforeEach(() => {
      createStudyResource(server, {
        name: 'Weekly consume of meat',
        slug: 'weekly-consume-of-meat',
      });

      cy.visit('/studies/weekly-consume-of-meat');

      assertLoadersAppear();
    });

    it("They's redirected to the Studies page", () => {
      cy.get('[data-testid="header"]')
        .contains('Studies')
        .should('have.class', 'border-transparent text-gray-500')
        .should('not.have.attr', 'aria-current');

      cy.get('[data-testid="header"]').contains('Studies').click();

      cy.url().should('eq', `${Cypress.config().baseUrl}/`);
      cy.get('[data-testid="header"]')
        .contains('Studies')
        .should('have.class', 'border-indigo-500 text-gray-900')
        .should('have.attr', 'aria-current', 'page');
    });
  });
  
 // TODO this test is very flaky, we should rewrite it to be more stable
 // describe('When they visits a specific Study page and there is an error while fetching the Study', () => {
 //   beforeEach(() => {
 //     server.get(
 //       '/studies/:slug',
 //       () =>
 //         new Response(
 //           500,
 //           { 'content-type': 'application/json' },
 //           {
 //             error:
 //               "Database is temporarily down. Couldn't retrieve the Study.",
 //           }
 //         )
 //     );

 //     cy.visit('/studies/weekly-consume-of-meat');

 //     assertLoadersAppear();
 //   });

 //   it('They see an error page with a button to retry fetching the Study', () => {
 //     cy.contains('Something went wrong while fetching the Study.').then(() => {
 //       server.shutdown();
 //       server = makeServer({ environment: 'test' });
 //       const study = createStudyResource(server, {
 //         name: 'Weekly consume of meat',
 //         slug: 'weekly-consume-of-meat',
 //       });
 //       createStudySegments(server, { study, numOfSegments: 1 });
 //     });

 //     cy.contains('Please try again').click();
 //     assertLoadersAppear();

 //     cy.contains('Weekly consume of meat');
 //   });
 // });

  describe("When they visits a specific Study page that hasn't any progress", () => {
    beforeEach(() => {
      createStudyResource(server, {
        name: 'Weekly consume of meat',
        slug: 'weekly-consume-of-meat',
      });

      cy.visit('/studies/weekly-consume-of-meat');

      assertLoadersAppear();
    });

    it('They see default values in the overview of the Study', () => {
      cy.get('[data-testid="stats-card-for-current-participants"]').contains(
        '0'
      );
      cy.get('[data-testid="stats-card-for-expected-participants"]').contains(
        '0'
      );
      cy.get('[data-testid="stats-card-for-current-avg.-deviation"]').contains(
        '0 %'
      );
      cy.get('[data-testid="stats-card-for-expected-avg.-deviation"]').contains(
        '0 %'
      );
    });

    it('They see the default Study progress in the areachart', () => {
      assertStudyProgressChartAppears({
        numDataPoints: 1,
      });
      cy.get('[data-testid="study-progress-chart"]').contains('0');
    });

    // TODO: Create a tests for the table empty state
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

const createStudySegments = (
  server: ReturnType<typeof makeServer>,
  { study, numOfSegments }: { study: StudyResource; numOfSegments: number }
) => {
  const currentTime = Date.now();
  const placeholderData = {
    creationDate: currentTime,
    desiredParticipants: 24000,
    desiredParticipantsPerStrata: 2400,
    totalDaysOfData: 24,
  };

  const segmentsProgress = createFakeStudy({
    ...placeholderData,
    numOfDifferentStrata: numOfSegments,
  }).stratumProgressList.slice(-numOfSegments);

  segmentsProgress.forEach(segmentProgress => {
    createSegmentProgressResource(server, {
      study,
      segmentProgress: {
        ...segmentProgress,
        datetime: currentTime,
      },
    });
  });
};

const getFakeStudySegmentProgress = (): StudySegmentProgressResource => ({
  id: chance.guid({ version: 4 }),
  currentBudget: 0,
  desiredPercentage: 0,
  currentPercentage: 0,
  desiredParticipants: null,
  currentPricePerParticipant: 0,
  expectedPercentage: 0,
  percentageDeviationFromGoal: 0,
  currentParticipants: 0,
  expectedParticipants: 0,
  datetime: Date.now(),
  name: '',
});

const assertValuesAreOrdered = (values: number[], order: 'asc' | 'desc') => {
  values.forEach((value, index) => {
    if (index === 0) {
      return;
    }

    const previousValue = values[index - 1];

    if (order === 'asc') {
      expect(value).to.be.gte(previousValue);
    } else {
      expect(value).to.be.lte(previousValue);
    }
  });
};
