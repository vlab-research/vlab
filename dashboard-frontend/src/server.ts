import { Model, Server } from 'miragejs';
import { createFakeStudy } from './fixtures/study';
import { StudyResource } from './types/study';
import { isValidNumber } from './helpers/numbers';

export const makeServer = ({ environment = 'development' } = {}) => {
  let server = new Server({
    environment,

    models: {
      study: Model,
    },

    seeds(server) {
      const today = Date.now();
      const yesterday = Date.now() - 24 * 60 * 60 * 1000;

      [
        {
          name: 'Weekly consume meat',
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
      ].forEach(study => createStudyResource(server, study));

      createStudyResources(server, 34);
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
    },
  });

  return server;
};

export const createStudyResources = (
  server: InstanceType<typeof Server>,
  numStudyResources: number
) => {
  Array.from({ length: numStudyResources }, () =>
    createStudyResource(server, {
      createdAt: 1604530800000,
    })
  );
};

export const createStudyResource = (
  server: InstanceType<typeof Server>,
  {
    name,
    createdAt,
  }: {
    name?: string;
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
    slug: study.slug,
    createdAt: createdAt || study.createdAt,
  };

  server.create('study', studyResource);
};
