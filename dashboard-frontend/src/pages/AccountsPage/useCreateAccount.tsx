import { useQuery } from 'react-query';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';
import { AccountResource } from '../../types/account';

const defaultErrorMessage =
  'Something went wrong while connecting your account.';

const useCreateAccount = (account: AccountResource) => {
  const { createAccount } = useAuthenticatedApi();
  const queryKey = 'create-account';

  const data = JSON.stringify(account);

  const query = useQuery([queryKey, data], () => createAccount({ data }), {
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });

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
