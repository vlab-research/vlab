import { queryCache, useInfiniteQuery } from 'react-query';
import { fetchCampaigns } from '../../../../helpers/api';
import { Cursor } from '../../../../types/api';
import { CampaignsApiResponse } from '../../../../types/study';

const limit = 100;
const defaultErrorMessage =
  'Something went wrong while fetching your campaigns';

const useCampaigns = (accountNumber: string, accessToken: string) => {
  const queryKey = `campaigns${accountNumber}${accessToken}`;

  const query = useInfiniteQuery<CampaignsApiResponse, string, Cursor>(
    queryKey,
    (_: unknown, cursor: Cursor = null) =>
      fetchCampaigns({
        limit,
        accountNumber,
        cursor,
        accessToken,
        defaultErrorMessage,
      }),
    {
      getFetchMore: lastPage => lastPage.paging.after,
    }
  );

  const isLoading = !query.data;

  const errorOnLoad = isLoading && query.isError;

  return {
    query,
    campaigns: (query.data || []).flatMap(page => page.data),
    loadingCampaigns: isLoading,
    errorLoadingCampaigns: errorOnLoad,
    errorMessage: query.error || defaultErrorMessage,
    refetchData: () => {
      queryCache.invalidateQueries([queryKey]);
    },
  };
};

export default useCampaigns;
