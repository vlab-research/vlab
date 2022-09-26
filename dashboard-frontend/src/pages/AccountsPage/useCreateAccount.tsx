import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
import toast from 'react-hot-toast';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';
import {
  SecretAccountResource,
  TokenAccountResource,
} from '../../types/account';
import { addAccountToCacheWhileRefetching } from './useAccounts';

const useCreateAccount = () => {
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
        toast.success(`Account connected`);
      },
      onError: error => {
        toast.error(`Something went wrong: ${error.message}`);
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
