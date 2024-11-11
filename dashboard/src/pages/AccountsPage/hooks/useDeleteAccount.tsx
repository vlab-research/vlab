import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
import { Notyf } from 'notyf';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
// import { clearCacheWhileRefetching } from './useAccounts';

const useDeleteAccount: any = (onSettled: () => void) => {
  const notyf = new Notyf();
  const history = useHistory();
  const { deleteAccount } = useAuthenticatedApi();
  const { mutate: deleteAccountMutation, isLoading } = useMutation(
    async ({ name, authType }: { name: string; authType: string }) =>
      await deleteAccount({ name, authType }),
    {
      onSuccess: () => {
        // clearCacheWhileRefetching();
        history.push('/accounts');
        notyf.success({
          message: 'Account deleted',
          background: 'rgb(67 56 202)',
        });
      },
      onError: (error: any) => {
        notyf.error({
          message: `${error.message}`,
          background: 'rgb(251 113 133)',
          dismissible: true,
        });
      },
      onSettled: onSettled,
    }
  );

  return {
    deleteAccount: deleteAccountMutation,
    isDeleting: isLoading,
  };
};

export default useDeleteAccount;
