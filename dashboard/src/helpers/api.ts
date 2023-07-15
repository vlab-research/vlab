import { fetchWithTimeout } from './http';
import {
  CampaignsApiResponse,
  AdsetsApiResponse,
  CreateStudyApiResponse,
  CreateStudyConfApiResponse,
  CreateUserApiResponse,
  StudiesApiResponse,
  StudyApiResponse,
  StudyConfApiResponse,
  StudyConfData,
  StudySegmentsProgressApiResponse,
} from '../types/study';
import querystring from 'querystring';
import { Cursor } from '../types/api';
import {
  AccountsApiResponse,
  AccountApiResponse,
  ConnectedAccount,
  CreateAccountApiResponse,
} from '../types/account';

/**
 * TODO:
 *  Create ApiError and TimeoutError which will be useful to have
 *    when reporting to Sentry or a similar service.
 */

const orgPrefix = () => sessionStorage.getItem('current-vlab-org');

const fetchStudies = ({
  studiesPerPage,
  cursor,
  defaultErrorMessage,
  accessToken,
}: {
  studiesPerPage: number;
  cursor: Cursor;
  defaultErrorMessage: string;
  accessToken: string;
}) => {
  // TODO: make general (move to useAuthenticatedAPI) -
  //       automatically remove null/undefined params
  //       which requires changing the current method
  //       of declaring the function params/defaults
  const route = `/${orgPrefix()}/studies`;
  const params: any = { number: studiesPerPage };
  if (cursor) {
    params['cursor'] = cursor;
  }
  const q = querystring.encode(params);
  const path = `${route}?${q}`;

  return apiRequest<StudiesApiResponse>(path, {
    defaultErrorMessage,
    accessToken,
  });
};

const fetchStudy = ({
  slug,
  accessToken,
}: {
  slug: string;
  accessToken: string;
}) =>
  apiRequest<StudyApiResponse>(`/${orgPrefix()}/studies/${slug}`, {
    accessToken,
  }).then(({ data }) => data);

const fetchStudySegmentsProgress = ({
  slug,
  accessToken,
}: {
  slug: string;
  accessToken: string;
}) =>
  apiRequest<StudySegmentsProgressApiResponse>(
    `/${orgPrefix()}/studies/${slug}/segments-progress`,
    { accessToken }
  );

const createUser = ({ accessToken }: { accessToken: string }) => {
  const userCreatedStatusCode = 201;
  const userAlreadyExistsStatusCode = 200;

  return apiRequest<CreateUserApiResponse>('/users', {
    accessToken,
    method: 'POST',
    expectedStatusCodes: [userCreatedStatusCode, userAlreadyExistsStatusCode],
  });
};

const createFacebookAccount = ({
  accessToken,
  code,
}: {
  accessToken: string;
  code: string;
}) => {
  return apiRequest<AccountApiResponse>('/facebook/token', {
    accessToken,
    method: 'POST',
    expectedStatusCodes: [201],
    body: { code },
  });
};

const createStudy = ({
  name,
  accessToken,
}: {
  name: string;
  accessToken: string;
}) =>
  apiRequest<CreateStudyApiResponse>(`/${orgPrefix()}/studies`, {
    accessToken,
    method: 'POST',
    body: { name },
  });

const createStudyConf = ({
  data,
  studySlug,
  accessToken,
}: {
  data: StudyConfData;
  studySlug: string;
  accessToken: string;
}) =>
  apiRequest<CreateStudyConfApiResponse>(
    `/${orgPrefix()}/studies/${studySlug}/conf`,
    {
      accessToken,
      method: 'POST',
      body: data,
    }
  );

const deleteDestination = ({
  data,
  studySlug,
  accessToken,
}: {
  data: StudyConfData;
  studySlug: string;
  accessToken: string;
}) =>
  apiRequest<CreateStudyConfApiResponse>(
    `/${orgPrefix()}/studies/${studySlug}/conf`,
    {
      accessToken,
      method: 'POST',
      body: data,
    }
  );

const fetchStudyConf = ({
  studySlug,
  accessToken,
}: {
  studySlug: string;
  accessToken: string;
}) =>
  apiRequest<StudyConfApiResponse>(
    `/${orgPrefix()}/studies/${studySlug}/conf`,
    {
      accessToken,
    }
  ).then(({ data }) => data);

const fetchAccounts = ({
  defaultErrorMessage,
  accessToken,
  type,
}: {
  defaultErrorMessage: string;
  accessToken: string;
  type?: string;
}) =>
  apiRequest<AccountsApiResponse>(`/accounts`, {
    defaultErrorMessage,
    queryParams: type ? { type } : undefined,
    accessToken,
  });


const createAccount = ({
  name,
  authType,
  connectedAccount,
  accessToken,
}: {
  name: string;
  authType: string;
  connectedAccount: ConnectedAccount;
  accessToken: string;
}) =>
  apiRequest<CreateAccountApiResponse>('/accounts', {
    accessToken,
    method: 'POST',
    body: { name, authType, connectedAccount },
  });

const deleteAccount = ({
  name,
  authType,
  accessToken,
}: {
  name: string;
  authType: string;
  accessToken: string;
}) =>
  apiRequest<void>('/accounts', {
    accessToken,
    method: 'DELETE',
    body: { name, authType },
  });

