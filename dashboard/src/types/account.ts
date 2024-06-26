import { ApiResponse } from './api';

export interface AccountsApiResponse extends ApiResponse<Account[]> {}
export interface AccountApiResponse extends ApiResponse<Account> {}

export interface CreateAccountApiResponse extends ApiResponse<Account> {}

export interface CreateFacebookAccount {
  code: string;
}

export interface Account {
  id?: string;
  name: string;
  authType: string;
  connectedAccount?: ConnectedAccount;
}

export interface ConnectedAccount {
  createdAt: number;
  credentials: object;
}

export interface TypeformAccount extends ConnectedAccount {
  credentials: {
    key: string;
  };
}

export interface FlyAccount extends ConnectedAccount {
  credentials: {
    api_key: string;
  };
}

export interface AlchemerAccount extends ConnectedAccount {
  credentials: {
    api_token: string;
    api_token_secret: string;
  };
}

export interface FacebookAccount extends ConnectedAccount {
  credentials: {
    token: string;
  };
}
