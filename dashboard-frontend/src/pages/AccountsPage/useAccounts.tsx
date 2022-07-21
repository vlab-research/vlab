import { useQuery } from 'react-query';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';
import { AccountApiResponse } from '../../types/account';

const defaultErrorMessage = 'Something went wrong while fetching the Studies.';

const useAccounts = () => {
  const { fetchAccounts } = useAuthenticatedApi();
  const queryKey = 'accounts';

  const query = useQuery<AccountApiResponse[], string>(queryKey, (_: unknown) =>
    fetchAccounts({
      defaultErrorMessage,
    })
  );

  console.log(query);

  return {
    query,
    queryKey,
    accounts: query.data || [],
    errorMessage: query.error?.message || defaultErrorMessage,
  };
};

export default useAccounts;
