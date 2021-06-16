export interface Study {
  id: string;
  name: string;
  slug: string;
  createdAt: number;
  studyProgressList: StudyProgress[];
  stratumProgressList: StratumProgress[];
}

export interface StudyProgress {
  id: string;
  datetime: number;
  desiredParticipants?: number;
  currentParticipants: number;
  expectedParticipants: number;
  currentAverageDeviation: number;
  expectedAverageDeviation: number;
}

export interface StratumProgress {
  id: string;
  name: string;
  datetime: number;
  desiredPercentage: number;
  currentPercentage: number;
  expectedPercentage: number;
  percentageDeviationFromGoal: number;
  desiredParticipants?: number;
  expectedParticipants: number;
  currentParticipants: number;
  currentBudget: number;
  currentPricePerParticipant: number;
}
