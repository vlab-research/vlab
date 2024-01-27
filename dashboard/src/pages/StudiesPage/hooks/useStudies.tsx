import { useInfiniteQuery } from 'react-query';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';

const studiesPerPage = 10;
const queryKey = 'studies';
const defaultErrorMessage = 'Something went wrong while fetching the Studies.';

const useStudies = () => {
  const { fetchStudies } = useAuthenticatedApi();

  const query = useInfiniteQuery(
    queryKey,
    ({ pageParam: cursor }) =>
      fetchStudies({
        studiesPerPage,
        cursor,
        defaultErrorMessage,
      }),
    {
      getNextPageParam: lastPage => lastPage.pagination.nextCursor,
    }
  );

  return {
    query,
    queryKey,
    studiesPerPage,
    studies: (query.data?.pages || []).flatMap(page => page.data),
    errorMessage: defaultErrorMessage, // TODO: use custom error message from api
  };
};

export default useStudies;
