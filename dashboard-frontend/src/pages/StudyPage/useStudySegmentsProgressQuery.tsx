import { usePaginatedQuery } from 'react-query';
import { fetchStudySegmentsProgress } from '../../helpers/api';

export const segmentsProgressPerPage = 7;

const useStudySegmentsProgressQuery = (
  slug: string,
  cursor: string | null = null
) =>
  usePaginatedQuery(
    ['study', slug, 'segments-progress', { cursor }],
    () => fetchStudySegmentsProgress({ slug, cursor, segmentsProgressPerPage }),
    {
      refetchInterval: 30000,
    }
  );

export default useStudySegmentsProgressQuery;
