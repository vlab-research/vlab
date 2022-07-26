import { useQuery } from 'react-query';
import { AccountsApiResponse } from '../../types/account';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';

const defaultErrorMessage = 'Something went wrong while fetching the accounts.';

const useAccounts = () => {
  const { fetchAccounts } = useAuthenticatedApi();
  const queryKey = 'accounts';

  const query = useQuery<AccountsApiResponse, string>(queryKey, () =>
    fetchAccounts({
      defaultErrorMessage,
    })
  );

  console.log(query.data);

  return {
    query,
    queryKey,
    accounts: query.data || [],
    errorMessage: query.error?.message || defaultErrorMessage,
  };
};

export default useAccounts;
