import { useQuery } from 'react-query';
import { type AccountsApiResponse } from '../../../../types/account';
import useAuthenticatedApi from '../../../../hooks/useAuthenticatedApi';

const defaultErrorMessage =
  'Could not find a Facebook connection, please check your connected accounts';

const queryKey = 'facebook-accounts';

const useAccounts: any = () => {
  const { fetchAccounts } = useAuthenticatedApi();

  //TODO this is a hanging promise, we should handle it accordingly
  const query = useQuery<AccountsApiResponse, string>(
    queryKey,
    async () =>
      await fetchAccounts({
        // In this instance we only want facebook connections
        type: 'facebook',
        defaultErrorMessage,
      })
  );

  return {
    query,
    queryKey,
    //TODO for now we just return the first connected account that exists
    //as you can currently only connect one facebook account per user
    account: query.data?.data[0] || undefined,
    errorMessage: query.error?.message || defaultErrorMessage,
  };
};

export default useAccounts;
