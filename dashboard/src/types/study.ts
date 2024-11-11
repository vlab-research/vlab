import { ApiResponse, PaginatedApiResponse } from './api';
import { GlobalFormData, LocalFormData } from './conf';

export interface StudiesApiResponse
  extends PaginatedApiResponse<StudyResource[]> {}

export interface StudiesApiResponse
  extends PaginatedApiResponse<StudyResource[]> {}

export interface StudyApiResponse extends ApiResponse<StudyResource> {}

export interface StudyConfApiResponse extends ApiResponse<StudyConfData> {}

export interface CreateStudyApiResponse extends ApiResponse<StudyResource> {}

export interface CreateStudyConfApiResponse
  extends ApiResponse<StudyConfData> {}

export interface OptimizeStudyApiResponse
  extends ApiResponse<OptimizeInstruction[]> {}

export interface RunInstructionApiResponse
  extends ApiResponse<RunInstructionResult> {}


export interface CreateApiKeyResponse
  extends ApiResponse<CreateApiKeyResponseData> {}

// TODO: is this right? improve and make more meaningful?
export interface RunInstructionResult {
  timestamp: string;
  node: string;
  action: string;
  params: any;
  id: string | null;
}

export interface OptimizeInstruction {
  node: string;
  action: string;
  params: any;
  id: string | null;
}

export interface CreateApiKeyResponseData {
  name: string;
  id: string;
  token: string;
}

export type StudyConfData = GlobalFormData;
export type SingleStudyConf = LocalFormData;

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

export interface AdAccount {
  account_id: string;
  id: string;
  name: string;
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

export interface Ad {
  id: string;
  name: string;
  actor_id: any;
  asset_feed_spec: any;
  degrees_of_freedom_spec: any;
  effective_instagram_media_id: any;
  effective_instagram_story_id: any;
  effective_object_story_id: any;
  instagram_actor_id: any;
  instagram_user_id: any;
  object_story_spec: any;
  thumbnail_url: any;
}

export interface AdsApiResponse extends PaginatedFacebookResponse<Ad[]> {}

export interface AdAccountsApiResponse extends PaginatedFacebookResponse<AdAccount[]> {}

export interface CampaignsApiResponse extends PaginatedFacebookResponse<Campaign[]> {}

export interface AdsetsApiResponse extends PaginatedFacebookResponse<Adset[]> {}
