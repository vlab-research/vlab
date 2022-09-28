import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
import { Notyf } from 'notyf';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';
import {
  SecretAccountResource,
  TokenAccountResource,
} from '../../types/account';
import { addAccountToCacheWhileRefetching } from './useAccounts';

const useCreateAccount = () => {
  const notyf = new Notyf();
  const history = useHistory();
  const { createAccount } = useAuthenticatedApi();
  const [createAccountMutation, { isLoading, error }] = useMutation(
    ({
      name,
      authType,
      connectedAccount,
    }: {
      name: string;
      authType: string;
      connectedAccount: TokenAccountResource | SecretAccountResource;
    }) => createAccount({ name, authType, connectedAccount }),
    {
      onSuccess: ({ data: account }) => {
        addAccountToCacheWhileRefetching(account);
        history.push('/accounts');
        notyf.success(`${account.name} account connected!`);
      },
      onError: error => {
        notyf.error({ message: `${error.message}`, dismissible: true });
      },
    }
  );

  return {
    createAccount: createAccountMutation,
    isCreating: isLoading,
    error: error?.message,
  };
};

export default useCreateAccount;
