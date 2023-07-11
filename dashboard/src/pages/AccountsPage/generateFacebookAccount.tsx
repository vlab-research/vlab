import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
import { Notyf } from 'notyf';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';
import { addToCache } from '../../helpers/cache';

// used to create account
// TODO specify return type instead of using any
const useGenerateFacebookAccount: any = () => {
  const notyf = new Notyf();
  const history = useHistory();
  const queryKey = 'accounts';

  const { generateFacebookAccount } = useAuthenticatedApi();
  const [generateFacebookAccountMutation, { isLoading, error }] = useMutation(
    async ({ code }: { code: string }) =>
      await generateFacebookAccount({ code }),
    {
      onSuccess: ({ data: account }) => {
        addToCache(account, queryKey);
        history.push('/accounts');
        notyf.success({
          message: `${account.name} account connected!`,
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
    generateFacebookAccount: generateFacebookAccountMutation,
    isCreating: isLoading,
    errorOnCreate: error?.message,
  };
};

export default useGenerateFacebookAccount;
