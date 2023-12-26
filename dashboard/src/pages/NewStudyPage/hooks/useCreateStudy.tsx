import { useMutation } from 'react-query';
import { Notyf } from 'notyf';
import { useHistory } from 'react-router-dom';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
import { createSlugFor } from '../../../helpers/strings';

const useCreateStudy = (name: string) => {
  const notyf = new Notyf();
  const history = useHistory();
  const { createStudy } = useAuthenticatedApi();

  const { mutate: createStudyMutation, isLoading, error } = useMutation(
    ({ name }: { name: string }) => createStudy({ name }),
    {
      onSuccess: () => {
        history.push(`/studies/${createSlugFor(name)}/general`);
        notyf.success({
          message: `Study created`,
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
    }
  );

  return {
    createStudy: createStudyMutation,
    isLoadingOnCreateStudy: isLoading,
    errorOnCreateStudy: error?.message,
  };
};

export default useCreateStudy;
