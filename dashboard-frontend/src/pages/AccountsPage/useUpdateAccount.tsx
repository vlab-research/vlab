import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
import toast from 'react-hot-toast';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';
import {
  TokenAccountResource,
  SecretAccountResource,
} from '../../types/account';
import { addAccountToCacheWhileRefetching } from './useAccounts';

const useUpdateAccount = () => {
  const history = useHistory();

  const { updateAccount } = useAuthenticatedApi();

  const [updateAccountMutation, { isLoading }] = useMutation(
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
        toast.success(`${account.name} account updated!`);
      },
      onError: error => {
        toast.error(`Something went wrong: ${error.message}`);
      },
    }
  );

  return {
    updateAccount: updateAccountMutation,
    isUpdating: isLoading,
  };
};

export default useUpdateAccount;
