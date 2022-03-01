import { fetchWithTimeout } from './http';
import {
  CreateStudyApiResponse,
  CreateUserApiResponse,
  StudiesApiResponse,
  StudyApiResponse,
  StudySegmentsProgressApiResponse,
} from '../types/study';
import { Cursor } from '../types/api';

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
}) =>
  apiRequest<StudiesApiResponse>(
    `/api/studies?number=${studiesPerPage}&cursor=${cursor}`,
    {
      defaultErrorMessage,
      accessToken,
    }
  );

const fetchStudy = ({
  slug,
  accessToken,
}: {
  slug: string;
  accessToken: string;
}) =>
  apiRequest<StudyApiResponse>(`/api/studies/${slug}`, { accessToken }).then(
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
    `/api/studies/${slug}/segments-progress`,
    { accessToken }
  );

const createUser = ({ accessToken }: { accessToken: string }) => {
  const userCreatedStatusCode = 201;
  const userAlreadyExistsStatusCode = 422;

  return apiRequest<CreateUserApiResponse>('/api/users', {
    accessToken,
    method: 'POST',
    expectedStatusCodes: [userCreatedStatusCode, userAlreadyExistsStatusCode],
  });
};

const createStudy = ({
  name,
  accessToken,
}: {
  name: string;
  accessToken: string;
}) =>
  apiRequest<CreateStudyApiResponse>('/api/studies', {
    accessToken,
    method: 'POST',
    body: { name },
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
    method?: 'GET' | 'POST';
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

    return response.json() as Promise<ApiResponse>;
  } catch (err) {
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
};
