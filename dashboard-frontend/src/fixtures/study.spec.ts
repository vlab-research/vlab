import { createFakeStudy } from './study';

type Study = ReturnType<typeof createFakeStudy>;
type StratumProgress = Study['stratumProgressList'][number];
type StudyProgress = Study['studyProgressList'][number];

describe('FakeStudyBuilder', () => {
  let study: Study;
  const studyCreationDate = 1623497646531;
  const desiredParticipants = 24000;

  beforeEach(() => {
    study = createFakeStudy({
      creationDate: studyCreationDate,
      desiredParticipants,
      numOfDifferentStrata: 2,
      desiredParticipantsPerStrata: 12000,
      totalDaysOfData: 2,
    });
  });

  it('returns a Study when all required data is provided', () => {
    expect(study).toEqual({
      id: expect.anything(),
      name: expect.anything(),
      objective: expect.anything(),
      optimization_goal: expect.anything(),
      destination_type: expect.anything(),
      page_id: expect.anything(),
      instagram_id: expect.anything(),
      min_budget: expect.anything(),
      opt_window: expect.anything(),
      ad_account: expect.anything(),
      country: expect.anything(),
      slug: expect.anything(),
      createdAt: studyCreationDate,
      studyProgressList: expect.anything(),
      stratumProgressList: expect.anything(),
    });
    expect(study.studyProgressList.length).toBe(3);
    expect(study.stratumProgressList.length).toBe(6);
  });

  describe('StudyProgress over time', () => {
    let first: StudyProgress;
    let second: StudyProgress;
    let third: StudyProgress;
    beforeEach(() => {
      [first, second, third] = study.studyProgressList;
    });

    it('currentParticipants augmented', () => {
      expect(first.currentParticipants).toBe(0);
      expect(second.currentParticipants).toBeGreaterThan(
        first.currentParticipants
      );
      expect(third.currentParticipants).toBeGreaterThan(
        second.currentParticipants
      );
    });

    it('expectedParticipants augmented', () => {
      expect(first.expectedParticipants).toBe(0);
      expect(second.expectedParticipants).toBeGreaterThan(
        first.expectedParticipants
      );
      expect(third.expectedParticipants).toBeGreaterThan(
        second.expectedParticipants
      );
    });

    it('datetime augmented', () => {
      const oneDayInMilliseconds = 24 * 60 * 60 * 1000;
      expect(first.datetime).toBe(studyCreationDate);
      expect(second.datetime).toBe(first.datetime + oneDayInMilliseconds);
      expect(third.datetime).toBe(second.datetime + oneDayInMilliseconds);
    });

    it('currentAverageDeviation changed', () => {
      expect(first.currentAverageDeviation).toBe(0);
      expect(second.currentAverageDeviation).not.toBe(
        first.currentAverageDeviation
      );
      expect(third.currentAverageDeviation).not.toBe(
        second.currentAverageDeviation
      );
    });

    it('expectedAverageDeviation changed', () => {
      expect(first.expectedAverageDeviation).toBe(0);
      expect(second.expectedAverageDeviation).not.toBe(
        first.expectedAverageDeviation
      );
      expect(third.expectedAverageDeviation).not.toBe(
        second.expectedAverageDeviation
      );
    });

    it('id changed', () => {
      expect(first.id).toBeDefined();
      expect(second.id).not.toBe(first.id);
      expect(third.id).not.toBe(second.id);
    });

    it('desiredParticipants remained the same', () => {
      expect(first.desiredParticipants).toBe(desiredParticipants);
      expect(second.desiredParticipants).toBe(desiredParticipants);
      expect(third.desiredParticipants).toBe(desiredParticipants);
    });
  });

  describe('StratumProgress over time', () => {
    let first: StratumProgress[];
    let second: StratumProgress[];
    let third: StratumProgress[];

    beforeEach(() => {
      first = study.stratumProgressList.slice(0, 2);
      second = study.stratumProgressList.slice(2, 4);
      third = study.stratumProgressList.slice(4, 6);
    });

    it('datetime augmented', () => {
      const oneDayInMilliseconds = 24 * 60 * 60 * 1000;

      first.forEach(({ datetime }, i) => {
        expect(datetime).toBe(studyCreationDate);
      });

      second.forEach(({ datetime }, i) => {
        expect(datetime).toBe(first[i].datetime + oneDayInMilliseconds);
      });

      third.forEach(({ datetime }, i) => {
        expect(datetime).toBe(second[i].datetime + oneDayInMilliseconds);
      });
    });

    it('currentPercentage changed', () => {
      first.forEach(({ currentPercentage }, i) => {
        expect(currentPercentage).toBe(0);
      });

      second.forEach(({ currentPercentage }, i) => {
        expect(currentPercentage).not.toBe(first[i].currentPercentage);
      });

      third.forEach(({ currentPercentage }, i) => {
        expect(currentPercentage).not.toBe(second[i].currentPercentage);
      });
    });

    it('currentParticipants augmented', () => {
      first.forEach(({ currentParticipants }, i) => {
        expect(currentParticipants).toBe(0);
      });

      second.forEach(({ currentParticipants }, i) => {
        expect(currentParticipants).toBeGreaterThan(
          first[i].currentParticipants
        );
      });

      third.forEach(({ currentParticipants }, i) => {
        expect(currentParticipants).toBeGreaterThan(
          second[i].currentParticipants
        );
      });
    });

    it('id changed', () => {
      first.forEach(({ id }, i) => {
        expect(id).toBeDefined();
      });

      second.forEach(({ id }, i) => {
        expect(id).not.toBe(first[i].id);
      });

      third.forEach(({ id }, i) => {
        expect(id).not.toBe(second[i].id);
      });
    });

    it('name remained the same', () => {
      first.forEach(({ name }, i) => {
        expect(name).toBeDefined();
      });

      second.forEach(({ name }, i) => {
        expect(name).toBe(first[i].name);
      });

      third.forEach(({ name }, i) => {
        expect(name).toBe(second[i].name);
      });
    });

    it('expectedPercentage changed', () => {
      first.forEach(({ expectedPercentage }, i) => {
        expect(expectedPercentage).toBe(0);
      });

      second.forEach(({ expectedPercentage }, i) => {
        expect(expectedPercentage).not.toBe(first[i].expectedPercentage);
      });

      third.forEach(({ expectedPercentage }, i) => {
        expect(expectedPercentage).not.toBe(second[i].expectedPercentage);
      });
    });

    it('expectedParticipants changed', () => {
      first.forEach(({ expectedParticipants }, i) => {
        expect(expectedParticipants).toBe(0);
      });

      second.forEach(({ expectedParticipants }, i) => {
        expect(expectedParticipants).not.toBe(first[i].expectedParticipants);
      });

      third.forEach(({ expectedParticipants }, i) => {
        expect(expectedParticipants).not.toBe(second[i].expectedParticipants);
      });
    });

    it('percentageDeviationFromGoal changed', () => {
      first.forEach(({ percentageDeviationFromGoal }, i) => {
        expect(percentageDeviationFromGoal).toBe(0);
      });

      second.forEach(({ percentageDeviationFromGoal }, i) => {
        expect(percentageDeviationFromGoal).not.toBe(
          first[i].percentageDeviationFromGoal
        );
      });

      third.forEach(({ percentageDeviationFromGoal }, i) => {
        expect(percentageDeviationFromGoal).not.toBe(
          second[i].percentageDeviationFromGoal
        );
      });
    });

    it('currentPricePerParticipant remained/changed to one of: 100, 200, 300', () => {
      first.forEach(({ currentPricePerParticipant }) => {
        expect(currentPricePerParticipant).toBe(0);
      });

      second.forEach(({ currentPricePerParticipant }) => {
        expect([100, 200, 300].includes(currentPricePerParticipant)).toBe(true);
      });

      third.forEach(({ currentPricePerParticipant }) => {
        expect([100, 200, 300].includes(currentPricePerParticipant)).toBe(true);
      });
    });

    it('desiredPercentage remained the same', () => {
      first.forEach(({ desiredPercentage }, i) => {
        expect(desiredPercentage).toBe(50);
      });

      second.forEach(({ desiredPercentage }, i) => {
        expect(desiredPercentage).toBe(50);
      });

      third.forEach(({ desiredPercentage }, i) => {
        expect(desiredPercentage).toBe(50);
      });
    });

    it('desiredParticipants remained the same', () => {
      first.forEach(({ desiredParticipants }, i) => {
        expect(desiredParticipants).toBe(12000);
      });

      second.forEach(({ desiredParticipants }, i) => {
        expect(desiredParticipants).toBe(12000);
      });

      third.forEach(({ desiredParticipants }, i) => {
        expect(desiredParticipants).toBe(12000);
      });
    });

    it('currentBudget remained the same', () => {
      first.forEach(({ currentBudget }, i) => {
        expect(currentBudget).toBeDefined();
      });

      second.forEach(({ currentBudget }, i) => {
        expect(currentBudget).toBe(first[i].currentBudget);
      });

      third.forEach(({ currentBudget }, i) => {
        expect(currentBudget).toBe(second[i].currentBudget);
      });
    });
  });
});
