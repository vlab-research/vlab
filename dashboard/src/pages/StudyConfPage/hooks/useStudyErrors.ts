import { useQuery, useQueryClient } from 'react-query';
import { Notyf } from 'notyf';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
import { StudyErrorsApiResponse } from '../../../types/study';

const defaultErrorMessage = 'Could not fetch study errors';

const useStudyErrors = (studySlug: string) => {
  const notyf = new Notyf();
  const queryClient = useQueryClient();
  const { fetchStudyErrors } = useAuthenticatedApi();

  const queryKey = ['study-errors', studySlug];

  const { data, isLoading, isError, refetch, dataUpdatedAt } =
    useQuery<StudyErrorsApiResponse>(
      queryKey,
      () => fetchStudyErrors({ studySlug, defaultErrorMessage }),
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
    errors: data?.errors || [],
    isLoading: isLoading || !!queryClient.isFetching(queryKey),
    isError,
    refetch,
    // When the derivation last resolved — the empty state shows this so a
    // healthy study still proves the check ran (the incident was silence).
    lastChecked: dataUpdatedAt ? new Date(dataUpdatedAt) : null,
  };
};

export default useStudyErrors;
