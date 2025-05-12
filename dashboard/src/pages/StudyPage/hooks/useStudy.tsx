import Chance from 'chance';
import { useMemo } from 'react';
import { useQuery } from 'react-query';
import { lastValue } from '../../../helpers/arrays';
import { computeStudyProgressDataFrom } from '../../../helpers/study';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
import {
  StudyProgressResource,
  StudySegmentProgressResource,
  UseStudyReturn,
} from '../../../types/study';

interface ApiError {
  status?: number;
  message?: string;
}

const chance = Chance();

const useStudy = (slug: string): UseStudyReturn => {
  const studyQuery = useStudyQuery(slug);
  const studySegmentsProgressQuery = useStudySegmentsProgressQuery(slug);
  const recruitmentStatsQuery = useStudyRecruitmentStatsQuery(slug);

  const segmentsProgressOverTime = useMemo(
    () => studySegmentsProgressQuery.data?.data ?? [],
    [studySegmentsProgressQuery.data]
  );

  const progressOverTime: StudyProgressResource[] = useMemo(() => {
    if (!segmentsProgressOverTime.length) {
      return [getStudyDefaultProgress()];
    }

    return segmentsProgressOverTime.map(computeStudyProgress);
  }, [segmentsProgressOverTime]);

  const currentSegmentsProgress = lastValue(segmentsProgressOverTime);

  const currentProgress: StudyProgressResource = useMemo(
    () => computeStudyProgress(currentSegmentsProgress),
    [currentSegmentsProgress]
  );

  // Only consider it loading if we don't have the basic study data
  const isLoading = !studyQuery.data;

  // Only consider it an error if it's not a 404 (missing confs)
  const anyErrorDuringLoading =
    isLoading && studyQuery.isError && (studyQuery.error as ApiError)?.status !== 404;

  return {
    name: studyQuery.data?.name ?? '',
    currentProgress,
    progressOverTime,
    currentSegmentsProgress: currentSegmentsProgress
      ? currentSegmentsProgress.segments
      : [],
    recruitmentStats: recruitmentStatsQuery.data?.data?.data ?? {},
    recruitmentStatsIsLoading: recruitmentStatsQuery.isLoading,
    isLoading,
    anyErrorDuringLoading,
    refetch: studyQuery.refetch,
  };
};

export const useStudyQuery = (slug: string) => {
  const { fetchStudy } = useAuthenticatedApi();
  return useQuery(['study', slug], () => fetchStudy({ slug }));
};

const useStudySegmentsProgressQuery = (slug: string) => {
  const { fetchStudySegmentsProgress } = useAuthenticatedApi();
  const fiveMinutesInMilliseconds = 5 * 60 * 1000;

  return useQuery(
    ['study', slug, 'segments-progress'],
    () => fetchStudySegmentsProgress({ slug }),
    {
      refetchInterval: fiveMinutesInMilliseconds,
    }
  );
};

const useStudyRecruitmentStatsQuery = (slug: string) => {
  const { fetchStudyRecruitmentStats } = useAuthenticatedApi();
  const fiveMinutesInMilliseconds = 5 * 60 * 1000;

  return useQuery(
    ['study', slug, 'recruitment-stats'],
    () => fetchStudyRecruitmentStats({ slug }),
    {
      refetchInterval: fiveMinutesInMilliseconds,
      // Don't treat 404s as errors since they just mean no recruitment data yet
      retry: (failureCount, error: ApiError) => {
        if (error?.status === 404) return false;
        return failureCount < 3;
      },
      // Add longer stale time and cache time
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      // Add error handling
      onError: (error: ApiError) => {
        console.error('Error fetching recruitment stats:', error);
      },
      onSuccess: (data) => {
        console.log('Recruitment stats raw data:', data);
        console.log('Recruitment stats data.data:', data?.data);
        console.log('Recruitment stats data.data.data:', data?.data?.data);
      },
    }
  );
};

const computeStudyProgress = (segmentsProgress?: {
  segments: StudySegmentProgressResource[];
  datetime: number;
}) => ({
  ...getStudyDefaultProgress(segmentsProgress?.datetime),
  ...(segmentsProgress?.segments
    ? computeStudyProgressDataFrom(segmentsProgress.segments)
    : {}),
});

const getStudyDefaultProgress = (datetime: number = Date.now()) => ({
  id: chance.guid({ version: 4 }),
  datetime,
  desiredParticipants: null,
  currentParticipants: 0,
  expectedParticipants: 0,
  currentAverageDeviation: 0,
  expectedAverageDeviation: 0,
});

export default useStudy;
