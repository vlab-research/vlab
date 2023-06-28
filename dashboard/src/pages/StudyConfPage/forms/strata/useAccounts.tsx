import { queryCache, useQuery } from 'react-query';
import { type Account, type AccountsApiResponse } from '../../../../types/account';
import useAuthenticatedApi from '../../../../hooks/useAuthenticatedApi';

const defaultErrorMessage = 'Could Not Find Facebook Connection, please see connected accounts';

const queryKey = 'facebook-accounts';

const useAccounts: any = () => {
  const { fetchAccounts } = useAuthenticatedApi();

  //TODO this is a hanging promise, we should handle it accordingly
  const query = useQuery<AccountsApiResponse, string>(
    queryKey,
    async () =>
      await fetchAccounts({
        // In this instance we only want facebook connections
        type: "facebook", 
        defaultErrorMessage,
      })
  );

  return {
    query,
    queryKey,
    //TODO for now we just return the first connected account that exists
    //as you can currently only connect one facebook account
    //per user
    account: query.data?.data[0] || undefined,
    errorMessage: query.error?.message || defaultErrorMessage,
  };
};

//TODO this logic is duplicated, we should probably find a qay to abstract it
export const addAccountToCacheWhileRefetching: any = (account: Account) => {
  // Add account to cache
  queryCache.setQueryData(queryKey, (accountsCache: any) => {
    const accountsCacheExists =
      Array.isArray(accountsCache) &&
      accountsCache[0] !== undefined &&
      Array.isArray(accountsCache[0].data);

    if (accountsCacheExists === true) {
      accountsCache[0].data = [account, ...accountsCache[0].data];
    }

    return accountsCache;
  });

  // Refetch the accounts by invalidating the query
  queryCache.invalidateQueries(queryKey);
};

export const clearCacheWhileRefetching = () => {
  queryCache.invalidateQueries(queryKey);
};

export default useAccounts;
