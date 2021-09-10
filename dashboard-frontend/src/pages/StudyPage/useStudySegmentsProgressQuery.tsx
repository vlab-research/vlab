import { usePaginatedQuery } from 'react-query';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';

export const segmentsProgressPerPage = 7;

const useStudySegmentsProgressQuery = (
  slug: string,
  cursor: string | null = null
) => {
  const { fetchStudySegmentsProgress } = useAuthenticatedApi();

  return usePaginatedQuery(
    ['study', slug, 'segments-progress', { cursor }],
    () =>
      fetchStudySegmentsProgress({
        slug,
        cursor,
        segmentsProgressPerPage,
      }),
    {
      refetchInterval: 30000,
    }
  );
};

export default useStudySegmentsProgressQuery;
