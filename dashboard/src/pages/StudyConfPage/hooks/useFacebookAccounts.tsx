import { queryCache, useQuery } from 'react-query';
import { Account } from '../../../types/account';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';

const defaultErrorMessage =
  'Could not find a Facebook connection, please check your connected accounts';

const queryKey = 'facebook-accounts';

const useFacebookAccounts: any = () => {
  const { fetchAccounts } = useAuthenticatedApi();

  //TODO this is a hanging promise, we should handle it accordingly
  const query = useQuery<Account, string>(
    queryKey,
    () => fetchAccounts({
      // In this instance we only want facebook connections
      type: 'facebook',
      defaultErrorMessage,
    }).then(data => data[0])
  );

  return {
    ...query,
    refetchData: () => {
      queryCache.invalidateQueries([queryKey]);
    },
  };
};

export default useFacebookAccounts;
