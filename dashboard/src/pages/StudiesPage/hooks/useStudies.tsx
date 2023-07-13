import { useInfiniteQuery } from 'react-query';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
import { Cursor } from '../../../types/api';
import { StudiesApiResponse } from '../../../types/study';

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
