import Chance from 'chance';
import {
  calculateAverageDeviation,
  calculatePercentage,
  round,
} from '../helpers/numbers';
import { createSlugFor } from '../helpers/strings';
import { lastValue } from '../helpers/arrays';
import {
  StudyResource,
  StudyProgressResource,
  StudySegmentProgressResource,
} from '../types/study';

interface Study extends StudyResource {
  studyProgressList: StudyProgressResource[];
  stratumProgressList: StudySegmentProgressResource[];
}

const chance = Chance();

export const createFakeStudy = ({
  creationDate,
  desiredParticipants,
  numOfDifferentStrata,
  desiredParticipantsPerStrata,
  totalHoursOfData,
}: {
  creationDate: number;
  desiredParticipants: number;
  numOfDifferentStrata: number;
  desiredParticipantsPerStrata: number;
  totalHoursOfData: number;
}) => {
  let study = createInitialStudyData({
    creationDate,
    desiredParticipants,
    numOfDifferentStrata,
    desiredParticipantsPerStrata,
  });

  for (let hours = 1; hours <= totalHoursOfData; hours++) {
    const lastStudyProgress = lastValue(study.studyProgressList);
    const oneHourInMilliseconds = 3600000;

    study = updateStudyData(study, {
      datetime: lastStudyProgress.datetime + oneHourInMilliseconds,
      maxOfNewParticipants: desiredParticipants / totalHoursOfData,
      numOfDifferentStrata: numOfDifferentStrata,
      desiredParticipants,
    });
  }

  return study;
};

const createInitialStudyData = ({
  creationDate,
  desiredParticipants,
  numOfDifferentStrata,
  desiredParticipantsPerStrata,
}: {
  creationDate: number;
  desiredParticipants: number;
  numOfDifferentStrata: number;
  desiredParticipantsPerStrata: number;
}) => {
  const studyAuthorName = chance.first({ nationality: 'en' });
  const studyName = `${studyAuthorName} ${createRandomSuffix()} Study`;
  const studySlug = createSlugFor(studyName);
  const studyCreationDate = creationDate;

  const study: Study = {
    id: chance.guid({ version: 4 }),
    name: studyName,
    slug: studySlug,
    createdAt: studyCreationDate,
    studyProgressList: [
      {
        id: chance.guid({ version: 4 }),
        datetime: studyCreationDate,
        desiredParticipants,
        currentParticipants: 0,
        expectedParticipants: 0,
        currentAverageDeviation: 0,
        expectedAverageDeviation: 0,
      },
    ],
    stratumProgressList: Array.from({ length: numOfDifferentStrata }, () => ({
      id: chance.guid({ version: 4 }),
      name: `${chance.age()}-${createRandomSuffix()}-${createRandomCountrySlug()}`,
      datetime: studyCreationDate,
      desiredParticipants: desiredParticipantsPerStrata,
      desiredPercentage: calculatePercentage({
        current: desiredParticipantsPerStrata,
        total: desiredParticipants,
      }),
      currentParticipants: 0,
      currentPercentage: 0,
      expectedParticipants: 0,
      expectedPercentage: 0,
      percentageDeviationFromGoal: 100,
      currentBudget: desiredParticipantsPerStrata * 3 * 100,
      currentPricePerParticipant: 0,
    })),
  };

  return study;
};

const updateStudyData = (
  study: Study,
  {
    maxOfNewParticipants,
    numOfDifferentStrata,
    datetime,
    desiredParticipants,
  }: {
    maxOfNewParticipants: number;
    numOfDifferentStrata: number;
    datetime: number;
    desiredParticipants: number;
  }
): Study => {
  const lastStratumProgressList = study.stratumProgressList.slice(
    -numOfDifferentStrata
  );
  const newStratumProgressList = lastStratumProgressList.map(
    (stratumProgress, index) =>
      updateStratumProgress(stratumProgress, {
        newParticipants: chance.natural({
          min: 1,
          max: Math.floor(maxOfNewParticipants / numOfDifferentStrata),
        }),
        datetime,
        desiredParticipants,
      })
  );

  const lastStudyProgressList = lastValue(study.studyProgressList);
  const newStudyProgress: Study['studyProgressList'][number] = {
    ...lastStudyProgressList,
    ...computeStudyProgressDataFrom(newStratumProgressList),
    id: chance.guid({ version: 4 }),
    datetime,
  };

  const newStudy: Study = {
    ...study,
    studyProgressList: [...study.studyProgressList, newStudyProgress],
    stratumProgressList: [
      ...study.stratumProgressList,
      ...newStratumProgressList,
    ],
  };

  return newStudy;
};

const updateStratumProgress = (
  stratumProgress: Study['stratumProgressList'][number],
  {
    newParticipants,
    datetime,
    desiredParticipants,
  }: {
    newParticipants: number;
    datetime: number;
    desiredParticipants: number;
  }
) => {
  const currentParticipants =
    stratumProgress.currentParticipants + newParticipants;

  const currentPercentage = round(
    (currentParticipants / desiredParticipants) * 100
  );

  const expectedParticipants = Math.floor(
    currentParticipants * chance.pickone([0.9, 1, 1.1])
  );

  return {
    ...stratumProgress,
    id: chance.guid({ version: 4 }),
    datetime,
    currentParticipants,
    expectedParticipants,
    currentPercentage,
    expectedPercentage: round(
      (expectedParticipants / desiredParticipants) * 100
    ),
    percentageDeviationFromGoal: round(100 - currentPercentage),
    currentPricePerParticipant: chance.pickone([100, 200, 300]),
  };
};

const computeStudyProgressDataFrom = (
  stratumProgressList: Study['stratumProgressList']
) => ({
  currentParticipants: stratumProgressList.reduce(
    (prev, { currentParticipants }) => prev + currentParticipants,
    0
  ),
  expectedParticipants: stratumProgressList.reduce(
    (prev, { expectedParticipants }) => prev + expectedParticipants,
    0
  ),
  currentAverageDeviation: calculateAverageDeviation(
    stratumProgressList.map(
      ({ percentageDeviationFromGoal }) => percentageDeviationFromGoal
    )
  ),
  expectedAverageDeviation: calculateAverageDeviation(
    stratumProgressList.map(({ expectedPercentage }) =>
      round(100 - expectedPercentage)
    )
  ),
});

const createRandomSuffix = () =>
  chance.string({
    length: 4,
    pool: 'abcdefghijklmnopqrstuvwxyz',
  });

const createRandomCountrySlug = () =>
  createSlugFor(chance.country({ full: true }).toLowerCase());
