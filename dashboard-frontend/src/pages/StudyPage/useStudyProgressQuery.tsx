import { useQuery } from 'react-query';
import { fetchStudyProgress } from '../../helpers/api';

const useStudyProgressQuery = (slug: string) =>
  useQuery(['study', slug, 'progress'], () => fetchStudyProgress(slug), {
    refetchInterval: 30000,
  });

export default useStudyProgressQuery;
