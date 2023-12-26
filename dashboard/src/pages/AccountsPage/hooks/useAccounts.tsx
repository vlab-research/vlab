import { useQuery } from 'react-query';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
import { type Account } from '../../../types/account';

const defaultErrorMessage = 'Something went wrong while fetching the accounts.';

const queryKey = 'accounts';

const useAccounts: any = () => {
  const { fetchAccounts } = useAuthenticatedApi();

  //TODO this is a hanging promise, we should handle it accordingly
  const query = useQuery<Account[], string>(
    queryKey,
    async () =>
      await fetchAccounts({
        defaultErrorMessage,
      })
  );

  return {
    query,
    queryKey,
    accounts: query.data || [],
    errorMessage: defaultErrorMessage, // TODO: add api error
  };
};

export default useAccounts;
