export interface Study {
  id: string;
  name: string;
  slug: string;
  createdAt: string;
  studyProgressList: StudyProgress[];
  stratumProgressList: StratumProgress[];
}

interface StudyProgress {
  id: string;
  datetime: string;
  currentParticipants: number;
  expectedParticipants: number;
  currentAverageDeviation: number;
  expectedAverageDeviation: number;
}

interface StratumProgress {
  id: string;
  name: string;
  datetime: string;
  desiredPercentage: number;
  currentPercentage: number;
  expectedPercentage: number;
  percentageDeviationFromGoal: number;
  desiredParticipants: number;
  currentParticipants: number;
  currentBudget: number;
  currentPricePerParticipant: number;
}