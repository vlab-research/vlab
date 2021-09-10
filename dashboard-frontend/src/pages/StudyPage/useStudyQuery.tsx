import { useQuery } from 'react-query';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';

const useStudyQuery = (slug: string) => {
  const { fetchStudy } = useAuthenticatedApi();

  return useQuery(['study', slug], () => fetchStudy({ slug }));
};

export default useStudyQuery;
