import { useMemo } from 'react';
import { useQuery, queryCache } from 'react-query';
import Chance from 'chance';
import { lastValue } from '../../helpers/arrays';
import { computeStudyProgressDataFrom } from '../../helpers/study';
import useAuthenticatedApi from '../../hooks/useAuthenticatedApi';
import {
  StudyProgressResource,
  StudySegmentProgressResource,
} from '../../types/study';

const chance = Chance();

const useStudy = (slug: string) => {
  const studyQuery = useStudyQuery(slug);
  const studySegmentsProgressQuery = useStudySegmentsProgressQuery(slug);

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

  const isLoading = !studyQuery.data || !studySegmentsProgressQuery.data?.data;

  const anyErrorDuringLoading =
    isLoading && (studyQuery.isError || studySegmentsProgressQuery.isError);

  return {
    name: studyQuery.data?.name ?? '',
    objective: studyQuery.data?.objective ?? '',
    optimizationGoal: studyQuery.data?.optimizationGoal ?? '',
    destinationType: studyQuery.data?.optimizationGoal ?? '',
    minBudget: studyQuery.data?.minBudget ?? '',
    instagramId: studyQuery.data?.instagramId ?? '',
    adAccount: studyQuery.data?.adAccount ?? '',
    country: studyQuery.data?.country ?? '',
    currentProgress,
    progressOverTime,
    currentSegmentsProgress: currentSegmentsProgress
      ? currentSegmentsProgress.segments
      : [],
    isLoading,
    anyErrorDuringLoading,
    refetchData: () => {
      queryCache.invalidateQueries(['study', slug]);
    },
  };
};

const useStudyQuery = (slug: string) => {
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
