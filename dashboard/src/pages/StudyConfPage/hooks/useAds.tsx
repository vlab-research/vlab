import { queryCache, useInfiniteQuery } from 'react-query';
import { fetchAds } from '../../../helpers/api';
import { Cursor } from '../../../types/api';
import { AdsApiResponse } from '../../../types/study';

const limit = 100;

const useAds = (
  campaign: string | undefined,
  accessToken: string,
) => {

  const queryKey = `ads${campaign}${accessToken}`;

  const defaultErrorMessage =
    'Something went wrong while fetching the ads for this campaign';

  const definiteCampaign = campaign!;

  const query = useInfiniteQuery<AdsApiResponse, string, Cursor>(
    queryKey,
    (_: unknown, cursor: Cursor = null) =>
      fetchAds({
        limit,
        campaign: definiteCampaign,
        cursor,
        accessToken,
        defaultErrorMessage,
      }),
    {
      getFetchMore: lastPage => lastPage.paging.after,
      enabled: campaign !== undefined,
    }
  );

  return {
    query,
    ads: (query.data || []).flatMap(page => page.data),
    errorMessage: query.error || defaultErrorMessage,
    refetchData: () => {
      queryCache.invalidateQueries(queryKey);
    },
  };
};

export default useAds;
