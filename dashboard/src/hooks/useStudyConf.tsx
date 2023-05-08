import { useQuery, queryCache } from 'react-query';
import useAuthenticatedApi from './useAuthenticatedApi';

const useStudyConf = (slug: string) => {
  const { fetchStudyConf } = useAuthenticatedApi();

  const studyConfQuery = useQuery(['studyConf', slug], () =>
    fetchStudyConf({ slug })
  );

  const isLoading = !studyConfQuery.data;

  const errorOnLoad = isLoading && studyConfQuery.isError;

  return {
    data: studyConfQuery.data ?? {},
    isLoading,
    errorOnLoad,
    refetchData: () => {
      queryCache.invalidateQueries(['studyConf', slug]);
    },
  };
};

export default useStudyConf;
