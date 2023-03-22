import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
import { StudyConfigResource } from '../types/study';
import useAuthenticatedApi from './useAuthenticatedApi';
import { addStudyConfToCacheWhileRefetching } from './useStudies';

const useCreateStudyConf = () => {
  const history = useHistory();
  const { createStudyConf } = useAuthenticatedApi();

  const [createStudyConfMutation, { isLoading, error }] = useMutation(
    ({
      config,
      slug,
      description,
    }: {
      config: StudyConfigResource;
      slug: string;
      description: string;
    }) => createStudyConf({ config, slug, description }),
    {
      onSuccess: ({ data: studyConf }) => {
        addStudyConfToCacheWhileRefetching(studyConf);
        history.push(`/studies`);
      },
    }
  );

  return {
    createStudyConf: createStudyConfMutation,
    isCreating: isLoading,
    errorMessage: error?.message,
  };
};

export default useCreateStudyConf;
