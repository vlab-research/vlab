import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';
import { addStudyToCacheWhileRefetching } from '../../hooks/useStudies';

const useCreateStudy = () => {
  const history = useHistory();
  const { createStudy } = useAuthenticatedApi();
  const [createStudyMutation, { isLoading, error }] = useMutation(
    ({ name }: { name: string }) => createStudy({ name }),
    {
      onSuccess: ({ data: newStudy }) => {
        addStudyToCacheWhileRefetching(newStudy);
        history.push('/');
      },
    }
  );

  return {
    createStudy: createStudyMutation,
    isCreating: isLoading,
    errorMessage: error?.message,
  };
};

export default useCreateStudy;
