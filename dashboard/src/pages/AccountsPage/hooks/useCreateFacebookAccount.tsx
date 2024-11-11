import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
import { Notyf } from 'notyf';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
// import { addAccountToCacheWhileRefetching } from './useAccounts';

const useCreateFacebookAccount: any = (onSettled: () => void) => {
  const notyf = new Notyf();
  const history = useHistory();
  const { createFacebookAccount } = useAuthenticatedApi();
  const { mutate: useCreateFacebookAccountMutation, isLoading, error } = useMutation(
    async ({ code }: { code: string }) => await createFacebookAccount({ code }),
    {
      onSuccess: ({ data: account }) => {
        // addAccountToCacheWhileRefetching(account);
        history.push('/accounts');
        notyf.success({
          message: `Facebook account connected`,
          background: 'rgb(67 56 202)',
        });
      },
      onError: (error: any) => {
        notyf.error({
          message: `${error.message}`,
          background: 'rgb(67 56 202)',
          dismissible: true,
        });
      },
      onSettled: onSettled,
    }
  );

  return {
    createFacebookAccount: useCreateFacebookAccountMutation,
    isCreating: isLoading,
    errorOnCreate: error?.message,
  };
};

export default useCreateFacebookAccount;
