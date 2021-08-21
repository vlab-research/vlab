import Chance from 'chance';
import { Model, Server } from 'miragejs';
import { createFakeStudy } from './fixtures/study';
import {
  StudyProgressResource,
  StudySegmentProgressResource,
  StudyResource,
} from './types/study';
import { isValidNumber } from './helpers/numbers';
import { createSlugFor } from './helpers/strings';

const chance = Chance();

export const makeServer = ({ environment = 'development' } = {}) => {
  let server = new Server({
    environment,

    models: {
      study: Model,
      studyProgress: Model,
      segmentProgress: Model,
    },

    seeds(server) {
      // TODO: Simplify the way I'm creating seeds.

      const today = Date.now();
      const yesterday = Date.now() - 24 * 60 * 60 * 1000;

      const staticStudyResources = [
        {
          name: 'Weekly consume meat',
          slug: 'weekly-consume-meat',
          createdAt: today,
        },
        {
          name: 'An extra-uterine system to physiologically support the extreme premature lamb',
          createdAt: yesterday,
        },
        {
          name: 'Correction of pathogenic gene mutation in human embryos',
          createdAt: new Date('06/10/2021').getTime(),
        },
        {
          name: 'A Feathered Dinosaur Tail wih Primitive Plumage Trapped in Mid-Cretaceous Amber',
          createdAt: new Date('05/15/2021').getTime(),
        },
        {
          name: 'The meditteranean diet is the best one',
          createdAt: new Date('02/17/2021').getTime(),
        },
        {
          name: 'Efficacy and effectiveness of an rVSV-vectored vaccine in preventing Ebola virus disease',
          createdAt: new Date('01/02/2021').getTime(),
        },
      ].map(study =>
        createStudyResource(server, {
          ...study,
          slug: createSlugFor(study.name),
        })
      );
      const randomStudyResources = createStudyResources(server, 34);

      [...staticStudyResources, ...randomStudyResources].forEach(
        studyResource => {
          const twentySegments = 20;

          const fakeStudy = createFakeStudy({
            creationDate: studyResource.createdAt,
            desiredParticipants: 24000,
            numOfDifferentStrata: twentySegments,
            desiredParticipantsPerStrata: 2400,
            totalHoursOfData: 24,
          });

          // For each Study, creates StudyProgress resources for last 24 days. (1 per day)
          const aDayInMilliseconds = 24 * 60 * 60 * 1000;
          const currentTimestamp = Date.now();
          const dateTimeFrom24DaysAgo =
            currentTimestamp -
            aDayInMilliseconds * fakeStudy.studyProgressList.length;

          let datetime = dateTimeFrom24DaysAgo;

          fakeStudy.studyProgressList.forEach(progress => {
            createStudyProgressResource(server, {
              study: studyResource,
              progress: {
                ...progress,
                datetime,
              },
            });

            datetime += aDayInMilliseconds;
          });

          /*
            For each Study, creates 20 SegmentProgress resources (1 for each Study Segment)
            Are going to be used to display current progress of the different 20 Segments in the Study page tables.
          */
          fakeStudy.stratumProgressList
            .slice(-twentySegments)
            .forEach((stratumProgress: any) => {
              createSegmentProgressResource(server, {
                study: studyResource,
                segmentProgress: {
                  ...stratumProgress,
                  datetime: currentTimestamp,
                },
              });
            });
        }
      );
    },

    routes() {
      this.namespace = 'api';
      this.timing = 750;

      this.get('/studies', ({ db }, request) => {
        let number = 10;
        let cursor = 0;

        const receivedNumber = Number(request.queryParams.number);
        if (isValidNumber(receivedNumber)) {
          number = receivedNumber;
        }

        const receivedCursor = Number(request.queryParams.cursor);
        if (isValidNumber(receivedCursor)) {
          cursor = receivedCursor;
        }

        const data = Array.from(db.studies as any).slice(
          cursor * number,
          cursor * number + 10
        );

        const nextData = Array.from(db.studies as any).slice(
          (cursor + 1) * number,
          (cursor + 1) * number + 10
        );

        return {
          data,
          pagination: {
            nextCursor: nextData.length ? String(cursor + 1) : null,
          },
        };
      });

      this.get('/studies/:slug', ({ db }, request) => {
        const study = (db.studies as any).findBy({ slug: request.params.slug });

        return {
          data: study,
        };
      });

      /**
       * Things to consider when implementing the real endpoint:
       *  - When a Study is initially created, an associated StudyProgress must be created with default values.
       *    As an example, when the frontend hits the real endpoint for a newly created Study, the response should
       *    include a data array with a single StudyProgress that have default values.
       *
       *  - This endpoint is used by the stats card and the chart displayed in the Study page.
       *    At the moment, we only display all-time progress (chart) or current progress (stat cards).
       *      - So this endpoint should only return one data point per day (latest one for that day)
       *      - This endpoint is not paginated because we need to display all available data in the chart.
       *        If we anticipate that this will be a problem, we can limit the number of StudyProgress returned
       *        by this endpoint to a fixed number. (first study progress and latest one will always be included)
       *
       *  - Soon, when we allow the users to pick a specific range of dates, we'll add the required query_parameters.
       *    To decide yet if we want more granularity and allow the user to see hourly and minutes updates reflected in the chart.
       */
      this.get('/studies/:slug/progress', ({ db }, request) => {
        const study: StudyResource = (db.studies as any).findBy({
          slug: request.params.slug,
        });

        return {
          data: Array.from(db.studyProgresses as any)
            .filter((progress: any) => progress.studyId === study.id)
            .sort((a: any, b: any) => a.datetime - b.datetime),
        };
      });

      /**
       * Things to consider when implementing the real endpoint:
       *  - This endpoint returns a paginated list of StudySegmentProgress for today.
       *    As an example, if an specific Study have 20 different Segments, when the frontend makes a request to this endpoint
       *    asking for 7 results, the api endpoint will return the most recent progress from 7 of the 20 Segments with a nextCursor,
       *    to request the next 7.
       *
       *  - The default order criteria still needs to be decided.
       *
       *  - Soon, when we allow the users to pick a specific range of dates, we'll add the required query_parameters.
       */
      this.get('/studies/:slug/segments-progress', ({ db }, request) => {
        let number = 10;
        let cursor = 0;

        const receivedNumber = Number(request.queryParams.number);
        if (isValidNumber(receivedNumber)) {
          number = receivedNumber;
        }

        const receivedCursor = Number(request.queryParams.cursor);
        if (isValidNumber(receivedCursor)) {
          cursor = receivedCursor;
        }

        const study: StudyResource = (db.studies as any).findBy({
          slug: request.params.slug,
        });

        const allSegmentsForAnSpecificStudy = Array.from(
          db.segmentProgresses as any
        ).filter(
          (segmentProgress: any) => segmentProgress.studyId === study.id
        );

        const data = Array.from(allSegmentsForAnSpecificStudy).slice(
          cursor * number,
          cursor * number + number
        );

        const nextData = Array.from(allSegmentsForAnSpecificStudy).slice(
          (cursor + 1) * number,
          (cursor + 1) * number + number
        );

        return {
          data,
          pagination: {
            nextCursor: nextData.length ? String(cursor + 1) : null,
            total: allSegmentsForAnSpecificStudy.length,
            from: cursor * number + 1,
            to: Math.min(
              cursor * number + number,
              allSegmentsForAnSpecificStudy.length
            ),
          },
        };
      });
    },
  });

  return server;
};

