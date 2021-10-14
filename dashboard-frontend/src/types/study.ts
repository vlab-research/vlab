import { ApiResponse, PaginatedApiResponse } from './api';

export interface StudiesApiResponse
  extends PaginatedApiResponse<StudyResource[]> {}

export interface StudyApiResponse extends ApiResponse<StudyResource> {}

export interface StudySegmentsProgressApiResponse
  extends ApiResponse<
    {
      segments: StudySegmentProgressResource[];
      datetime: number;
    }[]
  > {}

export interface StudyResource {
  id: string;
  name: string;
  slug: string;
  createdAt: number;
}

export interface StudyProgressResource {
  id: string;
  datetime: number;
  desiredParticipants: number | null;
  currentParticipants: number;
  expectedParticipants: number;
  currentAverageDeviation: number;
  expectedAverageDeviation: number;
}

export interface StudySegmentProgressResource {
  id: string;
  name: string;
  datetime: number;
  currentBudget: number;
  desiredPercentage: number;
  currentPercentage: number;
  expectedPercentage: number;
  desiredParticipants: number | null;
  expectedParticipants: number;
  currentParticipants: number;
  currentPricePerParticipant: number;
  percentageDeviationFromGoal: number;
}
