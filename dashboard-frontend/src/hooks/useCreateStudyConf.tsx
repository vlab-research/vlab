import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
import { StudyConfResource } from '../types/study';
import useAuthenticatedApi from './useAuthenticatedApi';
import { addStudyConfToCacheWhileRefetching } from './useStudies';

const useCreateStudyConf = () => {
  const history = useHistory();
  const { createStudyConf } = useAuthenticatedApi();

  const [createStudyConfMutation, { isLoading, error }] = useMutation(
    ({ data, slug }: { data: StudyConfResource; slug: string }) =>
      createStudyConf({ data, slug }),
    {
      onSuccess: ({ data: studyConf }) => {
        addStudyConfToCacheWhileRefetching(studyConf);
        history.push(`/studies`);
      },
    }
  );

  return {
    createStudyConf: createStudyConfMutation,
    isLoadingOnCreateStudyConf: isLoading,
    errorOnCreateStudyConf: error?.message,
  };
};

export default useCreateStudyConf;
