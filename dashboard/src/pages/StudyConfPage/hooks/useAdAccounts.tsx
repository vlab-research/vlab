import { queryCache, useInfiniteQuery } from 'react-query';
import { fetchAdAccounts } from '../../../helpers/api';
import { Cursor } from '../../../types/api';
import { AdAccountsApiResponse } from '../../../types/study';

const limit = 100;
const defaultErrorMessage =
  'Something went wrong while fetching your ad accounts.';

const useAdAccounts = (accessToken: string) => {
  const queryKey = `adAccounts${accessToken}`;

  const query = useInfiniteQuery<AdAccountsApiResponse, string, Cursor>(
    queryKey,
    (_: unknown, cursor: Cursor = null) =>
      fetchAdAccounts({
        limit,
        cursor,
        accessToken,
        defaultErrorMessage,
      }),
    {
      getFetchMore: lastPage => lastPage.paging.after,
    }
  );

  return {
    query,
    adAccounts: (query.data || []).flatMap(page => page.data),
    errorMessage: query.error || defaultErrorMessage,
    refetchData: () => {
      queryCache.invalidateQueries([queryKey]);
    },
  };
};

export default useAdAccounts;
