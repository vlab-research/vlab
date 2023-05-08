import { useMutation, queryCache } from 'react-query';
import { useHistory } from 'react-router-dom';
import useAuthenticatedApi from './useAuthenticatedApi';
import { StudyConfData } from '../types/study';

const queryKey = 'studyConf';

const useCreateStudyConf = () => {
  const history = useHistory();
  const { createStudyConf } = useAuthenticatedApi();

  const [createStudyConfMutation, { isLoading, error }] = useMutation(
    ({ data, slug }: { data: any; slug: string }) =>
      createStudyConf({ data, slug }),
    {
      onSuccess: ({ data: conf }) => {
        addStudyConfToCacheWhileRefetching(conf);
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

export const addStudyConfToCacheWhileRefetching = (conf: StudyConfData) => {
  // Add a conf to the cache
  queryCache.setQueryData(queryKey, (confsCache: any) => {
    const confsCacheExists = // currently returning undefined
      Array.isArray(confsCache) &&
      confsCache[0] &&
      Array.isArray(confsCache[0].data);

    console.log(confsCache);

    if (confsCacheExists) {
      confsCache[0].data = [conf, ...confsCache[0].data];
    }
    return confsCache;
  });

  // Refetch the study conf by invalidating the query
  console.log(queryCache.invalidateQueries(queryKey));

  queryCache.invalidateQueries(queryKey);
};

export default useCreateStudyConf;
