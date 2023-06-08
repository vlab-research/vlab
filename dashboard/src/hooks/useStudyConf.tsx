import { useQuery, queryCache } from 'react-query';
import useAuthenticatedApi from './useAuthenticatedApi';

const queryKey = 'studyConf';

const useStudyConf = (studySlug: string) => {
  const studyConfQuery = useStudyConfQuery(studySlug);

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

const useStudyConfQuery = (studySlug: string) => {
  const { fetchStudyConf } = useAuthenticatedApi();
  return useQuery([queryKey, studySlug], () => fetchStudyConf({ studySlug }));
};

export const clearCacheWhileRefetching = () => {
  queryCache.invalidateQueries(queryKey);
};

export default useStudyConf;
