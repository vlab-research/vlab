import { useQuery, queryCache } from 'react-query';
import useAuthenticatedApi from './useAuthenticatedApi';

const useStudyConf = (studySlug: string) => {
  const { fetchStudyConf } = useAuthenticatedApi();

  const studyConfQuery = useQuery(['studyConf', studySlug], () =>
    fetchStudyConf({ studySlug })
  );

  const isLoading = !studyConfQuery.data;

  const errorOnLoad = isLoading && studyConfQuery.isError;

  return {
    data: studyConfQuery.data ?? '',
    isLoading,
    errorOnLoad,
    refetchData: () => {
      queryCache.invalidateQueries(['studyConf', studySlug]);
    },
  };
};

export default useStudyConf;
