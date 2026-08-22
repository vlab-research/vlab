import { useState } from 'react';
import { useQuery, useQueryClient } from 'react-query';
import { Notyf } from 'notyf';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
import { AdAttributionsApiResponse } from '../../../types/study';

const defaultErrorMessage = 'Could not fetch ad attributions';

/**
 * The study's ad -> stratum mapping, and the CSV of the same thing.
 *
 * Not polled. Rows are appended when an ad is created and are frozen from then
 * on — a snapshot, never refreshed — so unlike the errors view there is nothing
 * here that goes stale on its own. A researcher checking their ref codes after
 * a reconciliation run refetches by arriving on the page.
 */
const useAdAttributions = (studySlug: string) => {
  const notyf = new Notyf();
  const queryClient = useQueryClient();
  const { fetchAdAttributions, downloadAdAttributionsCsv } =
    useAuthenticatedApi();

  const [isDownloading, setIsDownloading] = useState(false);

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

  const download = async () => {
    setIsDownloading(true);
    try {
      await downloadAdAttributionsCsv({ studySlug });
    } catch (error: any) {
      notyf.error({
        message: error.message || 'Could not download ad attributions',
        dismissible: true,
      });
    } finally {
      setIsDownloading(false);
    }
  };

  return {
    columns: data?.data?.columns || [],
    rows: data?.data?.rows || [],
    isLoading: isLoading || !!queryClient.isFetching(queryKey),
    isError,
    refetch,
    download,
    isDownloading,
  };
};

export default useAdAttributions;
