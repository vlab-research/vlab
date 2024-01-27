import { useInfiniteQuery } from 'react-query';
import { fetchCampaigns } from '../../../helpers/api';

const limit = 100;
const defaultErrorMessage =
  'Something went wrong while fetching your campaigns';

const useCampaigns = (accountNumber: string | undefined, accessToken: string) => {
  const queryKey = `campaigns${accountNumber}${accessToken}`;

  const account = accountNumber!

  const query = useInfiniteQuery(
    queryKey,
    ({ pageParam: cursor }) =>
      fetchCampaigns({
        limit,
        accountNumber: account,
        cursor,
        accessToken,
        defaultErrorMessage,
      }),
    {
      getNextPageParam: lastPage => lastPage.paging.after,
      enabled: accountNumber !== undefined,
    }
  );

  return {
    query,
    campaigns: (query.data?.pages || []).flatMap(page => page.data),
    errorMessage: query.error || defaultErrorMessage,
  };
};

export default useCampaigns;
