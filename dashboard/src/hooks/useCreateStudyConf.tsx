import { useMutation, queryCache } from 'react-query';
import { Notyf } from 'notyf';
import { useHistory } from 'react-router-dom';
import useAuthenticatedApi from './useAuthenticatedApi';
import { StudyConfData } from '../types/study';

const queryKey = 'studyConf';

const useCreateStudyConf = () => {
  const notyf = new Notyf();
  const history = useHistory();
  const { createStudyConf } = useAuthenticatedApi();

  const [createStudyConfMutation, { isLoading, error }] = useMutation(
    async ({ data, slug }: { data: any; slug: string }) =>
      await createStudyConf({ data, slug }),
    {
      onSuccess: ({ data: conf }) => {
        addStudyConfToCacheWhileRefetching(conf);
        history.push(`/studies`);
        notyf.success({
          message: `Study updated!`,
          duration: 2000,
        });
      },
      onError: error => {
        notyf.error({
          message: `${error.message}`,
          duration: 2000,
          dismissible: true,
        });
      },
    }
  );

  return {
    createStudyConf: createStudyConfMutation,
    isLoadingOnCreateStudyConf: isLoading,
    errorOnCreateStudyConf: error?.message,
  };
};

export const addStudyConfToCacheWhileRefetching = (conf: StudyConfData) => {
  // Add a conf to the cache
  queryCache.setQueryData(queryKey, (confsCache: any) => {
    confsCache = conf;
    return confsCache;
  });

  // Refetch the study conf by invalidating the query
  queryCache.invalidateQueries(queryKey);
};

export const clearCacheWhileRefetching = () => {
  queryCache.invalidateQueries(queryKey);
};

export default useCreateStudyConf;
