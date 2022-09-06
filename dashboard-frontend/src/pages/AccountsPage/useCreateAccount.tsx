import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
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
      onSuccess: ({ data: newAccount }) => {
        addAccountToCacheWhileRefetching(newAccount);
        history.push('/accounts');
      },
    }
  );

  return {
    createAccount: createAccountMutation,
    isCreating: isLoading,
    errorMessage: error?.message,
  };
};

export default useCreateAccount;
