import { ApiResponse } from './api';

export interface AccountsApiResponse extends ApiResponse<AccountResource[]> {}

export interface AccountResource {
  id?: string;
  name: string;
  slug: string;
  authType: string;
}
