import { useInfiniteQuery } from 'react-query';
import { fetchStudies } from '../../helpers/api';
import { StudiesApiResponse } from '../../types/study';
import { Cursor } from '../../types/api';

const studiesPerPage = 10;
const defaultErrorMessage = 'Something went wrong while fetching the Studies.';

const useStudies = () => {
  const queryKey = 'studies';

  const query = useInfiniteQuery<StudiesApiResponse, string, Cursor>(
    queryKey,
    (_: unknown, cursor: Cursor = null) =>
      fetchStudies({ studiesPerPage, cursor, defaultErrorMessage }),
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
