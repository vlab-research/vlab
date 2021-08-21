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

export const fetchStudies = ({
  studiesPerPage,
  cursor,
  defaultErrorMessage,
}: {
  studiesPerPage: number;
  cursor: Cursor;
  defaultErrorMessage: string;
}) =>
  apiRequest<StudiesApiResponse>(
    `/api/studies?number=${studiesPerPage}&cursor=${cursor}`,
    {
      defaultErrorMessage,
    }
  );

export const fetchStudy = (slug: string) =>
  apiRequest<StudyApiResponse>(`/api/studies/${slug}`).then(({ data }) => data);

export const fetchStudyProgress = (slug: string) =>
  apiRequest<StudyProgressListApiResponse>(
    `/api/studies/${slug}/progress`
  ).then(({ data }) => data);

export const fetchStudySegmentsProgress = ({
  slug,
  segmentsProgressPerPage,
  cursor,
}: {
  slug: string;
  segmentsProgressPerPage: number;
  cursor: Cursor;
}) =>
  apiRequest<StudySegmentsProgressApiResponse>(
    `/api/studies/${slug}/segments-progress?number=${segmentsProgressPerPage}&cursor=${cursor}`
  );

const apiRequest = async <ApiResponse>(
  url: string,
  { defaultErrorMessage = 'Something went wrong.' } = {}
) => {
  try {
    const response = await fetchWithTimeout(url, {
      timeout: 10000,
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
