import Chance from 'chance';
import { Model, Server, Response, Request } from 'miragejs';
import { createFakeStudy } from './fixtures/study';
import {
  StudyProgressResource,
  StudySegmentProgressResource,
  StudyResource,
} from './types/study';
import { isValidNumber } from './helpers/numbers';
import { createSlugFor } from './helpers/strings';
import { lastValue } from './helpers/arrays';

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

      const randomStudyResources = createStudyResources(server, 8);

      [...staticStudyResources, ...randomStudyResources].forEach(
        studyResource => {
          const aDayInMilliseconds = 24 * 60 * 60 * 1000;
          const dateTimeFrom24DaysAgo = Date.now() - aDayInMilliseconds * 24;

          const fakeStudy = createFakeStudy({
            creationDate: dateTimeFrom24DaysAgo,
            desiredParticipants: 48000,
            numOfDifferentStrata: 20,
            desiredParticipantsPerStrata: 2400,
            totalDaysOfData: 24,
          });

          fakeStudy.studyProgressList.forEach(progress => {
            createStudyProgressResource(server, {
              study: studyResource,
              progress,
            });
          });

          fakeStudy.stratumProgressList.forEach(stratumProgress => {
            createSegmentProgressResource(server, {
              study: studyResource,
              segmentProgress: stratumProgress,
            });
          });
        }
      );
    },

    routes() {
      this.namespace = 'api';
      this.timing = 750;

      this.get('/studies', ({ db }, request) => {
        if (!isAuthenticatedRequest(request)) {
          return unauthorizedResponse;
        }

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
        if (!isAuthenticatedRequest(request)) {
          return unauthorizedResponse;
        }

        const study = (db.studies as any).findBy({ slug: request.params.slug });

        return {
          data: study,
        };
      });

      this.get('/studies/:slug/segments-progress', ({ db }, request) => {
        if (!isAuthenticatedRequest(request)) {
          return unauthorizedResponse;
        }

        const study: StudyResource = (db.studies as any).findBy({
          slug: request.params.slug,
        });

        const allSegmentsForAnSpecificStudy = Array.from(
          db.segmentProgresses as any
        ).filter(
          (segmentProgress: any) => segmentProgress.studyId === study.id
        ) as StudySegmentProgressResource[];

        const data = allSegmentsForAnSpecificStudy.reduce((acc, segment) => {
          if (acc.length === 0) {
            return [
              {
                segments: [segment],
                datetime: segment.datetime,
              },
            ];
          }

          const hasDatetimeChanged =
            lastValue(acc).datetime !== segment.datetime;

          if (hasDatetimeChanged) {
            acc.push({
              segments: [segment],
              datetime: segment.datetime,
            });
          } else {
            lastValue(acc).segments.push(segment);
          }

          return acc;
        }, [] as { segments: StudySegmentProgressResource[]; datetime: number }[]);

        return {
          data,
        };
      });

      this.passthrough(`https://${process.env.REACT_APP_AUTH0_DOMAIN}/**`);
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
    totalDaysOfData: 24,
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

const isAuthenticatedRequest = (request: Request) =>
  (request.requestHeaders.authorization || '').slice(7) !== '';

const unauthorizedResponse = new Response(
  401,
  { 'content-type': 'application/json' },
  {
    error: 'Unauthorized',
  }
);
