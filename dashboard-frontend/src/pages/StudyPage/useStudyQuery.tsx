import { useQuery } from 'react-query';
import { fetchStudy } from '../../helpers/api';

const useStudyQuery = (slug: string) =>
  useQuery(['study', slug], () => fetchStudy(slug));

export default useStudyQuery;
