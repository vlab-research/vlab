import { fetchWithTimeout } from './http';
import {
  StudiesApiResponse,
  StudyApiResponse,
  StudyProgressListApiResponse,
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

const fetchStudyProgress = ({
  slug,
  accessToken,
}: {
  slug: string;
  accessToken: string;
}) =>
  apiRequest<StudyProgressListApiResponse>(`/api/studies/${slug}/progress`, {
    accessToken,
  }).then(({ data }) => data);

const fetchStudySegmentsProgress = ({
  slug,
  segmentsProgressPerPage,
  cursor,
  accessToken,
}: {
  slug: string;
  segmentsProgressPerPage: number;
  cursor: Cursor;
  accessToken: string;
}) =>
  apiRequest<StudySegmentsProgressApiResponse>(
    `/api/studies/${slug}/segments-progress?number=${segmentsProgressPerPage}&cursor=${cursor}`,
    { accessToken }
  );

const apiRequest = async <ApiResponse>(
  url: string,
  {
    defaultErrorMessage = 'Something went wrong.',
    accessToken = '',
  }: { defaultErrorMessage?: string; accessToken: string }
) => {
  try {
    const response = await fetchWithTimeout(url, {
      timeout: 10000,
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
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
  fetchStudyProgress,
  fetchStudySegmentsProgress,
};
