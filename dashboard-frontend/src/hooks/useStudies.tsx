import { useInfiniteQuery, queryCache } from 'react-query';
import {
  StudiesApiResponse,
  StudyConfigResource,
  StudyResource,
} from '../types/study';
import { Cursor } from '../types/api';
import useAuthenticatedApi from './useAuthenticatedApi';

const studiesPerPage = 10;
const queryKey = 'studies';
const defaultErrorMessage = 'Something went wrong while fetching the Studies.';

const useStudies = () => {
  const { fetchStudies } = useAuthenticatedApi();

  const query = useInfiniteQuery<StudiesApiResponse, string, Cursor>(
    queryKey,
    (_: unknown, cursor: Cursor = null) =>
      fetchStudies({
        studiesPerPage,
        cursor,
        defaultErrorMessage,
      }),
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

export const addStudyToCacheWhileRefetching = (study: StudyResource) => {
  // Add a study to the cache
  queryCache.setQueryData(queryKey, (studiesCache: any) => {
    const studiesCacheExists =
      Array.isArray(studiesCache) &&
      studiesCache[0] &&
      Array.isArray(studiesCache[0].data);

    if (studiesCacheExists) {
      studiesCache[0].data = [study, ...studiesCache[0].data];
    }

    return studiesCache;
  });

  // Refetch the studies by invalidating the query
  queryCache.invalidateQueries(queryKey);
};

export const addStudyConfToCacheWhileRefetching = (
  conf: StudyConfigResource
) => {
  // Add a conf to the cache
  queryCache.setQueryData(queryKey, (configsCache: any) => {
    const configsCacheExists =
      Array.isArray(configsCache) &&
      configsCache[0] &&
      Array.isArray(configsCache[0].data);

    if (configsCacheExists) {
      configsCache[0].data = [conf, ...configsCache[0].data];
    }

    return configsCache;
  });

  // Refetch the studies by invalidating the query
  queryCache.invalidateQueries(queryKey);
};

export default useStudies;
