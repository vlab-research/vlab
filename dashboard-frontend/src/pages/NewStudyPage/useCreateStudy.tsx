import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
import { Notyf } from 'notyf';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';
import { addStudyToCacheWhileRefetching } from '../../hooks/useStudies';

const useCreateStudy = () => {
  const notyf = new Notyf();
  const history = useHistory();
  const { createStudy } = useAuthenticatedApi();
  const [createStudyMutation, { isLoading, error }] = useMutation(
    ({
      name,
      objective,
      optimization_goal,
      destination_type,
      page_id,
      instagram_id,
      min_budget,
      opt_window,
      ad_account,
      country,
    }: {
      name: string;
      objective: string;
      optimization_goal: string;
      destination_type: string;
      page_id: string;
      instagram_id: string;
      min_budget: number;
      opt_window: number;
      ad_account: string;
      country: string;
    }) =>
      createStudy({
        name,
        objective,
        optimization_goal,
        destination_type,
        page_id,
        instagram_id,
        min_budget,
        opt_window,
        ad_account,
        country,
      }),
    {
      onSuccess: ({ data: newStudy }) => {
        addStudyToCacheWhileRefetching(newStudy);
        history.push('/');
        notyf.success(`${newStudy.name} created!`);
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
