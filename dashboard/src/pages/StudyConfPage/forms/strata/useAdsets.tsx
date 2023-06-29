import { useInfiniteQuery } from 'react-query';
import { fetchAdsets } from '../../../../helpers/api';
import { Cursor } from '../../../../types/api';
import { AdsetsApiResponse } from '../../../../types/study';

const limit = 100;

const useAdsets = (accountNumber: string, campaign: string, accessToken: string) => {

  const defaultErrorMessage = 'Something went wrong while fetching the adsets for the campaign ';
  console.log("campaign: ", campaign);

  const query = useInfiniteQuery<AdsetsApiResponse, string, Cursor>(
    "adsets" + campaign + accessToken,
    (_: unknown, cursor: Cursor = null) =>
      fetchAdsets({
        limit,
        accountNumber,
        campaign,
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
    adsets: (query.data || []).flatMap(page => page.data),
    errorMessage: query.error?.message,
  };
};

export default useAdsets;
