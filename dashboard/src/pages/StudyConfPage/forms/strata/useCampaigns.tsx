import { useInfiniteQuery } from 'react-query';
import { fetchCampaigns } from '../../../../helpers/api';
import { Cursor } from '../../../../types/api';
import { CampaignsApiResponse } from '../../../../types/study';

const limit = 100;
const defaultErrorMessage = 'Something went wrong while fetching the campaigns';

const useCampaigns = (accountNumber: string, accessToken: string) => {
  const query = useInfiniteQuery<CampaignsApiResponse, string, Cursor>(
    "campaigns" + accountNumber + accessToken,
    (_: unknown, cursor: Cursor = null) =>
      fetchCampaigns({
        limit,
        accountNumber,
        cursor,
        accessToken,
        defaultErrorMessage,
      })
    ,
    {
      getFetchMore: lastPage => lastPage.paging.after,
    }
  );

  return {
    query,
    campaigns: (query.data || []).flatMap(page => page.data),
    errorMessage: query.error?.message,
  };
};

export default useCampaigns;
