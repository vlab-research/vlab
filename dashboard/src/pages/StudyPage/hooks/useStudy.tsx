import Chance from 'chance';
import { useMemo } from 'react';
import { useQuery } from 'react-query';
import { lastValue } from '../../../helpers/arrays';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
import {
  StudyProgressResource,
  UseStudyReturn,
  RespondentsTimePointData,
} from '../../../types/study';

interface ApiError {
  status?: number;
  message?: string;
}

const chance = Chance();

// Transform new adopt server API response to StudyProgressResource format
// This only provides currentParticipants over time for the time chart
const transformToStudyProgress = (
  timePoint: RespondentsTimePointData
): StudyProgressResource => {
  return {
    id: chance.guid({ version: 4 }),
    datetime: timePoint.datetime,
    desiredParticipants: null,
    currentParticipants: timePoint.totalParticipants,
    expectedParticipants: 0,
    currentAverageDeviation: 0,
    expectedAverageDeviation: 0,
  };
};

const useStudy = (slug: string): UseStudyReturn => {
  const studyQuery = useStudyQuery(slug);
  // Old Go API - for segment table and other components
  const studySegmentsProgressQuery = useStudySegmentsProgressQuery(slug);
  // New Adopt Server API - for participants over time chart
  const respondentsOverTimeQuery = useRespondentsOverTimeQuery(slug);
  const recruitmentStatsQuery = useStudyRecruitmentStatsQuery(slug);

  // Old Go API data for segment table
  const segmentsProgressOverTime = useMemo(
    () => studySegmentsProgressQuery.data?.data ?? [],
    [studySegmentsProgressQuery.data]
  );

  // New Adopt Server API data for time chart
  const progressOverTime: StudyProgressResource[] = useMemo(() => {
    const apiData = respondentsOverTimeQuery.data?.data ?? [];
    if (!apiData.length) {
      return [getStudyDefaultProgress()];
    }
    return apiData.map(transformToStudyProgress);
  }, [respondentsOverTimeQuery.data]);

  const currentProgress: StudyProgressResource = useMemo(
    () => lastValue(progressOverTime) ?? getStudyDefaultProgress(),
    [progressOverTime]
  );

  // Segment table data from old Go API
  const currentSegmentsProgress = useMemo(() => {
    const lastTimePoint = lastValue(segmentsProgressOverTime);
    return lastTimePoint ? lastTimePoint.segments : [];
  }, [segmentsProgressOverTime]);

  // Only consider it loading if we don't have the basic study data
  const isLoading = !studyQuery.data;

  // Only consider it an error if it's not a 404 (missing confs)
  const anyErrorDuringLoading =
    isLoading && studyQuery.isError && (studyQuery.error as ApiError)?.status !== 404;

  return {
    name: studyQuery.data?.name ?? '',
    currentProgress,
    progressOverTime,
    currentSegmentsProgress,
    recruitmentStats: recruitmentStatsQuery.data?.data ?? {},
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

// Old Go API - for segment table and other components
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

// New Adopt Server API - for participants over time chart
const useRespondentsOverTimeQuery = (slug: string) => {
  const { fetchRespondentsOverTime } = useAuthenticatedApi();
  const fiveMinutesInMilliseconds = 5 * 60 * 1000;

  return useQuery(
    ['study', slug, 'respondents-over-time'],
    () => fetchRespondentsOverTime({ slug }),
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
      },
    }
  );
};

const getStudyDefaultProgress = (datetime: number = Date.now()): StudyProgressResource => ({
  id: chance.guid({ version: 4 }),
  datetime,
  desiredParticipants: null,
  currentParticipants: 0,
  expectedParticipants: 0,
  currentAverageDeviation: 0,
  expectedAverageDeviation: 0,
});

export default useStudy;
