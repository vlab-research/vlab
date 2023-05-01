import Chance from 'chance';
import { Model, Server, Response, Request } from 'miragejs';
import { createFakeStudy } from './helpers/studyData';
import {
  StudyProgressResource,
  StudySegmentProgressResource,
  StudyResource,
} from './types/study';
import { isValidNumber } from './helpers/numbers';
import { createSlugFor } from './helpers/strings';
import { lastValue } from './helpers/arrays';
import { Account } from './types/account';

const chance = Chance();

export const makeServer = ({ environment = 'development' } = {}) => {
  let server = new Server({
    environment,

    models: {
      study: Model,
      studyconf: Model,
      studyProgress: Model,
      segmentProgress: Model,
      account: Model,
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

      const connectedAccounts = [
        {
          name: 'fly',
          authType: 'fly',
          connectedAccount: {
            createdAt: today,
            credentials: {
              api_key: 'super_secret',
            },
          },
        },
        {
          name: 'typeform',
          authType: 'typeform',
          connectedAccount: {
            createdAt: yesterday,
            credentials: {
              key: '1233foobar',
            },
          },
        },
      ];

      connectedAccounts.map(account => createAccountResource(server, account));

      const studyconf = {
        general: {
          name: 'most-used-programming-language-for-api-development',
          objective: 'MESSAGES',
          optimization_goal: 'REPLIES',
          destination_type: 'MESSENGER',
          page_id: '1234567898765432',
          min_budget: 1.5,
          opt_window: 48,
          instagram_id: '123456789',
          ad_account: '123456789',
        },
        targeting: null,
        targeting_distribution: null,
        recruitment: {
          end_date: '2022-08-05T00:00:00',
          start_date: '2022-07-26T00:00:00',
          ad_campaign_name: 'vlab-most-used-prog-1',
          budget: 10000,
          max_sample: 1000,
        },
      };
      createStudyConf(server, studyconf);
    },

    routes() {
      this.namespace = 'api';
      this.timing = 750;

      this.post('/users', ({ db }, request) => {
        if (!isAuthenticatedRequest(request)) {
          return unauthorizedResponse;
        }

        return {
          data: {
            id: 'auth0|61916c1dab79c900713936de',
          },
        };
      });

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

        const allStudies = (
          Array.from(db.studies as any) as StudyResource[]
        ).sort((studyA, studyB) => studyB.createdAt - studyA.createdAt);

        const data = allStudies.slice(cursor * number, cursor * number + 10);

        const nextData = allStudies.slice(
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

      this.get('/studies/:slug/conf', ({ db }, request) => {
        if (!isAuthenticatedRequest(request)) {
          return unauthorizedResponse;
        }

        const studyconf = db.studyconfs as any;

        return {
          data: studyconf[0],
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

      this.post('/studies', ({ db }, request) => {
        if (!isAuthenticatedRequest(request)) {
          return unauthorizedResponse;
        }

        const { name } = JSON.parse(request.requestBody);
        const isNameEmpty = name.trim() === '';
        if (isNameEmpty) {
          return new Response(
            400,
            { 'content-type': 'application/json' },
            {
              error: 'The name cannot be empty.',
            }
          );
        }

        const allStudies = Array.from(db.studies as any) as StudyResource[];
        const isNameAlreadyInUse =
          allStudies.filter(
            study => study.name.toLowerCase() === name.toLowerCase()
          ).length > 0;
        if (isNameAlreadyInUse) {
          return new Response(
            409,
            { 'content-type': 'application/json' },
            {
              error: 'The name is already in use.',
            }
          );
        }

        const studyResource: StudyResource = {
          id: chance.guid({ version: 4 }),
          name,
          slug: createSlugFor(name),
          createdAt: Date.now(),
        };

        server.create('study', studyResource);

        return {
          data: studyResource,
        };
      });

      this.get('/accounts', ({ db }, request) => {
        if (!isAuthenticatedRequest(request)) {
          return unauthorizedResponse;
        }

        const data = Array.from(db.accounts as any);

        return {
          data,
        };
      });

      this.post('/accounts', ({ db }, request) => {
        if (!isAuthenticatedRequest(request)) {
          return unauthorizedResponse;
        }

        const { name, authType, connectedAccount } = JSON.parse(
          request.requestBody
        );

        const credentials = Object.values(connectedAccount.credentials);

        const credentialsEmpty = credentials.some(
          (credential: any) => credential.trim() === ''
        );

        if (credentialsEmpty) {
          return new Response(
            400,
            { 'content-type': 'application/json' },
            {
              error: 'Field cannot be empty.',
            }
          );
        }

        const account: Account = {
          name,
          authType,
          connectedAccount,
        };

        server.create('account', account);

        return {
          data: account,
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

export const createStudyConf = (
  server: InstanceType<typeof Server>,
  studyconf: any
) => {
  server.create('studyconf', {
    ...studyconf,
  });
};

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

export const createAccountResource = (
  server: InstanceType<typeof Server>,
  accountResource: Account
) => {
  server.create('account', accountResource);

  return accountResource;
};

const isAuthenticatedRequest = (request: Request) =>
  (request.requestHeaders.Authorization || '').slice(7) !== '';

const unauthorizedResponse = new Response(
  401,
  { 'content-type': 'application/json' },
  {
    error: 'Unauthorized',
  }
);
