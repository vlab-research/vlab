import { useInfiniteQuery } from 'react-query';
import { fetchAds } from '../../../helpers/api';

const limit = 100;

const useAds = (
  campaign: string | undefined,
  accessToken: string,
) => {

  const queryKey = `ads${campaign}${accessToken}`;

  const defaultErrorMessage =
    'Something went wrong while fetching the ads for this campaign';

  const definiteCampaign = campaign!;

  const query = useInfiniteQuery(
    queryKey,
    ({ pageParam: cursor }) =>
      fetchAds({
        limit,
        campaign: definiteCampaign,
        cursor,
        accessToken,
        defaultErrorMessage,
      }),
    {
      getNextPageParam: lastPage => lastPage?.paging?.after,
      enabled: campaign !== undefined,
    }
  );

  return {
    query,
    ads: (query.data?.pages || []).flatMap(page => page.data),
    errorMessage: query.error || defaultErrorMessage,
  };
};

export default useAds;
