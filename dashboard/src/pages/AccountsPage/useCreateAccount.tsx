import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
import { Notyf } from 'notyf';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';
import {
  FlyAccount,
  TypeformAccount,
  AlchemerAccount,
} from '../../types/account';
import { addToCache } from '../../helpers/cache';

// used to create account
// TODO specify return type instead of using any
const useCreateAccount: any = () => {
  const notyf = new Notyf();
  const history = useHistory();
  const queryKey = 'accounts';

  const { createAccount } = useAuthenticatedApi();
  const [createAccountMutation, { isLoading, error }] = useMutation(
    async ({
      name,
      authType,
      connectedAccount,
    }: {
      name: string;
      authType: string;
      connectedAccount: FlyAccount | TypeformAccount | AlchemerAccount;
    }) => await createAccount({ name, authType, connectedAccount }),
    {
      onSuccess: ({ data: account }) => {
        addToCache(account, queryKey);
        history.push('/accounts');
        notyf.success({
          message: `${account.name} account connected!`,
          duration: 5000,
        });
      },
      onError: error => {
        notyf.error({
          message: `${error.message}`,
          duration: 5000,
          dismissible: true,
        });
      },
    }
  );

  return {
    createAccount: createAccountMutation,
    isCreating: isLoading,
    errorOnCreate: error?.message,
  };
};

export default useCreateAccount;
