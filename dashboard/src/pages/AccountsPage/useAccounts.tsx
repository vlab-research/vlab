import { useQuery } from 'react-query';
import { type AccountsApiResponse } from '../../types/account';
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

export default useAccounts;
