import { Response } from 'miragejs';
import Chance from 'chance';
import { createFakeStudy } from '../../src/fixtures/study';
import {
  makeServer,
  createStudyResource,
  createStudyProgressResource,
  createSegmentProgressResource,
} from '../../src/server';
import { StudyResource } from '../../src/types/study';

const chance = Chance();

describe('Given an authenticated user', () => {
  let server: ReturnType<typeof makeServer>;

  beforeEach(() => {
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

      [
        {
          id: chance.guid({ version: 4 }),
          datetime: new Date('2021-06-19').getTime(),
          currentParticipants: 0,
          expectedParticipants: 0,
          currentAverageDeviation: 0,
          expectedAverageDeviation: 0,
          desiredParticipants: null,
        },
        {
          id: chance.guid({ version: 4 }),
          datetime: new Date('2021-06-20').getTime(),
          currentParticipants: 15037,
          expectedParticipants: 16000,
          currentAverageDeviation: 1,
          expectedAverageDeviation: 1.1,
          desiredParticipants: null,
        },
        {
          id: chance.guid({ version: 4 }),
          datetime: new Date('2021-06-21').getTime(),
          currentParticipants: 20137,
          expectedParticipants: 21250,
          currentAverageDeviation: 1.5,
          expectedAverageDeviation: 1.7,
          desiredParticipants: null,
        },
      ].forEach(progress => {
        createStudyProgressResource(server, {
          study,
          progress,
        });
      });

      cy.visit('/studies/weekly-consume-of-meat');

      assertLoadersAppear();
    });

    it('He sees the name of the Study', () => {
      cy.contains('Weekly consume of meat');
    });

    it('He sees an overview of the current Study progress', () => {
      cy.contains('Current Participants');
      cy.contains('20,137');

      cy.contains('Expected Participants');
      cy.contains('21,250');

      cy.contains('Current Avg. Deviation');
      cy.contains('1.5 %');

      cy.contains('Expected Avg. Deviation');
      cy.contains('1.7 %');
    });

    it('He sees an areachart with current participants data over time', () => {
      assertStudyProgressChartAppears({
        numDataPoints: 3,
      });
    });

    it('He sees current avg. deviation data over time in the areachart after clicking the related stat card', () => {
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
      cy.get('[data-testid="study-progress-chart"]').contains('1.5');
    });

    it("He's redirected to the Studies page when clicking the back button", () => {
      cy.get('[data-testid="back-button"]').click();

      cy.url().should('eq', `${Cypress.config().baseUrl}/`);
    });
  });

  describe('When he has created a Study with one Segment and visits the Study page', () => {
    beforeEach(() => {
      const study = createStudyWithRandomProgress(server);

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
          percentageDeviationFromGoal: 5.95,
        },
      });

      cy.visit(`/studies/${study.slug}`);

      assertLoadersAppear();
    });

    it('He sees a table that displays summary per segment data', () => {
      cy.contains('Summary per segment');

      cy.get('[data-testid="summary-per-segment-table"]').contains('Name');
      cy.get('[data-testid="summary-per-segment-table"]').contains('%Progress');
      cy.get('[data-testid="summary-per-segment-table"]').contains('Budget');
      cy.get('[data-testid="summary-per-segment-table"]').contains('Spent');

      cy.get('[data-testid="summary-per-segment-table"]').contains('64-spain');
      cy.get('[data-testid="summary-per-segment-table"]').contains('94.05');
      cy.get('[data-testid="summary-per-segment-table"]').contains('7,200');
      cy.get('[data-testid="summary-per-segment-table"]').contains('2,858');
    });

    it('He sees a table that displays percentage of participants per segment data', () => {
      cy.contains('% Participants per segment');

      cy.get(
        '[data-testid="percentage-participants-per-segment-table"]'
      ).contains('Name');
      cy.get(
        '[data-testid="percentage-participants-per-segment-table"]'
      ).contains('%Desired');
      cy.get(
        '[data-testid="percentage-participants-per-segment-table"]'
      ).contains('%Current');
      cy.get(
        '[data-testid="percentage-participants-per-segment-table"]'
      ).contains('%Expected');

      cy.get(
        '[data-testid="percentage-participants-per-segment-table"]'
      ).contains('64-spain');
      cy.get(
        '[data-testid="percentage-participants-per-segment-table"]'
      ).contains('10');
      cy.get(
        '[data-testid="percentage-participants-per-segment-table"]'
      ).contains('5.95');
      cy.get(
        '[data-testid="percentage-participants-per-segment-table"]'
      ).contains('6.55');
    });

    it('He sees a table that displays participants per segment data', () => {
      cy.contains('Participants per segment');

      cy.get('[data-testid="participants-per-segment-table"]').contains('Name');
      cy.get('[data-testid="participants-per-segment-table"]').contains(
        'Desired'
      );
      cy.get('[data-testid="participants-per-segment-table"]').contains(
        'Current'
      );
      cy.get('[data-testid="participants-per-segment-table"]').contains(
        'Expected'
      );

      cy.get('[data-testid="participants-per-segment-table"]').contains(
        '64-spain'
      );
      cy.get('[data-testid="participants-per-segment-table"]').contains('N/A');
      cy.get('[data-testid="participants-per-segment-table"]').contains(
        '1,429'
      );
      cy.get('[data-testid="participants-per-segment-table"]').contains(
        '1,571'
      );
    });
  });

  describe('When he has created a Study with 12 Segments and visits the Study page', () => {
    beforeEach(() => {
      const study = createStudyWithRandomProgress(server);

      createStudySegments(server, {
        study,
        numOfSegments: 12,
      });

      cy.visit(`/studies/${study.slug}`);

      assertLoadersAppear();
    });

    it('He sees 7 Segments in the Summary per Segment table', () => {
      cy.get('[data-testid="summary-per-segment-table"]').contains(
        'Showing 1 to 7 of 12 results'
      );
      cy.get('[data-testid="summary-per-segment-table"]')
        .find('tbody')
        .find('tr')
        .should('have.length', 7);
    });
    it('He sees the remaining 5 Segments after clicking the Next button', () => {
      cy.contains('Previous').should('have.attr', 'disabled', 'disabled');
      cy.contains('Next').should('not.have.attr', 'disabled');

      cy.contains('Next').click();

      cy.get('[data-testid="summary-per-segment-table"]').contains(
        'Showing 8 to 12 of 12 results'
      );
      cy.get('[data-testid="summary-per-segment-table"]')
        .find('tbody')
        .find('tr')
        .should('have.length', 5);

      cy.contains('Previous').should('not.have.attr', 'disabled');
      cy.contains('Next').should('have.attr', 'disabled', 'disabled');
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

    it("He's redirected to the Studies page", () => {
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

  describe('When he visits a specific Study page and there is an error while fetching the Study', () => {
    beforeEach(() => {
      server.get(
        '/studies/:slug',
        () =>
          new Response(
            500,
            { 'content-type': 'application/json' },
            {
              error:
                "Database is temporarily down. Couldn't retrieve the Study.",
            }
          )
      );

      cy.visit('/studies/weekly-consume-of-meat');

      assertLoadersAppear();
    });

    it('He sees an error page with a button to retry fetching the Study', () => {
      cy.contains('Something went wrong while fetching the Study.').then(() => {
        server.shutdown();
        server = makeServer({ environment: 'test' });
        const study = createStudyWithRandomProgress(server);
        createStudySegments(server, { study, numOfSegments: 1 });
      });

      cy.contains('Please try again').click();
      assertLoadersAppear();

      cy.contains('Weekly consume of meat');
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
  cy.get('[data-testid="study-segment-table-skeleton"]').should(
    'have.length',
    3
  );
};

const createStudyWithRandomProgress = (
  server: ReturnType<typeof makeServer>
) => {
  const study = createStudyResource(server, {
    name: 'Weekly consume of meat',
    slug: 'weekly-consume-of-meat',
  });

  [
    {
      id: chance.guid({ version: 4 }),
      datetime: new Date('2021-06-19').getTime(),
      currentParticipants: 0,
      expectedParticipants: 0,
      currentAverageDeviation: 0,
      expectedAverageDeviation: 0,
      desiredParticipants: null,
    },
    {
      id: chance.guid({ version: 4 }),
      datetime: new Date('2021-06-20').getTime(),
      currentParticipants: 15037,
      expectedParticipants: 16000,
      currentAverageDeviation: 1,
      expectedAverageDeviation: 1.1,
      desiredParticipants: null,
    },
    {
      id: chance.guid({ version: 4 }),
      datetime: new Date('2021-06-21').getTime(),
      currentParticipants: 20137,
      expectedParticipants: 21250,
      currentAverageDeviation: 1.5,
      expectedAverageDeviation: 1.7,
      desiredParticipants: null,
    },
  ].forEach(progress => {
    createStudyProgressResource(server, {
      study,
      progress,
    });
  });

  return study;
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
    totalHoursOfData: 24,
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
