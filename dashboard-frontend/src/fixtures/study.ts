import Chance from 'chance';
import { calculatePercentage, round } from '../helpers/numbers';
import { createSlugFor } from '../helpers/strings';
import { lastValue } from '../helpers/arrays';
import {
  StudyResource,
  StudyProgressResource,
  StudySegmentProgressResource,
} from '../types/study';
import {
  computeStudyProgressDataFrom,
  computeCurrentParticipantsFrom,
  computeExpectedParticipantsFrom,
} from '../helpers/study';

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
  totalDaysOfData,
}: {
  creationDate: number;
  desiredParticipants: number;
  numOfDifferentStrata: number;
  desiredParticipantsPerStrata: number;
  totalDaysOfData: number;
}) => {
  let study = createInitialStudyData({
    creationDate,
    desiredParticipants,
    numOfDifferentStrata,
    desiredParticipantsPerStrata,
  });

  for (let days = 1; days <= totalDaysOfData; days++) {
    const lastStudyProgress = lastValue(study.studyProgressList);
    const oneDayInMilliseconds = 24 * 60 * 60 * 1000;

    study = updateStudyData(study, {
      datetime: lastStudyProgress.datetime + oneDayInMilliseconds,
      maxOfNewParticipants: desiredParticipants / totalDaysOfData,
      numOfDifferentStrata: numOfDifferentStrata,
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
  const objective = `Objective for ${studyName} Study`;
  const optimization_goal = `Optimization goal for ${studyName} Study`;
  const destination_type = `Destination type for ${studyName} Study`;
  const page_id = chance.guid();
  const instagram_id = chance.fbid();
  const min_budget = chance.floating({ min: 1, max: 10000 });
  const opt_window = chance.floating({ min: 0, max: 14 });
  const ad_account = chance.fbid();
  const country = chance.country({ full: true });
  const studySlug = createSlugFor(studyName);
  const studyCreationDate = creationDate;

  const study: Study = {
    id: chance.guid({ version: 4 }),
    name: studyName,
    objective: objective,
    optimization_goal: optimization_goal,
    destination_type: destination_type,
    page_id: page_id,
    instagram_id: instagram_id,
    min_budget: min_budget,
    opt_window: opt_window,
    ad_account: ad_account,
    country: country,
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
      percentageDeviationFromGoal: 0,
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
  }: {
    maxOfNewParticipants: number;
    numOfDifferentStrata: number;
    datetime: number;
  }
): Study => {
  const lastStratumProgressList = study.stratumProgressList.slice(
    -numOfDifferentStrata
  );

  let newStratumProgressList = lastStratumProgressList.map(
    (stratumProgress, index) =>
      updateStratumProgress(stratumProgress, {
        newParticipants: chance.natural({
          min: 1,
          max: Math.floor(maxOfNewParticipants / numOfDifferentStrata),
        }),
        datetime,
      })
  );
  const currentParticipantsForStudy = computeCurrentParticipantsFrom(
    newStratumProgressList
  );
  const expectedParticipantsPerStudy = computeExpectedParticipantsFrom(
    newStratumProgressList
  );
  newStratumProgressList = newStratumProgressList.map(newStratumProgress => {
    const currentPercentage = round(
      (newStratumProgress.currentParticipants / currentParticipantsForStudy) *
        100
    );
    const percentageDeviationFromGoal = round(
      Math.abs(newStratumProgress.desiredPercentage - currentPercentage)
    );

    return {
      ...newStratumProgress,
      currentPercentage,
      percentageDeviationFromGoal,
      expectedPercentage: round(
        (newStratumProgress.expectedParticipants /
          expectedParticipantsPerStudy) *
          100
      ),
    };
  });

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
  }: {
    newParticipants: number;
    datetime: number;
  }
) => {
  const currentParticipants =
    stratumProgress.currentParticipants + newParticipants;

  const expectedParticipants = Math.floor(
    currentParticipants * chance.pickone([0.9, 1, 1.1])
  );

  return {
    ...stratumProgress,
    id: chance.guid({ version: 4 }),
    datetime,
    currentParticipants,
    expectedParticipants,
    currentPricePerParticipant: chance.pickone([100, 200, 300]),
  };
};

const createRandomSuffix = () =>
  chance.string({
    length: 4,
    pool: 'abcdefghijklmnopqrstuvwxyz',
  });

const createRandomCountrySlug = () =>
  createSlugFor(chance.country({ full: true }).toLowerCase());
