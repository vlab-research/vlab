import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
import useAuthenticatedApi from './useAuthenticatedApi';
import { addStudyToCacheWhileRefetching } from './useStudies';

const useCreateStudy = () => {
  const history = useHistory();
  const { createStudy } = useAuthenticatedApi();
  const [createStudyMutation, { isLoading, error }] = useMutation(
    ({ name }: { name: string }) => createStudy({ name }),
    {
      onSuccess: ({ data: newStudy }) => {
        addStudyToCacheWhileRefetching(newStudy);
        history.push(`/studies`);
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