const apiRequest = async <ApiResponse>(
  path: string,
  {
    defaultErrorMessage = 'Something went wrong.',
    method = 'GET',
    accessToken = '',
    body,
    queryParams,
    expectedStatusCodes,
  }: {
    defaultErrorMessage?: string;
    method?: 'GET' | 'POST' | 'DELETE';
    accessToken: string;
    body?: object;
    queryParams?: any;
    expectedStatusCodes?: number[];
  }
) => {
  const requestBody = body ? JSON.stringify(body) : undefined;
  const requestHeaders: HeadersInit = {
    Authorization: `Bearer ${accessToken}`,
  };
  if (requestBody) {
    requestHeaders['Content-Type'] = 'application/json';
  }
  if (queryParams) {
    path = `${path}?${querystring.encode(queryParams)}`;
  }
  try {
    const response = await fetchWithTimeout(path, {
      timeout: 10000,
      headers: requestHeaders,
      method,
      body: requestBody,
    });

    const isExpectedResponse = expectedStatusCodes
      ? expectedStatusCodes.includes(response.status)
      : response.ok;

    if (!isExpectedResponse) {
      throw new Error(await getErrorMessageFor(response, defaultErrorMessage));
    }

    // 204 is no content so we just return an empty type
    if (response.status === 204) {
      return {} as Promise<ApiResponse>;
    }

    return response.json() as Promise<ApiResponse>;
  } catch (err: any) {
    if (err.name === 'AbortError') {
      throw new Error(defaultErrorMessage);
    }

    throw err;
  }
};

const facebookRequest = async <ApiResponse>(
  path: string,
  {
    defaultErrorMessage = 'Something went wrong.',
    method = 'GET',
    body,
    queryParams,
    accessToken,
    expectedStatusCodes,
  }: {
    defaultErrorMessage?: string;
    method?: 'GET' | 'POST' | 'DELETE';
    body?: object;
    accessToken: string;
    queryParams?: any;
    expectedStatusCodes?: number[];
  }
) => {
  const requestBody = body ? JSON.stringify(body) : undefined;
  const requestHeaders: HeadersInit = {};
  if (requestBody) {
    requestHeaders['Content-Type'] = 'application/json';
  }

  //TODO Handle when access token is not set
  queryParams['access_token'] = accessToken;
  const q = querystring.encode(queryParams);
  path = `${path}?${q}`;

  //TODO make this configurabel (i.e ENV variable)
  const baseURL = `https://graph.facebook.com/v17.0`;

  try {
    const response = await fetchWithTimeout(path, {
      timeout: 10000,
      headers: requestHeaders,
      method,
      body: requestBody,
      baseURL: baseURL,
    });

    const isExpectedResponse = expectedStatusCodes
      ? expectedStatusCodes.includes(response.status)
      : response.ok;

    if (!isExpectedResponse) {
      throw new Error(await getErrorMessageFor(response, defaultErrorMessage));
    }

    // 204 is no content so we just return an empty type
    if (response.status === 204) {
      return {} as Promise<ApiResponse>;
    }

    return response.json() as Promise<ApiResponse>;
  } catch (err: any) {
    if (err.name === 'AbortError') {
      throw new Error(defaultErrorMessage);
    }

    throw err;
  }
};

export const fetchCampaigns = ({
  limit,
  cursor,
  accessToken,
  accountNumber,
  defaultErrorMessage,
}: {
  limit: number;
  cursor: Cursor;
  accessToken: string;
  accountNumber: string;
  defaultErrorMessage: string;
}) => {
  const params: any = {
    limit,
    pretty: 0,
    fields: 'name, id',
    access_token: accessToken,
  };
  if (cursor) {
    params['cursor'] = cursor;
  }

  const path = `/act_${accountNumber}/campaigns`;

  return facebookRequest<CampaignsApiResponse>(path, {
    queryParams: params,
    accessToken,
    defaultErrorMessage,
  });
};

export const fetchAdsets = async ({
  limit,
  cursor,
  accessToken,
  campaign,
  defaultErrorMessage,
}: {
  limit: number;
  cursor: Cursor;
  accessToken: string;
  campaign: string;
  defaultErrorMessage: string;
}) => {
  const params: any = {
    limit,
    pretty: 0,
    fields: 'name, id, targeting',
    access_token: accessToken,
  };
  if (cursor) {
    params['cursor'] = cursor;
  }

  const path = `/${campaign}/adsets`;

  return facebookRequest<AdsetsApiResponse>(path, {
    queryParams: params,
    accessToken,
    defaultErrorMessage,
  });
};

const getErrorMessageFor = async (
  errorResponse: Response,
  defaultErrorMessage: string
): Promise<string> => {
  const containsJSON = errorResponse.headers
    .get('content-type')
    ?.includes('application/json');

  if (!containsJSON) {
    return defaultErrorMessage;
  }

  const responseBody = await errorResponse.json();

  return responseBody.error || defaultErrorMessage;
};

export const authenticatedApiCalls = {
  fetchStudies,
  fetchStudy,
  fetchStudySegmentsProgress,
  createUser,
  createStudy,
  createStudyConf,
  deleteDestination,
  fetchStudyConf,
  fetchAccounts,
  createAccount,
  deleteAccount,
  createFacebookAccount,
};
