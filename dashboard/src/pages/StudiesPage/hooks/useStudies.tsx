<<<<<<< HEAD:dashboard/src/hooks/useStudies.tsx
import { useInfiniteQuery } from 'react-query';
import { StudiesApiResponse } from '../types/study';
import { Cursor } from '../types/api';
import useAuthenticatedApi from './useAuthenticatedApi';
=======
import { useInfiniteQuery, queryCache } from 'react-query';
import { StudiesApiResponse, StudyResource } from '../../../types/study';
import { Cursor } from '../../../types/api';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
>>>>>>> 5c21eae (fix: connected accounts):dashboard/src/pages/StudiesPage/hooks/useStudies.tsx

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

export default useStudies;
