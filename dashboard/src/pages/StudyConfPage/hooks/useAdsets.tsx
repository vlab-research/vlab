import { queryCache, useInfiniteQuery } from 'react-query';
import { fetchAdsets } from '../../../helpers/api';
import { Cursor } from '../../../types/api';
import { AdsetsApiResponse } from '../../../types/study';

const limit = 100;

const useAdsets = (
  campaign: string | undefined,
  accessToken: string,
) => {

  const queryKey = `adsets${campaign}${accessToken}`;

  const defaultErrorMessage =
    'Something went wrong while fetching the adsets for this campaign';

  const definiteCampaign = campaign!;

  const query = useInfiniteQuery<AdsetsApiResponse, string, Cursor>(
    queryKey,
    (_: unknown, cursor: Cursor = null) =>
      fetchAdsets({
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
    adsets: (query.data || []).flatMap(page => page.data),
    errorMessage: query.error || defaultErrorMessage,
    refetchData: () => {
      queryCache.invalidateQueries(queryKey);
    },
  };
};

export default useAdsets;
