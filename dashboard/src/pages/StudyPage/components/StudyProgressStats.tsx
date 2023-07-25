import Stats, { StatsSkeleton } from './Stats';
import { StudyProgressResource } from '../../../types/study';
import { formatNumber } from '../../../helpers/numbers';

const StudyProgressStats = ({
  currentProgress,
  selectedStat,
  onSelectStat,
}: {
  currentProgress?: StudyProgressResource;
  selectedStat: string;
  onSelectStat: (selectedStat: string) => void;
}) => {
  if (!currentProgress) {
    return (
      <StatsSkeleton
        statTestId="study-current-progress-card-skeleton"
        statNames={[
          'Current Participants',
          'Expected Participants',
          'Current Avg. Deviation',
          'Expected Avg. Deviation',
        ]}
        selectedStat="Current Participants"
      />
    );
  }

  return (
    <Stats
      testId="study-page-stats"
      selectedStat={selectedStat}
      onSelectStat={onSelectStat}
      stats={[
        {
          name: 'Current Participants',
          stat: formatNumber(currentProgress.currentParticipants),
        },
        {
          name: 'Expected Participants',
          stat: formatNumber(currentProgress.expectedParticipants),
        },

        {
          name: 'Current Avg. Deviation',
          stat: `${currentProgress.currentAverageDeviation} %`,
        },
        {
          name: 'Expected Avg. Deviation',
          stat: `${currentProgress.expectedAverageDeviation} %`,
        },
      ]}
    />
  );
};

export default StudyProgressStats;
