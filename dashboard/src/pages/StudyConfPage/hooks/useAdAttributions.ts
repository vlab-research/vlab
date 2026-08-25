import { useQuery, useQueryClient } from 'react-query';
import { Notyf } from 'notyf';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
import { AdAttributionsApiResponse } from '../../../types/study';

const defaultErrorMessage = 'Could not fetch ad attributions';

const useAdAttributions = (studySlug: string) => {
  const notyf = new Notyf();
  const queryClient = useQueryClient();
  const { fetchAdAttributions } = useAuthenticatedApi();

  const queryKey = ['ad-attributions', studySlug];

  const { data, isLoading, isError, refetch } =
    useQuery<AdAttributionsApiResponse>(
      queryKey,
      () => fetchAdAttributions({ studySlug, defaultErrorMessage }),
      {
        enabled: !!studySlug,
        onError: (error: any) => {
          notyf.error({
            message: error.message || defaultErrorMessage,
            dismissible: true,
          });
        },
      }
    );

  return {
    table: data?.data || { columns: [], rows: [] },
    isLoading: isLoading || !!queryClient.isFetching(queryKey),
    isError,
    refetch,
  };
};

export default useAdAttributions;
