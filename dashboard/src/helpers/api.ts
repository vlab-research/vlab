import { fetchWithTimeout } from './http';
import {
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
  const route = `/studies`;
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
  apiRequest<StudyApiResponse>(`/studies/${slug}`, { accessToken }).then(
    ({ data }) => data
  );

const fetchStudySegmentsProgress = ({
  slug,
  accessToken,
}: {
  slug: string;
  accessToken: string;
}) =>
  apiRequest<StudySegmentsProgressApiResponse>(
    `/studies/${slug}/segments-progress`,
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

const generateFacebookAccount = ({
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
  apiRequest<CreateStudyApiResponse>('/studies', {
    accessToken,
    method: 'POST',
    body: { name },
  });

const createStudyConf = ({
  studySlug,
  accessToken,
  data,
}: {
  data: StudyConfData;
  studySlug: string;
  accessToken: string;
}) =>
  apiRequest<CreateStudyConfApiResponse>(`/studies/${studySlug}/conf`, {
    accessToken,
    method: 'POST',
    body: data,
  });

const fetchStudyConf = ({
  studySlug,
  accessToken,
}: {
  studySlug: string;
  accessToken: string;
}) =>
  apiRequest<StudyConfApiResponse>(`/studies/${studySlug}/conf`, {
    accessToken,
  }).then(({ data }) => data);

const fetchAccounts = ({
  defaultErrorMessage,
  accessToken,
}: {
  defaultErrorMessage: string;
  accessToken: string;
}) =>
  apiRequest<AccountsApiResponse>(`/accounts`, {
    defaultErrorMessage,
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
  url: string,
  {
    defaultErrorMessage = 'Something went wrong.',
    method = 'GET',
    accessToken = '',
    body,
    expectedStatusCodes,
  }: {
    defaultErrorMessage?: string;
    method?: 'GET' | 'POST' | 'DELETE';
    accessToken: string;
    body?: object;
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

  try {
    const response = await fetchWithTimeout(url, {
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

    // 204 is no content so we just return and empty
    // type
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
  fetchStudyConf,
  fetchAccounts,
  createAccount,
  deleteAccount,
  generateFacebookAccount,
};