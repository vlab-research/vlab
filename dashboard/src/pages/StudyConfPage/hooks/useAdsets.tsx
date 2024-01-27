import { useInfiniteQuery } from 'react-query';
import { fetchAdsets } from '../../../helpers/api';

const limit = 100;

const useAdsets = (
  campaign: string | undefined,
  accessToken: string,
) => {

  const queryKey = `adsets${campaign}${accessToken}`;

  const defaultErrorMessage =
    'Something went wrong while fetching the adsets for this campaign';

  const definiteCampaign = campaign!;

  const query = useInfiniteQuery(
    queryKey,
    ({ pageParam: cursor }) =>
      fetchAdsets({
        limit,
        campaign: definiteCampaign,
        cursor,
        accessToken,
        defaultErrorMessage,
      }),
    {
      getNextPageParam: lastPage => lastPage.paging.after,
      enabled: campaign !== undefined,
    }
  );

  return {
    query,
    adsets: (query.data?.pages || []).flatMap(page => page.data),
    errorMessage: query.error || defaultErrorMessage,
  };
};

export default useAdsets;