export const createStudyResources = (
  server: InstanceType<typeof Server>,
  numStudyResources: number
) =>
  Array.from({ length: numStudyResources }, () =>
    createStudyResource(server, {
      createdAt: 1604530800000,
    })
  );

export const createStudyResource = (
  server: InstanceType<typeof Server>,
  {
    name,
    slug,
    createdAt,
  }: {
    name?: string;
    slug?: string;
    createdAt?: number;
  } = {}
) => {
  const study = createFakeStudy({
    creationDate: Date.now(),
    desiredParticipants: 24000,
    numOfDifferentStrata: 10,
    desiredParticipantsPerStrata: 2400,
    totalHoursOfData: 24,
  });

  const studyResource: StudyResource = {
    id: study.id,
    name: name || study.name,
    slug: slug || study.slug,
    createdAt: createdAt || study.createdAt,
  };

  server.create('study', studyResource);

  return studyResource;
};

export const createStudyProgressResource = (
  server: InstanceType<typeof Server>,
  {
    study,
    progress,
  }: {
    study: StudyResource;
    progress: StudyProgressResource;
  }
) => {
  server.create('studyProgress', {
    ...progress,
    id: chance.guid({ version: 4 }),
    studyId: study.id,
  });
};

export const createSegmentProgressResource = (
  server: InstanceType<typeof Server>,
  {
    study,
    segmentProgress,
  }: {
    study: StudyResource;
    segmentProgress: StudySegmentProgressResource;
  }
) => {
  server.create('segmentProgress', {
    ...segmentProgress,
    id: chance.guid({ version: 4 }),
    studyId: study.id,
  });
};
