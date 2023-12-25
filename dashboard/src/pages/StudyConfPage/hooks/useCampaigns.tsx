import { queryCache, useInfiniteQuery } from 'react-query';
import { fetchCampaigns } from '../../../helpers/api';
import { Cursor } from '../../../types/api';
import { CampaignsApiResponse } from '../../../types/study';

const limit = 100;
const defaultErrorMessage =
  'Something went wrong while fetching your campaigns';

const useCampaigns = (accountNumber: string | undefined, accessToken: string) => {
  const queryKey = `campaigns${accountNumber}${accessToken}`;

  const account = accountNumber!

  const query = useInfiniteQuery<CampaignsApiResponse, string, Cursor>(
    queryKey,
    (_: unknown, cursor: Cursor = null) =>
      fetchCampaigns({
        limit,
        accountNumber: account,
        cursor,
        accessToken,
        defaultErrorMessage,
      }),
    {
      getFetchMore: lastPage => lastPage.paging.after,
      enabled: accountNumber !== undefined,
    }
  );

  return {
    query,
    campaigns: (query.data || []).flatMap(page => page.data),
    errorMessage: query.error || defaultErrorMessage,
    refetchData: () => {
      queryCache.invalidateQueries([queryKey]);
    },
  };
};

export default useCampaigns;
