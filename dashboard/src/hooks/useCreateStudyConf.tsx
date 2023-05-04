import { useMutation } from 'react-query';
import { useHistory } from 'react-router-dom';
import useAuthenticatedApi from './useAuthenticatedApi';
import { addStudyConfToCacheWhileRefetching } from './useStudies';
import { StudyConfData } from '../types/study';

const useCreateStudyConf = () => {
  const history = useHistory();
  const { createStudyConf } = useAuthenticatedApi();

  const [createStudyConfMutation, { isLoading, error }] = useMutation(
    ({ data, studySlug }: { data: StudyConfData; studySlug: string }) =>
      createStudyConf({ data, studySlug }),
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
