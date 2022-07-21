import { ApiResponse } from './api';

export interface AccountApiResponse extends ApiResponse<AccountResource> {}

export interface AccountResource {
  id?: string;
  name: string;
  slug: string;
  authType: string;
}
