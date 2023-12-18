import { useMutation } from 'react-query';
import { Notyf } from 'notyf';
import { useHistory } from 'react-router-dom';
import { addToCache } from '../../../helpers/cache';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
import { createSlugFor } from '../../../helpers/strings';

const useCreateStudy = (name: string) => {
  const notyf = new Notyf();
  const history = useHistory();
  const queryKey = 'study';
  const { createStudy } = useAuthenticatedApi();

  const [createStudyMutation, { isLoading, error }] = useMutation(
    ({ name }: { name: string }) => createStudy({ name }),
    {
      onSuccess: ({ data: newStudy }) => {
        addToCache(newStudy, queryKey);

        history.push(`/studies/${createSlugFor(name)}/general`);
        notyf.success({
          message: `Study created`,
          background: 'rgb(67 56 202)',
        });
      },
      onError: error => {
        notyf.error({
          message: `${error.message}`,
          background: 'rgb(251 113 133)',
          dismissible: true,
        });
      },
    }
  );

  return {
    createStudy: createStudyMutation,
    isLoadingOnCreateStudy: isLoading,
    errorOnCreateStudy: error?.message,
  };
};

export default useCreateStudy;
