import { useQuery, queryCache } from 'react-query';
import useAuthenticatedApi from './useAuthenticatedApi';

const queryKey = 'studyConf';

const useStudyConf = (slug: string) => {
  const studyConfQuery = useStudyConfQuery(slug);

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

const useStudyConfQuery = (slug: string) => {
  const { fetchStudyConf } = useAuthenticatedApi();
  return useQuery([queryKey, slug], () => fetchStudyConf({ slug }));
};

export const clearCacheWhileRefetching = () => {
  queryCache.invalidateQueries(queryKey);
};

export default useStudyConf;
