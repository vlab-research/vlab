import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
import { Notyf } from 'notyf';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
import {
  FlyAccount,
  TypeformAccount,
  AlchemerAccount,
} from '../../../types/account';
import { addAccountToCacheWhileRefetching } from './useAccounts';
import { createLabelFor } from '../../../helpers/strings';

const useCreateAccount = () => {
  const notyf = new Notyf();
  const history = useHistory();
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
        addAccountToCacheWhileRefetching(account);
        history.push('/accounts');
        notyf.success({
          message: `${createLabelFor(account.authType)} account saved`,
          background: 'rgb(67 56 202)',
        });
      },
      onError: error => {
        notyf.error({
          message: `${error.message}`,
          background: 'rgb(67 56 202)',
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
