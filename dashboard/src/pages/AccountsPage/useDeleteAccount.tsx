import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
import { Notyf } from 'notyf';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';
import { clearCacheWhileRefetching } from '../../helpers/cache';

const useDeleteAccount: any = () => {
  const notyf = new Notyf();
  const history = useHistory();
  const queryKey = 'accounts';

  const { deleteAccount } = useAuthenticatedApi();
  const [deleteAccountMutation, { isLoading }] = useMutation(
    async ({ name, authType }: { name: string; authType: string }) =>
      await deleteAccount({ name, authType }),
    {
      onSuccess: () => {
        clearCacheWhileRefetching(queryKey);
        history.push('/accounts');
        notyf.success({
          message: `account deleted!`,
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
    deleteAccount: deleteAccountMutation,
    isDeleting: isLoading,
  };
};

export default useDeleteAccount;
