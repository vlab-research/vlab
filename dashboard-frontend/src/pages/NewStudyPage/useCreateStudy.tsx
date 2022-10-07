import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';
import { addStudyToCacheWhileRefetching } from '../../hooks/useStudies';

const useCreateStudy = () => {
  const history = useHistory();
  const { createStudy } = useAuthenticatedApi();
  const [createStudyMutation, { isLoading, error }] = useMutation(
    ({
      name,
      objective,
      optimizationGoal,
      destinationType,
      pageId,
      instagramId,
      minBudget,
      optWindow,
      adAccount,
      country,
    }: {
      name: string;
      objective: string;
      optimizationGoal: string;
      destinationType: string;
      pageId: string;
      instagramId: string;
      minBudget: number;
      optWindow: number;
      adAccount: string;
      country: string;
    }) =>
      createStudy({
        name,
        objective,
        optimizationGoal,
        destinationType,
        pageId,
        instagramId,
        minBudget,
        optWindow,
        adAccount,
        country,
      }),
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
    errorOnCreate: error?.message,
  };
};

export default useCreateStudy;
