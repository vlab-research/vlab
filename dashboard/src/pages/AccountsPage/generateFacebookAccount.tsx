import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
import { Notyf } from 'notyf';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';

// used to create account
// TODO specify return type instead of using any
const useGenerateFacebookAccount: any = () => {
  const notyf = new Notyf();
  const history = useHistory();

  const { createFacebookAccount } = useAuthenticatedApi();
  const { mutate: generateFacebookAccountMutation, isLoading, error } = useMutation(
    async ({ code }: { code: string }) =>
      await createFacebookAccount({ code }),
    {
      onSuccess: ({ data: account }) => {
        history.push('/accounts');
        notyf.success({
          message: `${account.name} account connected!`,
          duration: 5000,
        });
      },
      onError: (error: any) => {
        notyf.error({
          message: `${error.message}`,
          duration: 5000,
          dismissible: true,
        });
      },
    }
  );

  return {
    generateFacebookAccount: generateFacebookAccountMutation,
    isCreating: isLoading,
    errorOnCreate: error?.message,
  };
};

export default useGenerateFacebookAccount;
