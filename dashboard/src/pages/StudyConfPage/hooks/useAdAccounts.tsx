import { useInfiniteQuery } from 'react-query';
import { fetchAdAccounts } from '../../../helpers/api';

const limit = 100;
const defaultErrorMessage =
  'Something went wrong while fetching your ad accounts.';

const useAdAccounts = (accessToken: string) => {
  const queryKey = `adAccounts${accessToken}`;

  const query = useInfiniteQuery(
    queryKey,
    ({ pageParam: cursor }) =>
      fetchAdAccounts({
        limit,
        cursor,
        accessToken,
        defaultErrorMessage,
      }),
    {
      getNextPageParam: lastPage => lastPage.paging.after,
    }
  );

  return {
    query,
    adAccounts: (query.data?.pages || []).flatMap(page => page.data),
    errorMessage: query.error || defaultErrorMessage,
  };
};

export default useAdAccounts;
