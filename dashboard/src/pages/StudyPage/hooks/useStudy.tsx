import Chance from 'chance';
import { useMemo } from 'react';
import { useQuery } from 'react-query';
import { lastValue } from '../../../helpers/arrays';
import { computeStudyProgressDataFrom } from '../../../helpers/study';
import useAuthenticatedApi from '../../../hooks/useAuthenticatedApi';
import {
  StudyProgressResource,
  StudySegmentProgressResource,
  RecruitmentStatsRow,
} from '../../../types/study';

const chance = Chance();

const useStudy = (slug: string) => {
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

  const isLoading = !studyQuery.data || !studySegmentsProgressQuery.data?.data || !recruitmentStatsQuery.data?.data;

  const anyErrorDuringLoading =
    isLoading && (studyQuery.isError || studySegmentsProgressQuery.isError || recruitmentStatsQuery.isError);

  return {
    name: studyQuery.data?.name ?? '',
    currentProgress,
    progressOverTime,
    currentSegmentsProgress: currentSegmentsProgress
      ? currentSegmentsProgress.segments
      : [],
    recruitmentStats: recruitmentStatsQuery.data?.data ?? {},
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
