import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';
import {
  TokenAccountResource,
  SecretAccountResource,
} from '../../types/account';
import { addAccountToCacheWhileRefetching } from './useAccounts';
import { Notyf } from 'notyf';

const useUpdateAccount = () => {
  const history = useHistory();
  const notyf = new Notyf();
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
      onSuccess: ({ data: account }) => {
        addAccountToCacheWhileRefetching(account);
        history.push('/accounts');
        notyf.success({
          message: `${account.name} account updated!`,
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
    updateAccount: updateAccountMutation,
    isUpdating: isLoading,
    errorOnUpdate: error?.message,
  };
};

export default useUpdateAccount;
