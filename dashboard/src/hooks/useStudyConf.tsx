import { useQuery, queryCache } from 'react-query';
import useAuthenticatedApi from './useAuthenticatedApi';
import { addStudyConfToCacheWhileRefetching } from './useCreateStudyConf';

const queryKey = 'studyConf';

const useStudyConf = (slug: string) => {
  const { fetchStudyConf } = useAuthenticatedApi();

  const studyConfQuery = useQuery(
    ['studyConf', slug],
    async () => await fetchStudyConf({ slug }),
    {
      onSuccess: data => {
        addStudyConfToCacheWhileRefetching(data);
      },
    }
  );

  const isLoading = !studyConfQuery.data;

  const errorOnLoad = isLoading && studyConfQuery.isError;

  return {
    data: studyConfQuery.data ?? {},
    isLoading,
    errorOnLoad,
    refetchData: () => {
      queryCache.invalidateQueries(queryKey);
    },
  };
};

export const clearCacheWhileRefetching = () => {
  queryCache.invalidateQueries(queryKey);
};

export default useStudyConf;
