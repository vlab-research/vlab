import { useQuery } from 'react-query';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';

export const queryKey = 'studyConf';

const useStudyConf = (studySlug: string) => {
  const { fetchStudyConf } = useAuthenticatedApi();
  return useQuery([queryKey, studySlug], () => fetchStudyConf({ studySlug }));
};

export default useStudyConf;
