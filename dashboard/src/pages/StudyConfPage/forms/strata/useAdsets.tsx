import { queryCache, useInfiniteQuery } from 'react-query';
import { fetchAdsets } from '../../../../helpers/api';
import { Cursor } from '../../../../types/api';
import { AdsetsApiResponse } from '../../../../types/study';

const limit = 100;

const useAdsets = (
  accountNumber: string,
  campaign: string,
  accessToken: string
) => {
  const queryKey = `adsets${campaign}${accessToken}`;

  const defaultErrorMessage =
    'Something went wrong while fetching the adsets for this campaign';
  console.log('campaign: ', campaign);

  const query = useInfiniteQuery<AdsetsApiResponse, string, Cursor>(
    queryKey,
    (_: unknown, cursor: Cursor = null) =>
      fetchAdsets({
        limit,
        accountNumber,
        campaign,
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
    adsets: (query.data || []).flatMap(page => page.data),
    loadingAdsets: isLoading,
    errorLoadingAdsets: errorOnLoad,
    errorMessage: query.error || defaultErrorMessage,
    refetchData: () => {
      queryCache.invalidateQueries(queryKey);
    },
  };
};

export default useAdsets;
