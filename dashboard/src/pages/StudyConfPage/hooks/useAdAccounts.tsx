import { useInfiniteQuery } from 'react-query';
import { fetchAdAccounts } from '../../../helpers/api';
import { Cursor } from '../../../types/api';

const limit = 100;
const defaultErrorMessage =
  'Something went wrong while fetching your ad accounts.';

const useAdAccounts = (accessToken: string) => {
  const queryKey = `adAccounts${accessToken}`;

  const query = useInfiniteQuery(
    queryKey,
    (_: unknown, cursor: Cursor = null) =>
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
