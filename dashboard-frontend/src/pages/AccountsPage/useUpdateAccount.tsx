import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';

import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';
import {
  TokenAccountResource,
  SecretAccountResource,
} from '../../types/account';
import { addAccountToCacheWhileRefetching } from './useAccounts';

const useUpdateAccount = () => {
  const history = useHistory();

  const { updateAccount } = useAuthenticatedApi();

  const [updateAccountMutation, { isLoading, error }] = useMutation(
    ({
      name,
      authType,
      connectedAccount,
    }: {
      name: string;
      authType: string;
      connectedAccount: TokenAccountResource | SecretAccountResource;
    }) => updateAccount({ name, authType, connectedAccount }),
    {
      onSuccess: ({ data: newAccount }) => {
        addAccountToCacheWhileRefetching(newAccount);
        history.push('/accounts');
      },
    }
  );

  return {
    updateAccount: updateAccountMutation,
    isUpdating: isLoading,
    errorOnUpdate: error?.message,
  };
};

export default useUpdateAccount;
