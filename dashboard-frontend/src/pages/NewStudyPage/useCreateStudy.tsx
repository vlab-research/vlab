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
      minBudget,
      instagramId,
      adAccount,
      country,
    }: {
      name: string;
      objective: string;
      optimizationGoal: string;
      destinationType: string;
      minBudget: number;
      instagramId: string;
      adAccount: string;
      country: string;
    }) =>
      createStudy({
        name,
        objective,
        optimizationGoal,
        destinationType,
        minBudget,
        instagramId,
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
