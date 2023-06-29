import { ApiResponse, PaginatedApiResponse } from './api';
import { LocalFormData } from './conf';

export interface StudiesApiResponse
  extends PaginatedApiResponse<StudyResource[]> {}

export interface StudiesApiResponse
  extends PaginatedApiResponse<StudyResource[]> {}

export interface StudyApiResponse extends ApiResponse<StudyResource> {}

export interface StudyConfApiResponse extends ApiResponse<StudyConfData> {}

export interface CreateStudyApiResponse extends ApiResponse<StudyResource> {}

export interface CreateStudyConfApiResponse
  extends ApiResponse<StudyConfData> {}

export type StudyConfData = Record<string, LocalFormData>;

export interface StudyResource {
  id: string;
  name: string;
  slug: string;
  createdAt: number;
}

export interface StudySegmentsProgressApiResponse
  extends ApiResponse<
    {
      segments: StudySegmentProgressResource[];
      datetime: number;
    }[]
  > {}

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

export interface Org {
  name: string;
  id: string;
}

export interface CreateUserApiResponse
  extends ApiResponse<{
    id: string;
    orgs: Org[];
  }> {}


interface PaginatedFacebookResponse<Data> {
  data: Data;
  paging: {
    before: string;
    after: string;
  }
}


export interface Campaign {
  id: string;
  name: string;
}


export interface Adset {
  id: string;
  name: string;
  targeting: any;
}

export interface CampaignsApiResponse extends PaginatedFacebookResponse<Campaign[]> {}

export interface AdsetsApiResponse extends PaginatedFacebookResponse<Adset[]> {}
