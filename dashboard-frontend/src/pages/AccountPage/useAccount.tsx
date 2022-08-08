import { queryCache, useQuery } from 'react-query';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';

const useAccount = (slug: string) => {
  const accountQuery = useAccountQuery(slug);
  const isLoading = !accountQuery.data;
  const error = isLoading && accountQuery.isError;

  return {
    name: accountQuery.data?.name ?? '',
    isLoading,
    error,
    refetchData: () => {
      queryCache.invalidateQueries(['account', slug]);
    },
  };
};

const useAccountQuery = (slug: string) => {
  const { fetchAccount } = useAuthenticatedApi();
  return useQuery(['account', slug], () => fetchAccount({ slug }));
};

export default useAccount;
