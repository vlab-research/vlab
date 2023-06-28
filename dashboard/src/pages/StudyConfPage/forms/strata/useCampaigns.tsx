import { useInfiniteQuery } from 'react-query';
import { fetchCampaigns } from '../../../../helpers/api';
import { Cursor } from '../../../../types/api';
import { CampaignsApiResponse } from '../../../../types/study';

const campaignsPerPage = 100;
const queryKey = 'campaigns';
const accessToken = '';
const defaultErrorMessage = 'Something went wrong while fetching the campaigns';
const accountNumber = '1342820622846299';

const useCampaigns = () => {
  const query = useInfiniteQuery<CampaignsApiResponse, string, Cursor>(
    queryKey,
    (_: unknown, cursor: Cursor = null) =>
      fetchCampaigns({
        campaignsPerPage,
        accountNumber,
        cursor,
        accessToken,
        defaultErrorMessage,
      })
  );

  return {
    query,
    queryKey,
    campaignsPerPage,
    campaigns: (query.data || [])
      .flatMap(page => page)
      .map(facebookResponse => facebookResponse.data)
      .flatMap(campaignData => campaignData),
    errorMessage: query.error?.message,
  };
};

export default useCampaigns;
