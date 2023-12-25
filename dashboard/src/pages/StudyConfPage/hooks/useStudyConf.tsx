import { useQuery, queryCache } from 'react-query';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';

const queryKey = 'studyConf';

const useStudyConf = (studySlug: string) => {
  const query = useStudyConfQuery(studySlug);

  return {
    ...query,
    refetchData: () => {
      queryCache.invalidateQueries(queryKey);
    },
  };
};

const useStudyConfQuery = (studySlug: string) => {
  const { fetchStudyConf } = useAuthenticatedApi();
  return useQuery([queryKey, studySlug], () => fetchStudyConf({ studySlug }));
};

export default useStudyConf;
