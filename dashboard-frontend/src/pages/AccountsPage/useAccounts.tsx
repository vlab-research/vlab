import { queryCache, useQuery } from 'react-query';
import { AccountResource, AccountsApiResponse } from '../../types/account';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';

const defaultErrorMessage = 'Something went wrong while fetching the accounts.';

const queryKey = 'accounts';

const useAccounts = () => {
  const { fetchAccounts } = useAuthenticatedApi();

  const query = useQuery<AccountsApiResponse, string>(queryKey, () =>
    fetchAccounts({
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

export const addAccountToCacheWhileRefetching = (account: AccountResource) => {
  // Add account to cache
  queryCache.setQueryData(queryKey, (accountsCache: any) => {
    const accountsCacheExists =
      Array.isArray(accountsCache) &&
      accountsCache[0] &&
      Array.isArray(accountsCache[0].data);

    if (accountsCacheExists) {
      accountsCache[0].data = [account, ...accountsCache[0].data];
    }

    return accountsCache;
  });

  // Refetch the accounts by invalidating the query
  queryCache.invalidateQueries(queryKey);
};

export default useAccounts;
