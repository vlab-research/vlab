import { useInfiniteQuery } from 'react-query';
import { StudiesApiResponse } from '../../types/study';

const studiesPerPage = 10;
const defaultErrorMessage = 'Something went wrong while fetching the Studies.';

type Cursor = string | null;

const useStudies = () => {
  const queryKey = 'studies';

  const query = useInfiniteQuery<StudiesApiResponse, string, Cursor>(
    queryKey,
    fetchStudies,
    {
      getFetchMore: lastPage => lastPage.pagination.nextCursor,
    }
  );

  return {
    query,
    queryKey,
    studiesPerPage,
    studies: (query.data || [])
      .flatMap(page => page)
      .map(studyResponse => studyResponse.data)
      .flatMap(studyData => studyData),
    errorMessage: query.error?.message || defaultErrorMessage,
  };
};

/**
 * TODO:
 *  Create a centralized api layer
 *  Create ApiError and TimeoutError which will be useful to have
 *    when reporting to Sentry or a similar service.
 */
const fetchStudies = async (_: any, cursor: Cursor = null) => {
  const url =
    cursor === null
      ? `/api/studies?number=${studiesPerPage}`
      : `/api/studies?number=${studiesPerPage}&cursor=${cursor}`;

  try {
    const response = await fetchWithTimeout(url, { timeout: 10000 });

    if (!response.ok) {
      throw new Error(await getErrorMessageFor(response));
    }

    return response.json();
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error(defaultErrorMessage);
    }

    throw err;
  }
};

const getErrorMessageFor = async (errorResponse: Response): Promise<string> => {
  const containsJSON = errorResponse.headers
    .get('content-type')
    ?.includes('application/json');

  if (!containsJSON) {
    return defaultErrorMessage;
  }

  const responseBody = await errorResponse.json();

  return responseBody.error || defaultErrorMessage;
};

/**
 * TODO: Extract as a helper and test properly
 */
const fetchWithTimeout = async (
  requestInfo: RequestInfo,
  { timeout, ...requestInit }: { timeout: number } & RequestInit
) => {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  const response = await fetch(requestInfo, {
    ...requestInit,
    signal: controller.signal,
  });

  clearTimeout(id);

  return response;
};

export default useStudies;
