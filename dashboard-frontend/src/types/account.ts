import { ApiResponse } from './api';

export interface AccountsApiResponse extends ApiResponse<AccountResource[]> {}
export interface AccountApiResponse extends ApiResponse<AccountResource> {}

export interface CreateAccountApiResponse
  extends ApiResponse<AccountResource> {}

export interface AccountResource {
  id?: string;
  name: string;
  authType: string;
  connectedAccount?: ConnectedAccountResource;
}

export interface ConnectedAccountResource {
  createdAt: number;
}

export interface TokenAccountResource extends ConnectedAccountResource {
  credentials?: {
    token: string;
  };
}

export interface SecretAccountResource extends ConnectedAccountResource {
  credentials?: {
    clientId: string;
    clientSecret: string;
  };
}
