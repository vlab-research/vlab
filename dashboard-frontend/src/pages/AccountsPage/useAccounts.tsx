import { queryCache, useQuery } from 'react-query';
import { Account, AccountsApiResponse } from '../../types/account';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';

const defaultErrorMessage = 'Something went wrong while fetching the accounts.';

const queryKey = 'accounts';

const useAccounts: any = () => {
  const { fetchAccounts } = useAuthenticatedApi();

  //TODO this is a hanging promise, we should handle it accordingly
  const query = useQuery<AccountsApiResponse, string>(
    queryKey,
    async () =>
      await fetchAccounts({
        defaultErrorMessage,
      })
  );

  return {
    query,
    queryKey,
    accounts: query.data?.data || [],
    errorMessage: query.error?.message || defaultErrorMessage,
  };
};

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

export default useAccounts;
