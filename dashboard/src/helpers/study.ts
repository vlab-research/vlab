import { StudySegmentProgressResource } from '../types/study';
import { calculateAverage } from './numbers';

export const computeStudyProgressDataFrom = (
  segmentProgressList: StudySegmentProgressResource[]
) => ({
  currentParticipants: computeCurrentParticipantsFrom(segmentProgressList),
  expectedParticipants: computeExpectedParticipantsFrom(segmentProgressList),
  currentAverageDeviation: calculateAverage(
    segmentProgressList.map(
      ({ percentageDeviationFromGoal }) => percentageDeviationFromGoal
    )
  ),
  expectedAverageDeviation: calculateAverage(
    segmentProgressList.map(({ expectedPercentage, desiredPercentage }) =>
      Math.abs(desiredPercentage - expectedPercentage)
    )
  ),
});

export const computeCurrentParticipantsFrom = (
  segmentProgressList: StudySegmentProgressResource[]
) =>
  segmentProgressList.reduce(
    (prev, { currentParticipants }) => prev + currentParticipants,
    0
  );

export const computeExpectedParticipantsFrom = (
  segmentProgressList: StudySegmentProgressResource[]
) =>
  segmentProgressList.reduce(
    (prev, { expectedParticipants }) => prev + expectedParticipants,
    0
  );
