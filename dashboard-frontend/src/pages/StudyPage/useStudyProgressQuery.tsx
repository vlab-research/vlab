import { useQuery } from 'react-query';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';

const useStudyProgressQuery = (slug: string) => {
  const { fetchStudyProgress } = useAuthenticatedApi();

  return useQuery(
    ['study', slug, 'progress'],
    () => fetchStudyProgress({ slug }),
    {
      refetchInterval: 30000,
    }
  );
};

export default useStudyProgressQuery;
