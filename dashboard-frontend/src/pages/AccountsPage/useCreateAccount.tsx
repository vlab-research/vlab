import { useQuery } from 'react-query';
import { AccountResource } from '../../types/account';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';

const defaultErrorMessage =
  'Something went wrong while connecting your account.';

const useCreateAccount = (account: AccountResource) => {
  const { createAccount } = useAuthenticatedApi();
  const queryKey = 'create-account';

  const query = useQuery(
    [queryKey, account],
    () => createAccount({ account }),
    {
      staleTime: Infinity,
      refetchOnWindowFocus: false,
    }
  );

  const inProgress = !query.isSuccess && !query.isError;

  return {
    query,
    queryKey,
    data: query.data?.data || [],
    errorMessage: query.error?.message || defaultErrorMessage,
    inProgress,
    failed: query.isError,
    success: query.isSuccess,
  };
};

export default useCreateAccount;
