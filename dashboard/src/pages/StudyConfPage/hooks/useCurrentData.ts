import { useQuery, useQueryClient } from 'react-query';
import { Notyf } from 'notyf';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
import { CurrentDataApiResponse } from '../../../types/study';

const defaultErrorMessage = 'Could not fetch current data';

const useCurrentData = (studySlug: string) => {
  const notyf = new Notyf();
  const queryClient = useQueryClient();
  const { fetchCurrentData } = useAuthenticatedApi();

  const queryKey = ['current-data', studySlug];

  const { data, isLoading, isError, refetch } = useQuery<CurrentDataApiResponse>(
    queryKey,
    () => fetchCurrentData({ studySlug, defaultErrorMessage }),
    {
      refetchInterval: 30000, // Refresh every 30 seconds
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
    data: data?.data || [],
    isLoading: isLoading || !!queryClient.isFetching(queryKey),
    isError,
    refetch,
  };
};

export default useCurrentData; 